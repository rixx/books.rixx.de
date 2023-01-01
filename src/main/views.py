from django.shortcuts import render
from django.views.generic import TemplateView
from django_context_decorator import context
from django.utils.functional import cached_property
from django.utils.timezone import now

from main.models import Review
from main.stats import get_year_stats


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
        first = 1999
        current = now().year
        return list(range(current, first - 1, -1))


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
    def stats(self):
        return get_year_stats(self.year)


class ReviewByAuthor(YearNavMixin, ActiveTemplateView):
    template_name = "index.html"
    active = "read"


class ReviewByTitle(YearNavMixin, ActiveTemplateView):
    template_name = "index.html"
    active = "read"


class ReviewBySeries(YearNavMixin, ActiveTemplateView):
    template_name = "index.html"
    active = "read"


class StatsView(ActiveTemplateView):
    template_name = "index.html"
    active = "stats"


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
