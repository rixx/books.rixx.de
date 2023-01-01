from django.shortcuts import render
from itertools import groupby
from django.views.generic import TemplateView
from django_context_decorator import context
from django.utils.functional import cached_property
from django.utils.timezone import now

from main.models import Review
from main.stats import get_year_stats, get_stats_grid, get_stats_table, get_all_years


class ActiveTemplateView(TemplateView):

    @context
    def active(self):
        return getattr(self, "active", None)


class IndexView(ActiveTemplateView):
    template_name = "index.html"

    @context
    def shelf_books(self):
        return Review.objects.all().order_by("book_author")

    @context
    def reviews(self):
        return Review.objects.all().order_by("-latest_date")[:5]


class YearNavMixin:
    @context
    def all_years(self):
        return get_all_years()


class YearView(YearNavMixin, ActiveTemplateView):
    template_name = "list_reviews.html"
    active = "read"

    @context
    @cached_property
    def year(self):
        return self.kwargs.get("year") or now().year

    @context
    @cached_property
    def current_year(self):
        return self.year == now().year

    @context
    @cached_property
    def title(self):
        return f"Books read in {self.year}"

    @context
    @cached_property
    def reviews(self):
        return Review.objects.all().filter(dates_read__contains=self.year)


class YearInBooksView(YearView):
    template_name = "year_stats.html"
    active = "read"

    @context
    @cached_property
    def title(self):
        return f"{self.year} in books"

    @context
    @cached_property
    def stats(self):
        return get_year_stats(self.year)


class ReviewByAuthor(YearNavMixin, ActiveTemplateView):
    template_name = "list_by_author.html"
    active = "read"

    @context
    @cached_property
    def title(self):
        return "Books by author"

    @context
    @cached_property
    def year(self):
        return "by-author"

    @context
    @cached_property
    def reviews(self):
        authors_with_reviews = sorted(
            [
                (author, list(reviews))
                for (author, reviews) in groupby(
                    Review.objects.all().order_by("book_author"),
                    key=lambda review: review.book_author,
                )
            ],
            key=lambda x: x[0].upper(),
        )
        return sorted(
            [
                (letter, list(authors))
                for letter, authors in groupby(
                    authors_with_reviews,
                    key=lambda pair: (pair[0][0].upper() if pair[0][0].isalpha() else "_"),
                )
            ],
            key=lambda x: (not x[0].isalpha(), x[0].upper()),
        )


class ReviewByTitle(YearNavMixin, ActiveTemplateView):
    template_name = "list_by_title.html"
    active = "read"

    @context
    @cached_property
    def title(self):
        return "Books by title"

    @context
    @cached_property
    def year(self):
        return "by-title"

    @context
    @cached_property
    def reviews(self):
        return sorted(
            [
                (letter, list(reviews))
                for (letter, reviews) in groupby(
                    Review.objects.all().order_by("book_title"),
                    key=lambda review: (
                        review.book_title[0].upper()
                        if review.book_title[0].upper().isalpha()
                        else "_"
                    ),
                )
            ],
            key=lambda x: (not x[0].isalpha(), x[0].upper()),
        )


class ReviewBySeries(YearNavMixin, ActiveTemplateView):
    template_name = "list_by_series.html"
    active = "read"

    @context
    @cached_property
    def title(self):
        return "Books by series"

    @context
    @cached_property
    def year(self):
        return "by-series"

    @context
    @cached_property
    def reviews(self):
        series_reviews = [
            (
                series,
                sorted(
                    list(books),
                    key=lambda book: float(book.book_series_position)
                ),
            )
            for series, books in groupby(
                sorted(
                    Review.objects.all().filter(book_series__isnull=False, book_series_position__isnull=False).exclude(book_series="").exclude(book_series_position=""),
                    key=lambda review: review.book_series,
                ),
                key=lambda review: review.book_series,
            )
        ]
        return sorted(
            [s for s in series_reviews if len(s[1]) > 1],
            key=lambda x: (not x[0][0].isalpha(), x[0].upper()),
        )


class StatsView(ActiveTemplateView):
    template_name = "stats.html"
    active = "stats"

    @context
    def grid(self):
        return get_stats_grid()

    @context
    def table(self):
        return get_stats_table()


class GraphView(ActiveTemplateView):
    template_name = "index.html"
    active = "graph"


class ToReadView(ActiveTemplateView):
    template_name = "index.html"
    active = "to-read"


class ListView(ActiveTemplateView):
    template_name = "list_reviews.html"
    active = "list"


class ListDetail(ActiveTemplateView):
    template_name = "index.html"
    active = "list"


class AuthorView(ActiveTemplateView):
    template_name = "index.html"
    active = "review"


class AuthorEdit(ActiveTemplateView):
    template_name = "index.html"
    active = "review"


class ReviewView(ActiveTemplateView):
    template_name = "index.html"
    active = "review"


class ReviewEdit(ActiveTemplateView):
    template_name = "index.html"
    active = "review"
