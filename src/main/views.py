from django.shortcuts import render
from django.views.generic import TemplateView


class ActiveTemplateView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active"] = getattr(self, "active", None)
        return context


class IndexView(ActiveTemplateView):
    template_name = "index.html"


class YearView(ActiveTemplateView):
    template_name = "year.html"
    active = "read"


class YearInBooksView(ActiveTemplateView):
    template_name = "year.html"
    active = "read"


class ReviewByAuthor(ActiveTemplateView):
    template_name = "index.html"
    active = "read"


class ReviewByTitle(ActiveTemplateView):
    template_name = "index.html"
    active = "read"


class ReviewBySeries(ActiveTemplateView):
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
    template_name = "index.html"
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
