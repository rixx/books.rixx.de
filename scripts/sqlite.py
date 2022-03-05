from pathlib import Path

import sqlite_utils
from tqdm import tqdm

from . import books


def render_db(db, reviews=None, plans=None):
    # TODO: include quotes
    # TODO: include authors, if they have pages of their own

    reviews = reviews or books.load_reviews()
    plans = plans or books.load_to_read()

    db = Path(db)
    if db.exists():
        # TODO: update database instead of re-rendering every time
        db.unlink()

    db = sqlite_utils.Database(db)

    authors_table = db.table("authors", pk="id")
    books_table = db.table("books", pk="id")
    tags_table = db.table("tags", pk="id")
    books_table = db.table("books", pk="id")
    dates_read_table = db.table("dates_read", pk="id")

    for review in tqdm(list(reviews) + list(plans), desc="Saving books  "):
        # TODO: maybe prepare relations using known IDs, and use bulk_insert
        # https://sqlite-utils.datasette.io/en/stable/python-api.html#bulk-inserts
        book = review.serialized_data
        authors = book.pop("author")
        authors = [authors] if authors else []
        tags = [{"id": tag, "tag": tag} for tag in book.pop("tags") or []]
        dates_read = book.pop("date_read", None) or []

        books_table.insert(book, pk="id", replace=True).m2m(authors_table, authors).m2m(
            tags_table, tags
        )

        for date in dates_read:
            dates_read_table.insert({"date": date, "book_id": book["id"]})
