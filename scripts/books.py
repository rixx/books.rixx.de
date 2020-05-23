import datetime as dt
import glob
import os
import re
import shutil
import subprocess
from contextlib import suppress
from pathlib import Path
from urllib.request import urlretrieve

import frontmatter
import inquirer
import requests
from unidecode import unidecode

from . import goodreads


def slugify(text):
    """Convert Unicode string into blog slug."""
    # https://leancrew.com/all-this/2014/10/asciifying/
    text = re.sub("[–—/:;,.]", "-", text)  # replace separating punctuation
    ascii_text = unidecode(text).lower()  # best ASCII substitutions, lowercased
    ascii_text = re.sub(r"[^a-z0-9 -]", "", ascii_text)  # delete any other characters
    ascii_text = ascii_text.replace(" ", "-")  # spaces to hyphens
    ascii_text = re.sub(r"-+", "-", ascii_text)  # condense repeated hyphens
    return ascii_text


def get_date(prompt, default):
    choices = ["today", "yesterday", "another day"]
    if default:
        choices.append(default)
    date = inquirer.list_input(
        message=prompt, choices=choices, carousel=True, default=default
    )
    today = dt.datetime.now()

    if date == "today":
        return today.date()
    if date == "yesterday":
        yesterday = today - dt.timedelta(days=1)
        return yesterday.date()
    if date == default:
        return default

    date = None
    while True:
        date = inquirer.text(message="Which other day?")

        if re.match(r"^\d{4}-\d{2}-\d{2}$", date.strip()):
            return dt.datetime.strptime(date, "%Y-%m-%d").date()
        elif re.match(r"^\d{1,2} [A-Z][a-z]+ \d{4}$", date.strip()):
            return dt.datetime.strptime(date, "%d %B %Y").date()
        else:
            print(f"Unrecognised date: {date}")


class Review:
    def __init__(self, entry_type=None, metadata=None, text=None, path=None):
        self.entry_type = entry_type
        self.path = Path(path) if path else None
        if path:
            self._load_data_from_file()
        elif metadata and entry_type:
            self.metadata = metadata
            self.text = text
        else:
            raise Exception("A review needs metadata or a path!")
        if not self.metadata["book"].get("slug"):
            self.metadata["book"]["slug"] = slugify(self.metadata["book"]["title"])

    def _load_data_from_file(self, path=None):
        post = frontmatter.load(path or self.path)
        self.metadata = post.metadata
        self.text = post.content
        if not self.entry_type:
            self.entry_type = self.entry_type_from_path()

    @property
    def isbn(self):
        return self.metadata["book"].get("isbn13") or self.metadata["book"].get("isbn9")

    def entry_type_from_path(self):
        valid_entry_types = ("reviews", "to-read", "currently-reading")
        entry_type = self.path.parent.name
        if entry_type not in valid_entry_types:
            entry_type = self.path.parent.parent.name
        if entry_type not in valid_entry_types:
            raise Exception(f"Wrong path for review: {entry_type}")
        return entry_type

    def change_entry_type(
        self, entry_type, save=True, push_to_goodreads=False, auth=None
    ):
        old_path = self.path or ""
        if entry_type == self.entry_type:
            return
        if entry_type not in ("reviews", "to-read", "currently-reading"):
            raise Exception(f"Invalid entry_type {entry_type}")
        if entry_type == "reviews" and not self.metadata.get("review", {}).get(
            "date_read"
        ):
            raise Exception("Cannot become a review, no date_read provided!")
        self.entry_type = entry_type
        if save:
            self.save()
        if push_to_goodreads:
            goodreads.change_shelf(review=self, auth=auth)
        subprocess.check_call(["git", "add", self.path, old_path])

    def get_core_path(self):
        if self.entry_type == "reviews":
            year = self.metadata["review"]["date_read"].year
            out_dir = f"reviews/{year}"
        elif self.entry_type == "to-read":
            out_dir = "to-read"
        else:
            out_dir = "currently-reading"
        return Path(out_dir) / self.metadata["book"]["slug"]

    def get_path(self):
        core_path = self.get_core_path()
        out_path = Path("src") / (str(core_path) + ".md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return out_path

    def save(self):
        self.clean()
        current_path = self.get_path()
        if self.path and current_path != self.path and Path(self.path).exists():
            Path(self.path).unlink()
        with open(current_path, "wb") as out_file:
            frontmatter.dump(
                frontmatter.Post(content=self.text, **self.metadata), out_file
            )
            out_file.write(b"\n")
        self.path = current_path
        return current_path

    def edit(self):
        subprocess.check_call([os.environ.get("EDITOR", "vim"), self.path])
        self._load_data_from_file()

    def clean(self):
        if not self.metadata["book"].get("slug"):
            self.metadata["book"]["slug"] = slugify(self.metadata["book"]["title"])
        required = ("title", "author", "slug")
        optional = (
            "publication_year",
            "cover_image",
            "cover_description",
            "cover_image_url",
            "series",
            "series_position",
            "goodreads",
            "slug",
            "pages",
            "isbn10",
            "isbn13",
        )

        if any(not self.metadata["book"].get(key) for key in required):
            raise Exception("Missing required metadata in post")
        superflous = set(self.metadata["book"].keys()) - set(required) - set(optional)
        if superflous:
            raise Exception(f"Superflous keys in post book data: {superflous}")

        if "review" in self.metadata:
            if not self.metadata["review"].get("date_read"):
                raise Exception("A review needs a date_read.")
            superflous = set(self.metadata["review"].keys()) - set(
                ("date_read", "date_started", "format", "rating", "did_not_finish")
            )
            if superflous:
                raise Exception(f"Superflous keys in post review data: {superflous}")

        if "plan" in self.metadata:
            if not self.metadata["plan"].get("date_added"):
                self.metadata["plan"]["date_added"] = dt.datetime.now().date()
            if list(self.metadata["plan"].keys()) != ["date_added"]:
                raise Exception("Unknown keys in post plan data.")

    def download_cover(self, cover_image_url=None, force_new=False):
        destination = Path("src") / "covers"
        destination.mkdir(parents=True, exist_ok=True)
        if not cover_image_url:
            cover_image_url = self.metadata["book"]["cover_image_url"]

        if not force_new and any(
            list(destination.glob(f"{self.metadata['book']['slug']}.{extension}"))
            for extension in ("jpg", "png", "gif")
        ):
            print(f"Cover for {self.metadata['book']['slug']} already exists, passing.")
            return

        filename, headers = urlretrieve(cover_image_url)
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif"}[
            headers["Content-Type"]
        ]
        cover_name = f"{self.metadata['book']['slug']}.{extension}"
        destination = destination / cover_name

        if not destination.exists() or force_new:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(filename, destination)

        self.metadata["book"]["cover_image"] = cover_name
        self.metadata["book"]["cover_image_url"] = cover_image_url
        return cover_name

    def find_openlibrary_cover(self, force_new=False):
        if not self.isbn:
            return False
        with suppress(Exception):
            return self.download_cover(
                f"http://covers.openlibrary.org/b/isbn/{self.isbn}-L.jpg",
                force_new=force_new,
            )
        return False

    def find_google_cover(self, force_new=False):
        if not self.isbn:
            return False
        with suppress(Exception):
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{self.isbn}"
            url = requests.get(url).json()["items"][0]["volumeInfo"]["imageLinks"][
                "thumbnail"
            ]
            return self.download_cover(url, force_new=force_new)
        return False

    def find_goodreads_cover(self, force_new=False):
        if "goodreads.com" in self.metadata["book"]["cover_image_url"]:
            url = self.metadata["book"]["cover_image_url"]
        else:
            data = self.get_goodreads_data()
            url = data["cover_image_url"]
        if url:
            with suppress(Exception):
                return self.download_cover(url, force_new=force_new)
        return False

    def find_goodreads_scrape_cover(self, force_new=False):
        import bs4

        goodreads_id = self.metadata["book"].get("goodreads")
        if not goodreads_id:
            return False
        goodreads_url = f"https://www.goodreads.com/book/show/{goodreads_id}-blabla"

        with suppress(Exception):
            soup = bs4.BeautifulSoup(
                requests.get(goodreads_url).content.decode(), "html.parser"
            )
            url = soup.select_one("#coverImage").attrs["src"]
            return self.download_cover(url, force_new=force_new)
        return False

    def find_cover(
        self, order="openlibrary,google,goodreads,goodreads_scrape", force_new=False
    ):
        order = order.split(",")
        for provider in order:
            result = getattr(self, f"find_{provider}_cover")(force_new=force_new)
            if result is not False:
                return result


def _load_entries(dirpath):
    for path in Path(dirpath).rglob("*.md"):
        yield Review(path=path)


def load_reviews():
    return _load_entries(dirpath="src/reviews")


def load_currently_reading():
    return _load_entries(dirpath="src/currently-reading")


def load_to_read():
    return _load_entries(dirpath="src/to-read")


def load_review_by_slug(slug):
    files = list(glob.glob(f"src/**/{slug}.md")) + list(
        glob.glob(f"src/reviews/**/{slug}.md")
    )
    return Review(path=files[0])


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
            carousel=True,
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


def get_review_info(review=None):
    known_metadata = (review.metadata.get("review") or {}) if review else {}
    date_started = get_date(
        "When did you start reading this book?",
        default=known_metadata.get("date_started"),
    )
    date_read = get_date(
        "When did you finish reading it?", default=known_metadata.get("date_read")
    )
    rating = inquirer.list_input(
        message="What’s your rating?",
        choices=[("⭐⭐⭐⭐⭐", 5), ("⭐⭐⭐⭐", 4), ("⭐⭐⭐", 3), ("⭐⭐", 2), ("⭐", 1)],
        default=known_metadata.get("rating"),
        carousel=True,
    )
    if rating > 3:
        did_not_finish = False
    else:
        did_not_finish = not inquirer.list_input(
            message="Did you finish the book?",
            choices=[("yes", True), ("no", False)],
            carousel=True,
        )

    return {
        "date_started": date_started,
        "date_read": date_read,
        "rating": rating,
        "did_not_finish": did_not_finish,
    }


def create_book(auth):
    choice = inquirer.list_input(
        "Do you want to get the book data from Goodreads, or input it manually?",
        choices=["goodreads", "manually"],
        default="goodreads",
        carousel=True,
    )
    entry_type = inquirer.list_input(
        message="What type of book is this?",
        choices=[
            ("One I’ve read", "reviews"),
            ("One I’m currently reading", "currently-reading"),
            ("One I want to read", "to-read"),
        ],
        carousel=True,
    )

    metadata = {
        "book": get_book_from_input()
        if choice == "manually"
        else goodreads.get_book_from_goodreads(auth=auth)
    }
    if entry_type == "reviews":
        review_info = get_review_info()
        metadata["review"] = {
            key: review_info[key] for key in ("date_read", "rating", "date_started")
        }
        if review_info["did_not_finish"]:
            metadata["review"]["did_not_finish"] = True

    review = Review(metadata=metadata, text="", entry_type=entry_type)
    if review.metadata["book"]["cover_image_url"]:
        review.download_cover()
    else:
        review.find_cover()
    review.save()

    review.edit()

    push_to_goodreads = inquirer.list_input(
        message="Do you want to push this change to Goodreads?",
        choices=[("Yes", True), ("No", False)],
        default=True,
        carousel=True,
    )

    if push_to_goodreads:
        review = Review(path=review.path)  # need to reload
        goodreads.push_to_goodreads(review, auth=auth)

    subprocess.check_call(
        ["git", "add", review.path, review.metadata["book"].get("cover_image") or ""]
    )


def get_review_from_user():
    review = None
    while not review:
        search = (
            inquirer.text(message="What's the book called?")
            .strip()
            .lower()
            .replace(" ", "-")
        )
        try:
            review = load_review_by_slug(f"*{search}*")
        except Exception:
            print("No book like that was found.")
    print()
    print(
        f"Book found: {review.metadata['book']['title']} by {review.metadata['book']['author']}.\nCurrent status: {review.entry_type}"
    )
    right_book = inquirer.list_input(
        message="Is this the book you meant?",
        choices=[("Yes", True), ("No", False)],
        carousel=True,
    )
    if right_book:
        return review
    return get_review_from_user()


def _change_rating(review, push_to_goodreads, auth):
    review.metadata["review"] = get_review_info(review)
    review.change_entry_type(
        "reviews", save=True, push_to_goodreads=push_to_goodreads, auth=auth
    )
    review.edit()
    if push_to_goodreads:
        goodreads.push_to_goodreads(review=review, auth=auth)


def _change_to_currently_reading(review, push_to_goodreads, auth):
    review_data = review.metadata.get("review") or {}
    review_data["date_started"] = dt.datetime.now().date()
    review.change_entry_type(
        "currently-reading", save=True, push_to_goodreads=push_to_goodreads, auth=auth
    )


def _change_to_tbr(review, push_to_goodreads, auth):
    review.change_entry_type(
        "to-read", save=True, push_to_goodreads=push_to_goodreads, auth=auth
    )


def _change_remove(review, push_to_goodreads, auth):
    review.path.unlink()
    if push_to_goodreads:
        goodreads.remove_review(review=review, auth=auth)


def _change_manually(review, push_to_goodreads, auth):
    review.edit()
    if push_to_goodreads:
        goodreads.push_to_goodreads(review=review, auth=auth)


def _change_cover(review, push_to_goodreads, auth):
    old_cover_url = review.metadata["book"]["cover_image_url"]
    source = inquirer.list_input(
        message="Where do you want to retrieve the cover image from?",
        choices=[
            ("Goodreads", "goodreads"),
            ("Goodreads web scraping", "goodreads_scrape"),
            ("Google APIs", "google"),
            ("OpenLibrary", "openlibrary"),
            ("Custom URL", "manually"),
        ],
        carousel=True,
    )
    if source == "manually":
        url = inquirer.text(message="Cover image URL")
        review.download_cover(url, force_new=True)
    else:
        review.find_cover(source, force_new=True)
    if review.metadata["book"]["cover_image_url"] != old_cover_url:
        print(
            f"Successfully downloaded new cover image! You can look at it at src/covers/{review.metadata['book']['cover_image']}"
        )
        review.save()
    else:
        print("Couldn't find a new cover, sorry!")


def change_book(auth):
    review = get_review_from_user()
    while True:
        action = inquirer.list_input(
            message="What do you want to do with this book?",
            choices=[
                ("Rate and review", "rating"),
                ("Mark as currently reading", "to_currently_reading"),
                ("Mark as to be read", "to_tbr"),
                ("Remove from library", "remove"),
                ("Edit manually", "manually"),
                ("Change cover image", "cover"),
                ("Choose different book", "book"),
                ("Quit", "quit"),
            ],
            carousel=True,
        )
        if action == "quit":
            return
        if action == "book":
            return change_book(auth=auth)
        push_to_goodreads = False
        if review.metadata["book"].get("goodreads") and action != "cover":
            push_to_goodreads = inquirer.list_input(
                message="Do you want to push this change to Goodreads?",
                choices=[("Yes", True), ("No", False)],
                default=True,
                carousel=True,
            )
        globals()[f"_change_{action}"](
            review=review, push_to_goodreads=push_to_goodreads, auth=auth
        )
        if action == "remove":
            return change_book(auth=auth)
