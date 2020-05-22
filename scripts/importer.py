import datetime as dt
import sqlite3

import frontmatter
from tqdm import tqdm

from .books import get_out_path, save_cover
from .utils import slugify


def import_books():
    conn = sqlite3.connect("/home/rixx/src/goodreads-to-sqlite/books.db")
    query = """select
      *
    from
      books
      join reviews on reviews.book_id = books.id
      join reviews_shelves on reviews.id = reviews_shelves.reviews_id
      join shelves on reviews_shelves.shelves_id = shelves.id
    where shelves.name in ("to-read", "read", "currently-reading")"""

    c = conn.cursor()
    books = list(c.execute(query))
    for book in tqdm(books):
        (
            book_id,
            isbn10,
            isbn13,
            title,
            series,
            series_position,
            pages,
            _,
            publication_date,
            _,
            image_url,
            review_id,
            _,
            _,
            rating,
            review,
            date_added,
            _,
            read_at,
            started_at,
            _,
            _,
            _,
            shelf,
            _,
        ) = book

        authors = list(
            c.execute(
                f"select * from authors join authors_books on authors.id = authors_books.authors_id where authors_books.books_id = '{book_id}'"
            )
        )
        author_names = ", ".join(author[1] for author in authors)
        book_data = {
            "goodreads": book_id,
            "title": title,
            "author": author_names,
            "publication_year": publication_date[:4] if publication_date else None,
            "slug": slugify(title),
            "cover_image_url": image_url,
        }
        plan = {
            "date_added": date_added[:10] if date_added else None,
        }
        for key, value in (
            ("isbn10", isbn10),
            ("isbn13", isbn13),
            ("series", series),
            ("series_position", series_position),
            ("pages", pages),
        ):
            if value:
                book_data[key] = value
        book_data["cover_image"] = save_cover(
            slug=book_data["slug"], cover_image_url=book_data["cover_image_url"]
        )
        entry = {"book": book_data, "plan": plan}
        read_at = (
            dt.datetime.strptime(read_at[:10], "%Y-%m-%d").date() if read_at else None
        )
        started_at = (
            dt.datetime.strptime(started_at[:10], "%Y-%m-%d").date()
            if started_at
            else read_at
        )
        read_at = read_at or started_at
        if shelf == "read":
            entry["review"] = {
                "date_started": started_at,
                "date_read": read_at,
                "rating": rating,
                "did_not_finish": False,
            }
        entry_type = {
            "read": "review",
            "to-read": "to_read",
            "currently-reading": "currently_reading",
        }[shelf]
        out_path = get_out_path(entry, entry_type)
        with open(out_path, "wb") as out_file:
            frontmatter.dump(
                frontmatter.Post(content=review if shelf == "read" else "", **entry),
                out_file,
            )
            out_file.write(b"\n")
