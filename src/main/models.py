import re
from unidecode import unidecode
import datetime as dt
import math
import random
from django.core.files.base import ContentFile
from django.utils.functional import cached_property
from django.db import models
from pathlib import Path

REVIEW_ROOT = Path(__file__).parent.parent.parent / "data" / "reviews"




def slugify(text):
    """Convert Unicode string into blog slug.

    Can't use Django's for backwards compatibility – this one turns
    j.k. r into j-k-r, Django's turns it into jk-r."""
    text = re.sub("[–—/:;,.]", "-", text)  # replace separating punctuation
    ascii_text = unidecode(text).lower()  # best ASCII substitutions, lowercased
    ascii_text = re.sub(r"[^a-z0-9 -]", "", ascii_text)  # delete any other characters
    ascii_text = ascii_text.replace(" ", "-")  # spaces to hyphens
    ascii_text = re.sub(r"-+", "-", ascii_text)  # condense repeated hyphens
    return ascii_text


def get_review_path(slug):
    return REVIEW_ROOT / slug


def load_quotes(paths):
    # TODO load quotes
    return []


class ToRead(models.Model):
    __yamdl__ = True
    __yamdl_directory__ = "queue"

    title = models.CharField(max_length=300)
    author = models.CharField(max_length=300)
    shelf = models.CharField(max_length=300)
    pages = models.IntegerField(null=True, blank=True)


class Review(models.Model):
    __yamdl__ = True
    __yamdl_directory__ = "reviews"

    slug = models.CharField(max_length=300)
    title_slug = models.CharField(max_length=300, null=True, blank=True)
    content = models.TextField()
    tldr = models.TextField(null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True)

    related_books = models.JSONField(null=True)
    date_added = models.DateField()
    latest_date = models.DateField()
    dates_read = models.CharField(max_length=300,null=True, blank=True)
    social = models.JSONField(null=True)
    quotes = models.JSONField(null=True)
    did_not_finish = models.BooleanField(default=False)

    book_title = models.CharField(max_length=300)
    book_author = models.CharField(max_length=300)
    book_cover_image_url = models.CharField(max_length=300, null=True, blank=True)
    book_cover_path = models.CharField(max_length=300, null=True, blank=True)
    book_dimensions = models.JSONField(null=True)
    book_goodreads = models.CharField(max_length=30, null=True, blank=True)
    book_isbn10 = models.CharField(max_length=30, null=True, blank=True)
    book_isbn13 = models.CharField(max_length=30, null=True, blank=True)
    book_source = models.CharField(max_length=300, null=True, blank=True)
    book_pages = models.IntegerField(null=True, blank=True)
    book_publication_year = models.IntegerField(null=True, blank=True)
    book_series = models.CharField(max_length=300, null=True, blank=True)
    book_series_position = models.CharField(max_length=5, null=True, blank=True)
    book_spine_color = models.CharField(max_length=7, null=True, blank=True)
    book_owned = models.BooleanField(default=False)

    book_tags = models.JSONField(null=True)

    @cached_property
    def spine(self):
        return Spine(self)

    @cached_property
    def dates_read_list(self):
        return [dt.datetime.strptime(date, "%Y-%m-%d").date() for date in self.dates_read.split(",")]


    @cached_property
    def date_read_lookup(self):
        return {date.year: date for date in self.dates_read_list}

    @cached_property
    def word_count(self):
        return len(self.content.split())

    @cached_property
    def first_paragraph(self):
        print(self.content)
        return self.content.strip().split("\n\n")[0] if self.content else ""

    @classmethod
    def from_yaml(cls, **data):
        data.pop("social", None)
        object_data = {
            "content": data.pop("content"),
            "related_books": data.pop("related_books", []),
            "title_slug": data.get("book").pop("title_slug", None),
            "date_added": data.pop("plan", {}).pop("date_added", None),
            "dates_read": ",".join([d.isoformat() for d in data.get("review", {}).pop("date_read", None) or []]),
        }
        for key in ("rating", "did_not_finish", "tldr"):
            value = data.get("review", {}).pop(key, None)
            if value is not None:
                object_data[key] = value

        for key in (
            "title",
            "author",
            "cover_image_url",
            "dimensions",
            "isbn10",
            "isbn13",
            "pages",
            "goodreads",
            "publication_year",
            "source",
            "series",
            "series_position",
            "spine_color",
            "owned",
            "tags",
        ):
            value = data["book"].pop(key, None)
            if value is not None:
                object_data[f"book_{key}"] = value
        object_data["slug"] = f"{slugify(object_data['book_author'])}/{object_data.get('title_slug') or slugify(object_data['book_title'].split(':')[0].split('.')[0])}"
        if data["book"]:
            raise Exception(f"Unparsed keys in review.book: {', '.join(data['book'].keys())}")
        else:
            data.pop("book")
        if data["review"]:
            raise Exception(f"Unparsed keys in review.review: {', '.join(data['review'].keys())}")
        else:
            data.pop("review", None)
        if data:
            raise Exception(f"Unparsed keys in review: {', '.join(data.keys())} ({object_data['slug']})")
        def to_str(d):
            if isinstance(d, str):
                return d
            return d.isoformat()
        object_data["latest_date"] = sorted([to_str(object_data["date_added"])] + object_data["dates_read"].split(","))[-1]
        path = get_review_path(object_data["slug"])
        quotes = path.glob("quotes.**")
        if quotes:
            object_data["quotes"] = load_quotes(quotes)
        cover = path / "cover.jpg"
        if cover.exists():
            object_data["book_cover_path"] = cover
        result = cls(**object_data)
        result.spine = Spine(result)
        return result


class Spine:
    def __init__(self, review):
        self.review = review
        self.height = self.get_spine_height()
        self.width = self.get_spine_width()
        self.color = self.review.book_spine_color
        self.cover = self.review.book_cover_path
        self.starred = self.review.rating == 5
        # self.labels = []
        # for tag_name in self.review.book_tags:
        #     if tag_name not in TAG_CACHE:
        #         TAG_CACHE[tag_name] = Tag(tag_name)
        #     tag = TAG_CACHE[tag_name]
        #     color = tag.metadata.get("color")
        #     if color:
        #         self.labels.append(tag)

    def random_height(self):
        return random.randint(16, 25)

    def normalize_height(self, height):
        return max(min(int(height * 4), 110), 50)

    def get_spine_height(self):
        height = self.review.book_dimensions.get("height") if self.review.book_dimensions else None
        if not height:
            height = self.random_height()
        return self.normalize_height(height)

    def get_spine_width(self):
        width = self.review.book_dimensions.get("thickness") if self.review.book_dimensions else None
        if not width:
            pages = self.review.book_pages
            if not pages:
                width = random.randint(1, 4) / 2
            else:
                width = (
                    int(pages) * 0.0075
                )  # Factor taken from known thickness/page ratio
        return min(max(int(width * 4), 12), 32)  # Clamp between 12 and 32

    def get_margin(self, tilt):
        tilt = abs(tilt)
        long_side = self.height * math.cos(math.radians(90 - tilt))
        short_side = self.width * math.cos(math.radians(tilt))
        total_required_margin = long_side + short_side - self.width
        return total_required_margin / 2
