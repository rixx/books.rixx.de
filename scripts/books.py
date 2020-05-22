import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlretrieve

import attr
import frontmatter
import hyperlink
import inquirer

from . import goodreads, utils


@attr.s
class Book:
    title = attr.ib()
    author = attr.ib()
    publication_year = attr.ib()
    cover_image = attr.ib(default="")
    cover_description = attr.ib(default="")
    cover_image_url = attr.ib(default="")

    series = attr.ib(default=None)
    series_position = attr.ib(default=None)

    goodreads = attr.ib(default="")
    slug = attr.ib(default="")
    pages = attr.ib(default="")

    isbn10 = attr.ib(default="")
    isbn13 = attr.ib(default="")


@attr.s
class Review:
    text = attr.ib()
    date_read = attr.ib()
    date_started = attr.ib(default=None)
    format = attr.ib(default=None)
    rating = attr.ib(default=None)
    did_not_finish = attr.ib(default=False)


@attr.s
class ReviewEntry:
    path = attr.ib()
    book = attr.ib()
    review = attr.ib()

    def out_path(self):
        name = self.path.with_suffix("").name
        return Path(f"reviews/{name}")


@attr.s
class CurrentlyReading:
    text = attr.ib()


@attr.s
class CurrentlyReadingEntry:
    path = attr.ib()
    book = attr.ib()
    reading = attr.ib()


def _parse_date(value):
    if isinstance(value, dt.date):
        return value
    else:
        return dt.datetime.strptime(value, "%Y-%m-%d").date()


@attr.s
class Plan:
    text = attr.ib()
    date_added = attr.ib(converter=_parse_date)


@attr.s
class PlanEntry:
    path = attr.ib()
    book = attr.ib()
    plan = attr.ib()


def get_review_entry_from_path(path):
    post = frontmatter.load(path)

    kwargs = {}
    for attr_name in Book.__attrs_attrs__:
        try:
            kwargs[attr_name.name] = post["book"][attr_name.name]
        except KeyError:
            pass

    book = Book(**kwargs)
    review = Review(**post["review"], text=post.content)
    return ReviewEntry(path=path, book=book, review=review)


def get_reading_entry_from_path(path):
    post = frontmatter.load(path)

    book = Book(**post["book"])
    reading = CurrentlyReading(text=post.content)

    return CurrentlyReadingEntry(path=path, book=book, reading=reading)


def get_plan_entry_from_path(path):
    post = frontmatter.load(path)
    book = Book(**post["book"])
    plan = Plan(date_added=post["plan"]["date_added"], text=post.content)
    return PlanEntry(path=path, book=book, plan=plan)


def get_entries(dirpath, constructor):
    for dirpath, _, filenames in os.walk(dirpath):
        for f in filenames:
            if not f.endswith(".md"):
                continue

            path = Path(dirpath) / f

            try:
                yield constructor(path)
            except Exception:
                print(f"Error parsing {path}", file=sys.stderr)
                raise


def get_reviews():
    return get_entries(dirpath="src/reviews", constructor=get_review_entry_from_path)


def get_currently_reading():
    return get_entries(
        dirpath="src/currently-reading", constructor=get_reading_entry_from_path
    )


def get_to_read():
    return get_entries(dirpath="src/to-read", constructor=get_plan_entry_from_path)


@utils.book_data
def get_book_from_input():
    questions = [
        inquirer.Text("title", message="What’s the title of the book?"),
        inquirer.Text("author", message="Who’s the author?"),
        inquirer.Text("publication_year", message="When was it published?"),
        inquirer.Text("cover_image_url", message="What’s the cover URL?"),
        inquirer.Text("cover_description", message="What’s the cover?"),
        inquirer.Text("isbn10", message="Do you know the ISBN-10?"),
        inquirer.Text("isbn13", message="Do you know the ISBN-13?"),
        inquirer.Number("pages", message="How many pages does the book have?"),
        inquirer.List(
            "series",
            message="Is this book part of a series?",
            choices=[("Yes", True), ("No", False)],
            default=False,
        ),
    ]

    answers = inquirer.prompt(questions)

    if answers["series"]:
        series_questions = [
            inquirer.Text("series", message="Which series does this book belong to?"),
            inquirer.Text(
                "series_position",
                message="Which position does the book have in its series?",
            ),
        ]
        answers = {**answers, **inquirer.prompt(series_questions)}
    return answers


def get_date(prompt):
    date_read = inquirer.list_input(
        message=prompt, choices=["today", "yesterday", "another day"],
    )
    today = dt.datetime.now()

    if date_read == "today":
        return today.date()
    if date_read == "yesterday":
        yesterday = today - dt.timedelta(days=1)
        return yesterday.date()
    date_read = None
    while True:
        date_read = inquirer.text(message="When did you finish reading it?")

        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_read.strip()):
            return dt.datetime.strptime(date_read, "%Y-%m-%d").date()
        elif re.match(r"^\d{1,2} [A-Z][a-z]+ \d{4}$", date_read.strip()):
            return dt.datetime.strptime(date_read, "%d %B %Y").date()
        else:
            print(f"Unrecognised date: {date_read}")


def get_review_info(date_started=None):
    if not date_started:
        date_started = get_date("When did you start reading this book?")
    date_read = get_date("When did you finish reading it?")
    rating = inquirer.list_input(
        message="What’s your rating?",
        choices=[("⭐⭐⭐⭐⭐", 5), ("⭐⭐⭐⭐", 4), ("⭐⭐⭐", 3), ("⭐⭐", 2), ("⭐", 1)],
    )
    if rating > 3:
        did_not_finish = False
    else:
        did_not_finish = not inquirer.list_input(
            message="Did you finish the book?", choices=[("yes", True), ("no", False)],
        )

    return {
        "date_started": date_started,
        "date_read": date_read,
        "rating": rating,
        "did_not_finish": did_not_finish,
    }


def save_cover(slug, cover_image_url, force_new=False):

    destination = Path("src") / "covers"
    destination.mkdir(parents=True, exist_ok=True)

    if not force_new and any(
        list(destination.glob(f"{slug}.{extension}"))
        for extension in ("jpg", "png", "gif")
    ):
        print(f"Cover for {slug} already exists, passing.")
        return

    try:
        filename, headers = urlretrieve(cover_image_url)
    except Exception as e:
        if "covers.openlibrary.org" in cover_image_url:
            time.sleep(300)
            filename, headers = urlretrieve(cover_image_url)
        raise e

    if headers["Content-Type"] == "image/jpeg":
        extension = ".jpg"
    elif headers["Content-Type"] == "image/png":
        extension = ".png"
    elif headers["Content-Type"] == "image/gif":
        extension = ".gif"
    else:
        raise Exception(f"Unknown cover format: {headers}")

    url_path = hyperlink.URL.from_text(cover_image_url).path
    extension = os.path.splitext(url_path[-1])[-1]

    cover_name = f"{slug}{extension}"
    destination = destination / cover_name

    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(filename, destination)

    return cover_name


def get_out_path(entry, entry_type):
    if entry_type == "review":
        year = entry["review"]["date_read"].year
        out_dir = f"reviews/{year}"
    elif entry_type == "to_read":
        entry["plan"] = {
            "date_added": dt.datetime.now().date(),
        }
        out_dir = "to-read"
    else:
        out_dir = "currently-reading"
    out_path = Path("src") / out_dir / f"{entry['book']['slug']}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def add_book(auth):
    choice = inquirer.list_input(
        "Do you want to get the book data from Goodreads, or input it manually?",
        choices=["goodreads", "manually"],
        default="goodreads",
    )
    entry_type = inquirer.list_input(
        message="What type of book is this?",
        choices=[
            ("One I’ve read", "review"),
            ("One I’m currently reading", "currently_reading"),
            ("One I want to read", "to_read"),
        ],
    )

    new_entry = (
        get_book_from_input()
        if choice == "manually"
        else goodreads.get_book_from_goodreads(auth=auth)
    )
    if entry_type == "review":
        review_info = get_review_info()
        new_entry["review"] = {key: review_info[key] for key in ("date_read", "rating")}
        if review_info["did_not_finish"]:
            new_entry["review"]["did_not_finish"] = True

    new_entry["book"]["cover_image"] = save_cover(
        slug=new_entry["book"]["slug"],
        cover_image_url=new_entry["book"]["cover_image_url"],
    )

    out_path = get_out_path(new_entry, entry_type)

    with open(out_path, "wb") as out_file:
        frontmatter.dump(frontmatter.Post(content="", **new_entry), out_file)
        out_file.write(b"\n")

    subprocess.check_call([os.environ.get("EDITOR", "vim"), out_path])

    if new_entry["book"].get("goodreads"):
        if inquirer.list_input(
            message="Do you want to push these changes to Goodreads?",
            choices=[("yes", True), ("no", False)],
        ):
            goodreads.push_to_goodreads(
                data=new_entry, path=out_path, auth=auth, entry_type=entry_type
            )


def change_book(auth):
    # TODO: load all books
    # TODO: search / suggest
    # TODO: change state or open editor
    # TODO update on goodreads, if wanted
    pass
