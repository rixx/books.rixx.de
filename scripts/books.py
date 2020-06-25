import datetime as dt
import glob
import os
import re
import shutil
import subprocess
from contextlib import suppress
from pathlib import Path
from urllib.request import urlretrieve

import click
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
            click.echo(click.style(f"Unrecognised date: {date}", fg="red"))


class Tag:
    def __init__(self, name):
        data = frontmatter.load(f"src/tags/{name}.md")
        self.metadata = data.metadata
        self.text = data.content
        self.slug = name


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
        try:
            post = frontmatter.load(path or self.path)
        except Exception as e:
            raise Exception(
                f"Error while loading review from {path or self.path}!\n{e}"
            )
        self.metadata = post.metadata
        self.text = post.content
        if not self.entry_type:
            self.entry_type = self.entry_type_from_path()

    @property
    def isbn(self):
        return self.metadata["book"].get("isbn13") or self.metadata["book"].get("isbn9")

    @property
    def relevant_date(self):
        if self.entry_type == "reviews":
            result = self.metadata["review"]["date_read"]
        else:
            result = self.metadata["plan"]["date_added"]
        if isinstance(result, dt.date):
            return result
        return dt.datetime.strptime(result, "%Y-%m-%d").date()

    def entry_type_from_path(self):
        valid_entry_types = ("reviews", "to-read")
        entry_type = self.path.parent.name
        if entry_type not in valid_entry_types:
            entry_type = self.path.parent.parent.name
        if entry_type not in valid_entry_types:
            raise Exception(f"Wrong path for review: {entry_type}")
        return entry_type

    def change_entry_type(
        self, entry_type, save=True, push_to_goodreads=False,
    ):
        old_path = self.path or ""
        if entry_type != self.entry_type:
            if entry_type not in ("reviews", "to-read"):
                raise Exception(f"Invalid entry_type {entry_type}")
            if entry_type == "reviews" and not self.metadata.get("review", {}).get(
                "date_read"
            ):
                raise Exception("Cannot become a review, no date_read provided!")
            self.entry_type = entry_type
        if save:
            self.save()
        if push_to_goodreads:
            goodreads.change_shelf(review=self)
        subprocess.check_call(["git", "add", self.path, old_path])

    def get_core_path(self):
        if self.entry_type == "reviews":
            year = self.metadata["review"]["date_read"].year
            out_dir = f"reviews/{year}"
        elif self.entry_type == "to-read":
            out_dir = "to-read"
        return Path(out_dir) / self.metadata["book"]["slug"]

    def get_path(self):
        core_path = self.get_core_path()
        out_path = Path("src") / (str(core_path) + ".md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        return out_path

    def add_tag(self, tag, save=True):
        current_tags = self.metadata["book"].get("tags", [])
        if tag in current_tags:
            return
        self.metadata["book"]["tags"] = sorted(current_tags + [tag])
        if save:
            self.save()

    def remove_tag(self, tag, save=True):
        current_tags = self.metadata["book"].get("tags", [])
        if tag not in current_tags:
            return
        self.metadata["book"]["tags"] = [tag for tag in current_tags if tag != tag]
        if save:
            self.save()

    def update_tags(self):
        available_tags = sorted([path.stem for path in Path("src/tags").glob("*.md")])
        current_tags = self.metadata["book"].get("tags", [])

        self.metadata["book"]["tags"] = inquirer.prompt(
            [
                inquirer.Checkbox(
                    name="tags",
                    message=f"Tags to apply to {self.metadata['book']['title']}",
                    choices=available_tags,
                    default=current_tags,
                ),
            ]
        )["tags"]

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
        self.save()

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
            "tags",
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
                (
                    "date_read",
                    "date_started",
                    "format",
                    "rating",
                    "did_not_finish",
                    "tldr",
                )
            )
            if superflous:
                raise Exception(f"Superflous keys in post review data: {superflous}")

        if "plan" in self.metadata:
            if not self.metadata["plan"].get("date_added"):
                self.metadata["plan"]["date_added"] = dt.datetime.now().date()
            if list(self.metadata["plan"].keys()) != ["date_added"]:
                raise Exception("Unknown keys in post plan data.")
        else:
            self.metadata["plan"] = {"date_added": dt.datetime.now().date()}

        if "social" in self.metadata:
            superflous = set(self.metadata["social"].keys()) - set(
                "twitter", "mastodon"
            )

    def download_cover(self, cover_image_url=None, force_new=False):
        destination = Path("src") / "covers"
        destination.mkdir(parents=True, exist_ok=True)
        if not cover_image_url:
            cover_image_url = self.metadata["book"]["cover_image_url"]

        if not force_new and any(
            list(destination.glob(f"{self.metadata['book']['slug']}.{extension}"))
            for extension in ("jpg", "png", "gif")
        ):
            click.echo(
                f"Cover for {self.metadata['book']['slug']} already exists, passing."
            )
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
                self.show_cover()
                return result

    def show_cover(self):
        subprocess.check_call(
            ["xdg-open", Path("src/covers") / self.metadata["book"]["cover_image"]]
        )


def _load_entries(dirpath):
    for path in Path(dirpath).rglob("*.md"):
        yield Review(path=path)


def load_reviews():
    return _load_entries(dirpath="src/reviews")


def load_to_read():
    return _load_entries(dirpath="src/to-read")


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
        "When did you finish reading it?",
        default=known_metadata.get("date_read") or date_started,
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


def create_book(search_term=None):
    choice = inquirer.list_input(
        "Do you want to get the book data from Goodreads, or input it manually?",
        choices=["goodreads", "manually"],
        default="goodreads",
        carousel=True,
    )
    entry_type = inquirer.list_input(
        message="What type of book is this?",
        choices=[("One I’ve read", "reviews"), ("One I want to read", "to-read"),],
        carousel=True,
    )

    metadata = {
        "book": get_book_from_input()
        if choice == "manually"
        else goodreads.get_book_from_goodreads(search_term=search_term)
    }
    if entry_type == "reviews":
        review_info = get_review_info()
        metadata["review"] = {
            key: review_info[key] for key in ("date_read", "rating", "date_started")
        }
        if review_info["did_not_finish"]:
            metadata["review"]["did_not_finish"] = True

    review = Review(metadata=metadata, text="", entry_type=entry_type)
    review.update_tags()
    if review.metadata["book"]["cover_image_url"]:
        review.download_cover()
        review.show_cover()
        if not inquirer.list_input(
            message="Cover ok?", choices=(True, False), carousel=True
        ):
            review.find_cover(force_new=True)
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
        goodreads.push_to_goodreads(review)

    subprocess.check_call(
        [
            "git",
            "add",
            review.path,
            Path("src/covers") / (review.metadata["book"].get("cover_image") or ""),
        ]
    )


def get_review_from_user():
    review = None
    while not review:
        original_search = inquirer.text(message="What's the book called?")
        search = original_search.strip().lower().replace(" ", "-")
        files = list(glob.glob(f"src/**/*{search}*.md")) + list(
            glob.glob(f"src/reviews/**/*{search}*.md")
        )
        if len(files) == 0:
            click.echo(click.style("No book like that was found.", fg="red"))
            progress = inquirer.list_input(
                "Do you want to add it as new book instead, or continue searching?",
                choices=[("New book", "new"), ("Continue", "continue")],
            )
            if progress == "new":
                return create_book(search_term=original_search)
            continue

        reviews = [Review(path=path) for path in files]
        options = [
            (
                f"{review.metadata['book']['title']} by {review.metadata['book']['author']} ({review.entry_type})",
                review,
            )
            for review in reviews
        ]
        options += [
            ("Try a different search", "again"),
            ("Add a new book instead", "new"),
        ]
        choice = inquirer.list_input(
            f"Found {len(reviews)} books. Which one's yours?",
            choices=options,
            carousel=True,
        )
        if choice == "new":
            return create_book(search_term=original_search)
        if choice == "again":
            continue
        return choice
    return get_review_from_user()


def _change_rating(review, push_to_goodreads):
    review.metadata["review"] = get_review_info(review)
    review.update_tags()
    review.change_entry_type("reviews", save=True, push_to_goodreads=push_to_goodreads)
    review.edit()
    if push_to_goodreads:
        goodreads.push_to_goodreads(review=review)


def _change_to_tbr(review, push_to_goodreads):
    review.change_entry_type(
        "to-read", save=True, push_to_goodreads=push_to_goodreads,
    )


def _change_remove(review, push_to_goodreads):
    review.path.unlink()
    if push_to_goodreads:
        goodreads.remove_review(review=review)


def _change_manually(review, push_to_goodreads):
    review.edit()
    if push_to_goodreads:
        goodreads.push_to_goodreads(review=review)


def _change_cover(review, push_to_goodreads):
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
        review.show_cover()
    else:
        review.find_cover(source, force_new=True)
    if review.metadata["book"]["cover_image_url"] != old_cover_url:
        click.echo(click.style("Successfully downloaded new cover image!", fg="green"))
        review.save()
    else:
        click.echo(click.style("Couldn't find a new cover, sorry!", fg="red"))


def change_book():
    review = get_review_from_user()
    while True:
        action = inquirer.list_input(
            message="What do you want to do with this book?",
            choices=[
                ("Rate and review", "rating"),
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
            return change_book()
        push_to_goodreads = False
        if review.metadata["book"].get("goodreads") and action != "cover":
            push_to_goodreads = inquirer.list_input(
                message="Do you want to push this change to Goodreads?",
                choices=[("Yes", True), ("No", False)],
                default=True,
                carousel=True,
            )
        globals()[f"_change_{action}"](
            review=review, push_to_goodreads=push_to_goodreads,
        )
        if action == "remove":
            return change_book()


def change_tags(**kwargs):
    reviews = sorted(
        load_reviews(),
        key=lambda r: (r.metadata["book"]["author"], r.metadata["book"]["title"]),
    )
    tags = sorted([path.stem for path in Path("src/tags").glob("*.md")])

    answers = inquirer.prompt(
        [
            inquirer.List(
                name="tag",
                message="Which tag do you want to work on?",
                choices=tags,
                carousel=True,
            ),
            inquirer.Checkbox(
                name="include",
                message="Show only books with these tags (empty for all)",
                choices=tags + ["no tags"],
            ),
            inquirer.Checkbox(
                name="exclude", message="Exclude books with these tags", choices=tags,
            ),
        ]
    )

    tag = answers["tag"]
    include = answers["include"]
    exclude = answers["exclude"]

    if include:
        include_empty = "no tags" in include
        reviews = [
            r
            for r in reviews
            if (include_empty and not r.metadata["book"].get("tags"))
            or any(tag in include for tag in r.metadata["book"].get("tags", []))
        ]

    if exclude:
        reviews = [
            r
            for r in reviews
            if not any(tag in exclude for tag in r.metadata["book"].get("tags", []))
        ]

    longest_author = max(len(r.metadata["book"]["author"]) for r in reviews) + 2
    longest_title = max(len(r.metadata["book"]["title"]) for r in reviews) + 2

    def review_string(r):
        result = r.metadata["book"]["author"].ljust(longest_author) + r.metadata[
            "book"
        ]["title"].ljust(longest_title)
        tags = r.metadata["book"].get("tags")
        if tags:
            tag_string = "".join([f"[{tag}]" for tag in tags])
            result = f"{result} {tag_string}"
        return result

    tagged = inquirer.prompt(
        [
            inquirer.Checkbox(
                name="tagged",
                message=f"Books tagged as {tag}",
                choices=[(review_string(r), r) for r in reviews],
                default=[
                    r for r in reviews if tag in r.metadata["book"].get("tags", [])
                ],
            )
        ]
    )["tagged"]

    for review in reviews:
        if review in tagged:
            review.add_tag(tag)
        else:
            review.remove_tag(tag)
