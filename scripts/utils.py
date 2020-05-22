import re

from unidecode import unidecode


def slugify(u):
    """Convert Unicode string into blog slug."""
    # https://leancrew.com/all-this/2014/10/asciifying/
    u = re.sub("[–—/:;,.]", "-", u)  # replace separating punctuation
    a = unidecode(u).lower()  # best ASCII substitutions, lowercased
    a = re.sub(r"[^a-z0-9 -]", "", a)  # delete any other characters
    a = a.replace(" ", "-")  # spaces to hyphens
    a = re.sub(r"-+", "-", a)  # condense repeated hyphens
    return a


def book_data(fn):
    def wrapper(*args, **kwargs):
        book_info = fn(*args, **kwargs)
        book_info["slug"] = slugify(book_info["title"])
        new_entry = {
            "book": {
                key: book_info[key]
                for key in (
                    "title",
                    "author",
                    "publication_year",
                    "slug",
                    "cover_image_url",
                )
            },
        }

        for key in (
            "cover_description",
            "isbn10",
            "isbn13",
            "series",
            "series_position",
        ):
            if value := book_info.get(key):
                new_entry["book"][key] = value

        return new_entry

    return wrapper
