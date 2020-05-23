import xml.etree.ElementTree as ET

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


def get_book_from_goodreads(auth):
    # TODO search
    # TODO offer options
    # TODO ask state
    pass


def add_review(review, auth):
    # review.create
    pass


def get_review(review, auth):
    data = {
        "key": auth["goodreads_developer_key"],
        "user_id": auth["goodreads_user_id"],
        "book_id": review.metadata["book"]["goodreads"],
        "include_review_on_work": True,
    }
    review.show_by_user_and_book
    response = requests.get(
        GOODREADS_URL + "/review/show_by_user_and_book.xml", data=data
    )
    # TODO response to json


def remove_review(review, auth):
    goodreads_review = get_review(review, auth)
    response = requests.delete(
        GOODREADS_URL + f"/review/destroy/{goodreads_review['id']}"
    )
    response.raise_for_status()


def push_to_goodreads(review, auth):
    goodreads_review = get_review(review, auth)
    shelf_name = "read" if review.entry_type == "reviews" else review.entry_type
    shelf_id = auth["shelves"][shelf_name]
    # TODO read frontmatter if needed
    # TODO push book to shelf
