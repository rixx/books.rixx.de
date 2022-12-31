from django.db import models
from django.utils.text import slugify


class Review(models.Model):
    __yamdl__ = True
    __yamdl_directory__ = "reviews"

    slug = models.CharField(max_length=300)
    content = models.TextField()
    related_books = models.JSONField(null=True)
    date_added = models.DateField()

    book_title = models.CharField(max_length=300)
    book_author = models.CharField(max_length=300)
    book_cover_image_url = models.CharField(max_length=300, null=True, blank=True)
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
    plan_dates_read = models.JSONField(null=True)

    @classmethod
    def from_yaml(cls, **data):
        object_data = {
            "content": data.pop("content"),
            "related_books": data.pop("related_books", []),
            "date_added": data.pop("plan", {}).pop("date_added", None),
        }
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
        if data["book"]:
            raise Exception(f"Unparsed keys in review.book: {', '.join(data['book'].keys())}")
        object_data["slug"] = f"{slugify(object_data['book_author'])}/{slugify(object_data['book_title'])}"
        return cls(**object_data)
