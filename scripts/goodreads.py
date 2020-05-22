import xml.etree.ElementTree as ET

import requests

from . import utils

GOODREADS_URL = "https://www.goodreads.com/"


def get_shelves(auth) -> dict:
    response = requests.get(
        GOODREADS_URL + f"user/show/{auth['goodreads_user_id']}.xml",
        {"key": auth["goodreads_personal_token"]},
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


@utils.book_data
def get_book_from_goodreads(auth):
    # TODO search
    # TODO offer options
    # TODO ask state
    pass


def push_to_goodreads(data, path, auth, entry_type):
    goodreads_id = data["book"]["goodreads"]
    shelf = {
        "review": "read",
        "to_read": "to-read",
        "currently_reading": "currently-reading",
    }[entry_type]
    shelf_id = auth["shelves"][shelf]
    # TODO read frontmatter if needed
    # TODO push book to shelf
