import datetime as dt
import json
import xml.etree.ElementTree as ET
from contextlib import suppress

import click
import dateutil.parser
import inquirer
import requests
from rauth.service import OAuth1Session

GOODREADS_URL = "https://www.goodreads.com/"


def get_auth():
    return json.load(open("auth.json"))


def get_session():
    auth = get_auth()
    return OAuth1Session(
        consumer_key=auth["goodreads_developer_key"],
        consumer_secret=auth["goodreads_developer_secret"],
        access_token=auth["goodreads_user_access_token"],
        access_token_secret=auth["goodreads_user_access_secret"],
    )


def get_shelves() -> dict:
    auth = get_auth()
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


def get_book_data(url):
    auth = get_auth()
    response = requests.get(url, {"key": auth["goodreads_developer_key"]})
    to_root = ET.fromstring(response.content.decode())
    book = to_root.find("book")
    return get_book_data_from_xml(book)


def get_book_from_goodreads(search_term=None):
    auth = get_auth()
    search_term = inquirer.text(
        "Give me your best Goodreads search terms – or a URL, if you have one!",
        default=None,
    )
    if "goodreads.com" in search_term:
        return get_book_data(url=search_term.strip() + ".xml")

    response = requests.get(
        f"{GOODREADS_URL}search/index.xml",
        {"key": auth["goodreads_developer_key"], "q": search_term},
    )

    to_root = ET.fromstring(response.content.decode())
    results = to_root.find("search").find("results")
    options = []
    for index, work in enumerate(results):
        title = work.find("best_book").find("title").text
        author = work.find("best_book").find("author").find("name").text
        options.append(
            (
                (f"{index + 1}. {title} by {author}"),
                work.find("best_book").find("id").text,
            )
        )

    click.echo(
        click.style(f"Found {len(options)} possible books:", fg="green", bold=True)
    )
    book = inquirer.list_input(message="Which one did you mean?", choices=options)
    return get_book_data(url=f"{GOODREADS_URL}book/show/{book}.xml")


def maybe_date(value):
    if value:
        return dateutil.parser.parse(value)
    return None


def get_book_data_from_xml(book):
    if not book:
        return
    keys = {
        "id": "goodreads",
        "isbn": "isbn10",
        "isbn13": "isbn13",
        "num_pages": "pages",
    }
    data = {mapped_key: book.find(key).text for key, mapped_key in keys.items()}
    try:
        data["publication_year"] = (
            book.find("work").find("original_publication_year").text
        )
    except Exception:
        data["publication_year"] = book.find("publication_year").text
    for key in ("small_image_url", "image_url", "large_image_url"):
        with suppress(Exception):
            data["cover_image_url"] = book.find(key).text
    data["author"] = ", ".join(
        author.find("name").text for author in book.find("authors")
    )
    title_series = book.find("title").text
    try:
        data["title"] = book.find("work").find("original_title").text
    except Exception:
        try:
            data["title"] = book.find("title_without_series").text
        except Exception:
            pass
    data["title"] = data["title"] or title_series
    if data["title"] != title_series:
        series_with_position = title_series.rsplit("(", maxsplit=1)[-1].strip(" ()")
        if "#" in series_with_position:
            series, series_position = series_with_position.split("#", maxsplit=1)
        elif "Book" in series_with_position:
            series, series_position = series_with_position.split("Book", maxsplit=1)
        else:
            series = series_with_position
            series_position = ""
        data["series"] = series.strip(", ")
        data["series_position"] = series_position.strip(", #")
    data["title"] = data["title"].split(":")[0].strip()
    return data


def get_review(review):
    auth = get_auth()
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
        click.echo("No existing review found, will create a new one.")
        return
    to_root = ET.fromstring(response.content.decode())
    review = to_root.find("review")
    review_data = {
        "id": review.find("id").text,
        "rating": review.find("rating").text,
        "date_added": maybe_date(review.find("date_added").text),
        "date_read": maybe_date(review.find("read_at").text),
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


def remove_review(review):
    # Oh goodreads.
    # Both the documented version
    # response = session.delete(GOODREADS_URL + f"review/destroy.xml?id={goodreads_review['id']}")
    # and the version actually used by the website:
    # session.post(GOODREADS_URL + f"review/destroy/{review.metadata['book']['goodreads']}", data={})
    # Only produce 401 errors on a correctly authed session. So apparently this is broken, and has been
    # for at least some years, judging from the forum posts.
    click.echo(
        click.style(
            "Sorry, removing books from shelves with goodreads is just … not possible right now.",
            fg="red",
        )
    )
    click.echo("Please go here and remove the book from your shelves manually:")
    click.echo(
        click.style(
            f"    {GOODREADS_URL}book/show/{review.metadata['book']['goodreads']}-bot-protect",
            bold=True,
        )
    )
    print()


def change_shelf(review, session=None):
    session = session or get_session()
    shelf_name = "read" if review.entry_type == "reviews" else review.entry_type
    response = session.post(
        f"{GOODREADS_URL}shelf/add_to_shelf.xml",
        {"name": shelf_name, "book_id": review.metadata["book"]["goodreads"]},
    )
    response.raise_for_status()


def push_to_goodreads(review):
    goodreads_review = get_review(review) or {}
    create_review = "id" not in goodreads_review
    shelf_name = "read" if review.entry_type == "reviews" else review.entry_type
    if (not create_review) and shelf_name != goodreads_review["shelf"]:
        change_shelf(review)

    review_text = "\n\n".join(
        paragraph.replace("\n", " ") for paragraph in review.text.split("\n\n")
    )

    review_data = {
        "book_id": review.metadata["book"]["goodreads"],
        "review[review]": review_text,
        "review[rating]": review.metadata.get("review", {}).get("rating", 0),
        "shelf_name": shelf_name,
    }
    read_at = review.metadata.get("review", {}).get("date_read", "")
    if read_at:
        if isinstance(read_at, (dt.date, dt.datetime)):
            read_at = read_at.strftime("%Y-%m-%d")
        review_data["review[read_at]"] = read_at
        review_data["review[started_at]"] = read_at
        review_data["finished"] = True
    else:
        review_data["finished"] = False

    session = get_session()

    if create_review:
        response = session.post(f"{GOODREADS_URL}review.xml", data=review_data)
        if shelf_name != "read":
            change_shelf(
                review, session=session
            )  # Somehow, the shelf gets always set to read, so we update it
    else:
        review_data["id"] = goodreads_review["id"]
        response = session.post(
            f"{GOODREADS_URL}review/{goodreads_review['id']}.xml", data=review_data
        )
    response.raise_for_status()
