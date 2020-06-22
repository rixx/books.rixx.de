import datetime as dt
import hashlib
import itertools
import os
import pathlib
import statistics
import subprocess
import uuid
from collections import defaultdict
from functools import partial

import markdown
import smartypants
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown.extensions.smarty import SmartyExtension
from PIL import Image

from . import books


def rsync(source, destination):
    subprocess.check_call(["rsync", "--recursive", "--delete", source, destination])


def render_markdown(text):
    return markdown.markdown(text, extensions=[SmartyExtension()])


def render_date(date_value):
    if isinstance(date_value, dt.date):
        return date_value.strftime("%Y-%m-%d")
    return date_value


def get_relevant_date(review):
    if review.entry_type == "reviews":
        result = review.metadata["review"]["date_read"]
    else:
        result = review.metadata["plan"]["date_added"]
    if isinstance(result, dt.date):
        return result
    return dt.datetime.strptime(result, "%Y-%m-%d").date()


def render_page(template_name, path, env=None, **context):
    template = env.get_template(template_name)
    html = template.render(**context)
    out_path = pathlib.Path("_html") / path
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)


def render_feed(events, path, render):
    for event in events:
        m = hashlib.md5()
        m.update(
            f"{event.metadata['book']['title']}:{event.entry_type}:{event.relevant_date}:{event.metadata['book'].get('goodreads', '')}".encode()
        )
        event.feed_uuid = str(uuid.UUID(m.hexdigest()))

    render("feed.atom", path, events=events)


def _create_new_thumbnail(src_path, dst_path):
    dst_path.parent.mkdir(exist_ok=True, parents=True)

    im = Image.open(src_path)

    if im.width > 240 and im.height > 240:
        im.thumbnail((240, 240))
    im.save(dst_path)


def thumbnail_1x(name):
    path = pathlib.Path(name)
    return f"{path.stem}_1x{path.suffix}"


def _create_new_square(src_path, square_path):
    square_path.parent.mkdir(exist_ok=True, parents=True)

    im = Image.open(src_path)
    im.thumbnail((240, 240))

    dimension = max(im.size)

    new = Image.new("RGB", size=(dimension, dimension), color=(255, 255, 255))

    if im.height > im.width:
        new.paste(im, box=((dimension - im.width) // 2, 0))
    else:
        new.paste(im, box=(0, (dimension - im.height) // 2))

    new.save(square_path)


def create_thumbnails():
    for image_name in os.listdir("src/covers"):
        src_path = pathlib.Path("src/covers") / image_name
        dst_path = pathlib.Path("_html/thumbnails") / image_name

        if not dst_path.exists() or src_path.stat().st_mtime > dst_path.stat().st_mtime:
            _create_new_thumbnail(src_path, dst_path)

        square_path = pathlib.Path("_html/squares") / image_name

        if (
            not square_path.exists()
            or src_path.stat().st_mtime > square_path.stat().st_mtime
        ):
            _create_new_square(src_path, square_path)


def isfloat(value):
    try:
        float(value)
        return True
    except Exception:
        return False


def median_year(reviews):
    years = [
        int(review.metadata["book"].get("publication_year"))
        for review in reviews
        if review.metadata["book"].get("publication_year")
    ]
    return int(statistics.median(years))


def build_site(**kwargs):
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["render_markdown"] = render_markdown
    env.filters["render_date"] = render_date
    env.filters["smartypants"] = smartypants.smartypants
    env.filters["thumbnail_1x"] = thumbnail_1x
    render = partial(render_page, env=env)

    create_thumbnails()

    rsync(source="src/covers/", destination="_html/covers/")
    rsync(source="static/", destination="_html/static/")

    this_year = dt.datetime.now().year
    all_reviews = list(books.load_reviews())
    all_plans = list(books.load_to_read())
    all_events = all_plans + all_reviews

    for element in all_events:
        element.relevant_date = get_relevant_date(element)

    all_reviews = sorted(all_reviews, key=lambda x: x.relevant_date, reverse=True)
    all_plans = sorted(all_plans, key=lambda x: x.relevant_date, reverse=True)
    all_events = sorted(all_events, key=lambda x: x.relevant_date, reverse=True)

    # Render single review pages

    for review in all_reviews:
        render(
            "review.html",
            review.get_core_path() / "index.html",
            review=review,
            title=f"Review of {review.metadata['book']['title']}",
            active="read",
        )

    # Render the "all reviews" page

    all_years = sorted(
        list(set(review.relevant_date.year for review in all_reviews)), reverse=True,
    )
    for (year, reviews) in itertools.groupby(
        all_reviews, key=lambda rev: rev.relevant_date.year
    ):
        kwargs = {
            "reviews": list(reviews),
            "all_years": all_years,
            "year": year,
            "current_year": (year == this_year),
            "title": "Books I’ve read",
            "active": "read",
        }
        render(
            "list_reviews.html", f"reviews/{year or 'other'}/index.html", **kwargs,
        )
        if year == this_year:
            render(
                "list_reviews.html", "reviews/index.html", **kwargs,
            )

    # Render the "by title" page

    title_reviews = sorted(
        [
            (letter, list(reviews))
            for (letter, reviews) in itertools.groupby(
                sorted(all_reviews, key=lambda rev: rev.metadata["book"]["title"]),
                key=lambda rev: (
                    rev.metadata["book"]["title"][0].upper()
                    if rev.metadata["book"]["title"][0].isalpha()
                    else "_"
                ),
            )
        ],
        key=lambda x: (not x[0].isalpha(), x[0].upper()),
    )
    render(
        "list_by_title.html",
        "reviews/by-title/index.html",
        reviews=title_reviews,
        all_years=all_years,
        title="Books by title",
        active="read",
        year="by-title",
    )

    # Render the "by author" page

    author_reviews = sorted(
        [  # don't @ me, this is beautiful
            (letter, list(authors))
            for letter, authors in itertools.groupby(
                sorted(
                    [
                        (author, list(reviews))
                        for (author, reviews) in itertools.groupby(
                            sorted(
                                all_reviews,
                                key=lambda rev: rev.metadata["book"]["author"],
                            ),
                            key=lambda review: review.metadata["book"]["author"],
                        )
                    ],
                    key=lambda x: x[0].upper(),
                ),
                key=lambda pair: (pair[0][0].upper() if pair[0][0].isalpha() else "_"),
            )
        ],
        key=lambda x: (not x[0].isalpha(), x[0].upper()),
    )
    render(
        "list_by_author.html",
        "reviews/by-author/index.html",
        reviews=author_reviews,
        all_years=all_years,
        title="Books by author",
        active="read",
        year="by-author",
    )

    # Render the "by series" page

    series_reviews = [
        (
            series,
            sorted(
                list(books),
                key=lambda book: float(book.metadata["book"]["series_position"])
                if isfloat(book.metadata["book"]["series_position"])
                else float(book.metadata["book"]["series_position"][0]),
            ),
        )
        for series, books in itertools.groupby(
            sorted(
                [
                    review
                    for review in all_reviews
                    if review.metadata["book"].get("series")
                    and review.metadata["book"].get("series_position")
                ],
                key=lambda rev: rev.metadata["book"]["series"],
            ),
            key=lambda rev: rev.metadata["book"]["series"],
        )
    ]
    series_reviews = sorted(
        [s for s in series_reviews if len(s[1]) > 1],
        key=lambda x: (not x[0][0].isalpha(), x[0].upper()),
    )
    render(
        "list_by_series.html",
        "reviews/by-series/index.html",
        reviews=series_reviews,
        all_years=all_years,
        title="Books by series",
        active="read",
        year="by-series",
    )

    # Render the "want to read" page

    render(
        "list_to_read.html",
        "to-read/index.html",
        all_plans=all_plans,
        title="Books i want to read",
        active="to-read",
    )

    # Render feeds

    render_feed(all_events[:20], "feed.atom", render)
    render_feed(all_reviews[:20], "reviews.atom", render)

    # Render the front page
    render(
        "index.html",
        "index.html",
        text=open("src/index.md").read(),
        reviews=all_reviews[:5],
    )

    # Render stats page
    time_lookup = defaultdict(list)
    for review in all_reviews:
        key = review.relevant_date.strftime("%Y-%m")
        time_lookup[key].append(review)

    most_books = 0
    most_pages = 0
    stats = []
    for year in all_years[::-1]:
        total_pages = 0
        total_books = 0
        months = []
        for month in range(12):
            written_month = f"{month + 1:02}"
            written_date = f"{year}-{written_month}"
            reviews = time_lookup[written_date]
            book_count = len(reviews)
            page_count = sum(
                int(review.metadata["book"].get("pages", 0)) for review in reviews
            )
            total_pages += page_count
            total_books += book_count
            most_books = max(most_books, book_count)
            most_pages = max(most_pages, page_count)
            months.append(
                {
                    "month": written_month,
                    "date": written_date,
                    "total_books": book_count,
                    "total_pages": page_count,
                }
            )
        stats.append(
            {
                "year": year,
                "months": months,
                "total_pages": total_pages,
                "total_books": total_books,
            }
        )

    table = [
        ("Total books read", len(all_reviews)),
        ("Reading pile", len(all_plans)),
        ("Books without review", len([b for b in all_reviews if not b.text.strip()])),
        (
            "Reviews without cross-reference",
            len(
                [b for b in all_reviews if b.text.strip() and "https://" not in b.text]
            ),
        ),
        (
            "Books per week",
            round(
                len(all_reviews)
                / ((dt.datetime.now().date() - dt.date(1998, 1, 1)).days / 7),
                2,
            ),
        ),
        ("Median publication year (reviews)", median_year(all_reviews)),
        ("Median publication year (reading pile)", median_year(all_plans)),
    ]

    render(
        "stats.html",
        "stats/index.html",
        stats=stats,
        most_books=most_books,
        most_pages=most_pages,
        table=table,
    )

    print("✨ Rendered HTML files to _html ✨")
