import datetime as dt
import sqlite3
from pathlib import Path
from scripts.books import load_review_by_slug

from tqdm import tqdm

from .books import Review


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
        plan = {
            "date_added": book["date_added"][:10] if book["date_added"] else None,
        }
        metadata = {"book": book_data, "plan": plan}
        text = ""
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
            metadata["review"] = {
                "date_started": started_at,
                "date_read": read_at,
                "rating": book["rating"],
                "did_not_finish": False,
            }
            text = book["text"]
        entry_type = {
            "read": "reviews",
            "to-read": "to-read",
            "currently-reading": "currently-reading",
        }[book["name"]]
        review = Review(metadata=metadata, text=text, entry_type=entry_type)
        review.download_cover()
        review.save()


def fix_duplicate_pics():
    # find src/ ! -empty -type f -exec md5sum {} + | sort | uniq -w32 -dD | cut -d " " -f 3 > dupes.txt

    with open("dupes.txt") as fp:
        dupes = [d.strip() for d in fp.read().split("\n")]

    dupes = [Path(d).stem for d in dupes]
    reviews = [load_review_by_slug(d) for d in dupes if d]
    for review in tqdm(reviews):
        previous_path = review.metadata["book"].pop("cover_image", None)
        if previous_path:
            path = Path("src/covers") / previous_path
            if path.exists():
                path.unlink()
        result = review.find_goodreads_scrape_cover(force_new=True)
        if result is False:
            print(f'Failed to find a cover for {review.metadata["book"]["slug"]}')
            review.metadata["book"].pop("cover_image_url", None)
        review.save()
