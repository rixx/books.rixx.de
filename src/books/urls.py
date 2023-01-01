"""books URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from main import views


urlpatterns = [
    path("", views.IndexView.as_view()),
    path("reviews/", views.YearView.as_view()),
    path("reviews/<int:year>/", views.YearView.as_view()),
    path("reviews/<int:year>/stats/", views.YearInBooksView.as_view()),
    path("reviews/by-author/", views.ReviewByAuthor.as_view()),
    path("reviews/by-title/", views.ReviewByTitle.as_view()),
    path("reviews/by-series/", views.ReviewBySeries.as_view()),
    path("stats/", views.StatsView.as_view()),
    path("graph/", views.GraphView.as_view()),
    path("graph.json", views.graph_data),
    path("search.json", views.search_data),
    path("to-read/", views.ToReadView.as_view()),
    path("lists/", views.ListView.as_view()),
    path("lists/<slug:tag>/", views.ListDetail.as_view()),
    path("<slug:author>/", views.AuthorView.as_view()),
    path("<slug:author>/edit", views.AuthorEdit.as_view()),
    path("<slug:author>/<slug:book>/", views.ReviewView.as_view()),
    path("<slug:author>/<slug:book>/edit", views.ReviewEdit.as_view()),
]
