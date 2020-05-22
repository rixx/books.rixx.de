import datetime as dt
import sqlite3

import frontmatter
import requests
from tqdm import tqdm

from .books import get_out_path, save_cover
from .utils import slugify


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def import_books():

    conn = sqlite3.connect("/home/rixx/src/goodreads-to-sqlite/books.db")
    conn.row_factory = dict_factory

    query = """select
      books.title as book_title,
      books.id as book_id,
      books.publication_date,
      books.image_url,
      books.isbn as isbn10,
      books.isbn13,
      books.series,
      books.series_position,
      books.pages,
      reviews.date_added,
      reviews.started_at,
      reviews.read_at,
      reviews.rating,
      reviews.text,
      shelves.name
    from
      books
      join reviews on reviews.book_id = books.id
      join reviews_shelves on reviews.id = reviews_shelves.reviews_id
      join shelves on reviews_shelves.shelves_id = shelves.id
    where shelves.name in ("to-read", "read", "currently-reading")"""

    c = conn.cursor()
    books = list(c.execute(query))
    for book in tqdm(books):
        book_id = book["book_id"]
        authors = list(
            c.execute(
                f"select * from authors join authors_books on authors.id = authors_books.authors_id where authors_books.books_id = '{book_id}'"
            )
        )
        author_names = ", ".join(author["name"] for author in authors)
        book_data = {
            "goodreads": book_id,
            "title": book["book_title"],
            "author": author_names,
            "publication_year": book["publication_date"][:4]
            if book["publication_date"]
            else None,
            "slug": slugify(book["book_title"]),
        }
        plan = {
            "date_added": book["date_added"][:10] if book["date_added"] else None,
        }
        for key in (
            "isbn10",
            "isbn13",
            "series",
            "series_position",
            "pages",
        ):
            if value := book[key]:
                book_data[key] = value

        book_data["cover_image_url"] = book["image_url"]
        isbn = book_data.get("isbn10") or book_data.get("isbn13")
        if isbn:
            url = f"http://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            try:
                book_data["cover_image"] = save_cover(
                    slug=book_data["slug"], cover_image_url=url,
                )
                book_data["cover_image_url"] = url
            except:
                pass
            if not book_data.get("cover_image"):
                url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
                response = requests.get(url)
                try:
                    url = response.json()["items"][0]["volumeInfo"]["imageLinks"][
                        "thumbnail"
                    ]
                    book_data["cover_image"] = save_cover(
                        slug=book_data["slug"], cover_image_url=url,
                    )
                except:
                    pass
        if not book_data.get("cover_image"):
            book_data["cover_image"] = save_cover(
                slug=book_data["slug"], cover_image_url=book_data["cover_image_url"],
            )
        entry = {"book": book_data, "plan": plan}
        if book["name"] == "read":
            read_at = (
                dt.datetime.strptime(book["read_at"][:10], "%Y-%m-%d").date()
                if book["read_at"]
                else None
            )
            started_at = (
                dt.datetime.strptime(book["started_at"][:10], "%Y-%m-%d").date()
                if book["started_at"]
                else None
            )
            read_at = read_at or started_at
            if not read_at:
                raise Exception(book)
            entry["review"] = {
                "date_started": started_at,
                "date_read": read_at,
                "rating": book["rating"],
                "did_not_finish": False,
            }
        entry_type = {
            "read": "review",
            "to-read": "to_read",
            "currently-reading": "currently_reading",
        }[book["name"]]
        out_path = get_out_path(entry, entry_type)
        with open(out_path, "wb") as out_file:
            frontmatter.dump(
                frontmatter.Post(
                    content=book["text"] if book["name"] == "read" else "", **entry
                ),
                out_file,
            )
            out_file.write(b"\n")
