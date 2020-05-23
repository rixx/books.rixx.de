import xml.etree.ElementTree as ET
from contextlib import suppress

import click
import dateutil.parser
import requests
from rauth.service import OAuth1Session

GOODREADS_URL = "https://www.goodreads.com/"


def get_session(auth):
    return OAuth1Session(
        consumer_key=auth["goodreads_developer_key"],
        consumer_secret=auth["goodreads_developer_secret"],
        access_token=auth["goodreads_user_access_token"],
        access_token_secret=auth["goodreads_user_access_secret"],
    )


def get_shelves(auth) -> dict:
    response = requests.get(
        GOODREADS_URL + f"user/show/{auth['goodreads_user_id']}.xml",
        {"key": auth["goodreads_developer_key"]},
    )
    response.raise_for_status()
    to_root = ET.fromstring(response.content.decode())
    user = to_root.find("user")
    shelves = user.find("user_shelves")
    if not shelves:
        raise Exception(
            "This user's shelves and reviews are private, and cannot be fetched."
        )

    return {shelf.find("name").text: shelf.find("id").text for shelf in shelves}


def get_book_data(url, auth):
    response = requests.get(url, {"key": auth["goodreads_developer_key"]})
    to_root = ET.fromstring(response.content.decode())
    book = to_root.find("book")
    return get_book_data_from_xml(book)


def get_book_from_goodreads(auth):
    search_term = click.prompt(
        "Give me your best Goodreads search terms – or a URL, if you have one!"
    )
    if "goodreads.com" in search_term:
        return get_book_data(url=search_term.strip() + ".xml", auth=auth)

    response = requests.get(
        f"{GOODREADS_URL}search/index.xml",
        {"key": auth["goodreads_developer_key"], "q": search_term},
    )

    to_root = ET.fromstring(response.content.decode())
    results = to_root.find("search").find("results")
    options = [
        {
            "id": work.find("best_book").find("id").text,
            "title": work.find("best_book").find("title").text,
            "author": work.find("best_book").find("author").find("name").text,
        }
        for work in results
    ]
    click.echo(f"Found {len(options)} possible books:")
    for index, book in enumerate(options):
        click.echo(f"{index + 1}. {book['title']} by {book['author']}")
    print()
    book = options[int(click.prompt("Which one is it?")) - 1]
    return get_book_data(url=f"{GOODREADS_URL}book/show/{book['id']}.xml", auth=auth)


def add_review(review, auth):
    # review.create
    pass


def maybe_date(value):
    if value:
        return dateutil.parser.parse(value)
    return None


def get_book_data_from_xml(book):
    keys = {
        "id": "goodreads",
        "isbn": "isbn10",
        "isbn13": "isbn13",
        "num_pages": "pages",
        "publication_year": "publication_year",
    }
    data = {mapped_key: book.find(key).text for key, mapped_key in keys.items()}
    for key in ("small_image_url", "image_url", "large_image_url"):
        with suppress(Exception):
            data["cover_image_url"] = book.find(key).text
    data["author"] = ", ".join(
        author.find("name").text for author in book.find("authors")
    )
    title_series = book.find("title").text
    try:
        data["title"] = book.find("title_without_series").text
    except Exception:
        data["title"] = title_series
    if data["title"] != title_series:
        series_with_position = title_series[len(data["title"]) :].strip(" ()")
        if "#" in series_with_position:
            series, series_position = series_with_position.split("#", maxsplit=1)
        elif "Book" in series_with_position:
            series, series_position = series_with_position.split("Book", maxsplit=1)
        else:
            series = series_with_position
            series_position = ""
        data["series"] = series.strip(", ")
        data["series_position"] = series_position.strip(", #")
    return data


def get_review(review, auth):
    data = {
        "key": auth["goodreads_developer_key"],
        "user_id": auth["goodreads_user_id"],
        "book_id": review.metadata["book"]["goodreads"],
        "include_review_on_work": True,
    }
    response = requests.get(
        GOODREADS_URL + "review/show_by_user_and_book.xml", data=data
    )
    if response.status_code != 200:
        print("No existing review found, will create a new one.")
        return
    to_root = ET.fromstring(response.content.decode())
    review = to_root.find("review")
    review_data = {
        "id": review.find("id").text,
        "rating": review.find("rating").text,
        "date_added": maybe_date(review.find("date_added").text),
        "started_at": maybe_date(review.find("started_at").text),
        "read_at": maybe_date(review.find("read_at").text),
        "book": get_book_data_from_xml(review.find("book")),
        "text": (review.find("body").text or "").strip(),
    }
    for shelf in review.find("shelves"):
        if shelf.attrib.get("exclusive") in [True, "true"]:
            review_data["shelf"] = {
                "id": shelf.attrib.get("id"),
                "name": shelf.attrib.get("name"),
            }
    return review_data


def remove_review(review, auth):
    # Oh goodreads.
    # Both the documented version
    # response = session.delete(GOODREADS_URL + f"review/destroy.xml?id={goodreads_review['id']}")
    # and the version actually used by the website:
    # session.post(GOODREADS_URL + f"review/destroy/{review.metadata['book']['goodreads']}", data={})
    # Only produce 401 errors on a correctly authed session. So apparently this is broken, and has been
    # for at least some years, judging from the forum posts.
    print(
        "Sorry, removing books from shelves with goodreads is just … not possible right now."
    )
    print("Please go here and remove the book from your shelves manually:")
    print(
        f"    {GOODREADS_URL}book/show/{review.metadata['book']['goodreads']}-bot-protect"
    )
    print()


def change_shelf(review, auth):
    session = get_session(auth)
    shelf_name = "read" if review.entry_type == "reviews" else review.entry_type
    response = session.post(
        f"{GOODREADS_URL}shelf/add_to_shelf.xml",
        {"name": shelf_name, "book_id": review.metadata["book"]["goodreads"]},
    )
    response.raise_for_status()


def push_to_goodreads(review, auth):
    goodreads_review = get_review(review, auth) or {}
    create_review = "id" not in goodreads_review
    shelf_name = "read" if review.entry_type == "reviews" else review.entry_type
    if (not create_review) and shelf_name != goodreads_review["shelf"]:
        change_shelf(review, auth)

    review_data = {
        "book_id": review.metadata["book"]["goodreads"],
        "review[review]": review.text,
        "review[rating]": review.metadata.get("review", {}).get("rating", 0),
        "shelf_name": shelf_name,
    }
    read_at = review.metadata.get("review", {}).get("read_at", "")
    if read_at:
        review_data["review[read_at]"] = read_at
        review_data["finished"] = True

    session = get_session(auth)
    response = session.post(f"{GOODREADS_URL}review.xml", data=review_data)
    response.raise_for_status()
