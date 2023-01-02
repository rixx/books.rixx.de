from django.shortcuts import render
import networkx as nx
from itertools import groupby
from django.db.models import Sum
from django.views.generic import TemplateView
from django_context_decorator import context
from django.utils.functional import cached_property
from django.http import JsonResponse, HttpResponseNotFound, FileResponse, HttpResponse
from django.utils.timezone import now

from main.models import Review, ToRead
from main.stats import get_year_stats, get_stats_grid, get_stats_table, get_all_years, get_graph, get_nodes, get_edges


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

def feed_view(request):
    from django.template import loader
    template = loader.get_template('feed.atom')
    context = {"reviews": Review.objects.all().order_by("-latest_date")[:20]}
    headers = {
        "Content-Type": "application/atom+xml",
    }
    return HttpResponse(template.render(context, request), headers=headers)


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
        return sorted(Review.objects.all().filter(dates_read__contains=self.year), key=lambda review: review.date_read_lookup[self.year], reverse=True)


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
    template_name = "graph.html"
    active = "graph"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        graph = get_graph()
        context["node_count"] = graph.number_of_nodes()
        context["edge_count"] = graph.number_of_edges()
        context["missing_nodes"] =Review.objects.all().count() - graph.number_of_nodes()
        context["parts"]=nx.number_connected_components(graph)
        context["is_connected"] = nx.is_connected(graph)
        return context


def graph_data(request):
    graph = get_graph()
    return JsonResponse({"nodes": get_nodes(graph), "links": get_edges(graph)})


def search_data(request):
    # TODO tag search
    search_tags = [
        # {
        #     "slug": tag.slug,
        #     "name": tag.metadata.get("title") or tag.slug,
        #     "search": (tag.metadata.get("title") or tag.slug).lower().split(),
        # }
        # for tag in tags.keys()
    ]
    return JsonResponse({"books": get_nodes(), "tags": []})


class ReviewView(ActiveTemplateView):
    template_name = "review.html"
    active = "review"

    @context
    @cached_property
    def review(self):
        review = Review.objects.get(slug=f"{self.kwargs['author']}/{self.kwargs['book']}")
        for related in (review.related_books or []):
            related["review"] = Review.objects.get(slug=related["book"])
        return review

class ReviewCoverView(ReviewView):
    def dispatch(self, *args, **kwargs):
        if not self.review.book_cover_path:
            return HttpResponseNotFound()
        return FileResponse(open(self.review.book_cover_path, "rb"))


class ReviewEdit(ReviewView):
    template_name = "index.html"
    active = "review"


class QueueView(ActiveTemplateView):
    template_name = "list_queue.html"
    active = "queue"

    @context
    def shelves(self):
        shelves = {name: books for (name, books) in groupby(ToRead.objects.all(), key=lambda x: x.shelf)}
        shelf_order = sorted(ToRead.objects.all().values_list("shelf", flat=True).distinct())
        return [
            {
                "name": shelf,
                "books": ToRead.objects.all().filter(shelf=shelf),
                "page_count": ToRead.objects.all().filter(shelf=shelf).aggregate(page_count=Sum("pages"))["page_count"],
            }
            for shelf in shelf_order
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_books"] = ToRead.objects.all().count()
        context["total_pages"] = ToRead.objects.all().aggregate(page_count=Sum("pages"))["page_count"]
        past_year_reviews = Review.objects.all().filter(dates_read__contains=now().year - 1)
        context["past_year_books"] = past_year_reviews.count()
        context["past_year_pages"] = past_year_reviews.aggregate(page_count=Sum("book_pages"))["page_count"]
        context["factor_books"] = round(context["total_books"] / context["past_year_books"], 1)
        context["factor_pages"] = round(context["total_pages"] / context["past_year_pages"], 1)
        return context


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


class ReviewCreate(ReviewView):
    template_name = "index.html"
    active = "review"
