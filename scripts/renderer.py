import datetime as dt
import itertools
import os
import pathlib
import subprocess
import hashlib
import uuid

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
    elif review.entry_type == "currently-reading":
        result = review.metadata["review"]["date_started"]
    else:
        result = review.metadata["plan"]["date_added"]
    if isinstance(result, dt.date):
        return result
    return dt.datetime.strptime(result, "%Y-%m-%d").date()


def render_individual_review(env, *, review):
    template = env.get_template("review.html")
    html = template.render(
        review=review,
        title=f"Review of {review.metadata['book']['title']}",
        active="read",
    )

    out_name = review.get_core_path() / "index.html"
    out_path = pathlib.Path("_html") / out_name
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)


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


def build_site():
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )

    env.filters["render_markdown"] = render_markdown
    env.filters["render_date"] = render_date
    env.filters["smartypants"] = smartypants.smartypants
    env.filters["thumbnail_1x"] = thumbnail_1x

    create_thumbnails()

    rsync(source="src/covers/", destination="_html/covers/")
    rsync(source="static/", destination="_html/static/")

    all_reviews = books.load_reviews()
    all_reviews = sorted(
        all_reviews,
        key=lambda review: str(review.metadata["review"]["date_read"]),
        reverse=True,
    )

    # Render single review pages

    for review in all_reviews:
        render_individual_review(env, review=review)

    # Render the "all reviews" page

    this_year = str(dt.datetime.now().year)
    all_years = sorted(
        list(
            set(
                str(review.metadata["review"]["date_read"])[:4]
                for review in all_reviews
            )
        ),
        reverse=True,
    )
    template = env.get_template("list_reviews.html")
    for (year, reviews) in itertools.groupby(
        all_reviews, key=lambda rev: str(rev.metadata["review"]["date_read"])[:4]
    ):
        html = template.render(
            reviews=list(reviews),
            all_years=all_years,
            year=year,
            this_year=this_year,
            title="Books I’ve read",
            active="read",
        )

        out_path = (
            pathlib.Path("_html") / "reviews" / (str(year) or "other") / "index.html"
        )
        out_path.parent.mkdir(exist_ok=True, parents=True)
        out_path.write_text(html)
        if year == this_year:
            out_path = pathlib.Path("_html") / "reviews/index.html"
            out_path.write_text(html)

    # Render the "by title" page

    template = env.get_template("list_by_title.html")
    title_reviews = [
        (letter, list(reviews))
        for (letter, reviews) in itertools.groupby(
            sorted(all_reviews, key=lambda rev: rev.metadata["book"]["title"]),
            key=lambda rev: (
                rev.metadata["book"]["title"][0].upper()
                if rev.metadata["book"]["title"][0].isalpha()
                else "_"
            ),
        )
    ]
    title_reviews = sorted(
        title_reviews, key=lambda x: (not x[0].isalpha(), x[0].upper())
    )
    html = template.render(
        reviews=title_reviews,
        all_years=all_years,
        title="Books by title",
        active="by-title",
    )
    out_path = pathlib.Path("_html") / "reviews" / "by-title/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "by author" page

    template = env.get_template("list_by_author.html")
    author_reviews = [  # don't @ me
        (letter, list(authors))
        for letter, authors in itertools.groupby(
            sorted(
                [
                    (author, list(reviews))
                    for (author, reviews) in itertools.groupby(
                        sorted(
                            all_reviews, key=lambda rev: rev.metadata["book"]["author"]
                        ),
                        key=lambda review: review.metadata["book"]["author"],
                    )
                ],
                key=lambda x: x[0].upper(),
            ),
            key=lambda pair: (pair[0][0].upper() if pair[0][0].isalpha() else "_"),
        )
    ]
    author_reviews = sorted(
        author_reviews, key=lambda x: (not x[0].isalpha(), x[0].upper())
    )
    html = template.render(
        reviews=author_reviews,
        all_years=all_years,
        title="Books by author",
        active="by-author",
    )
    out_path = pathlib.Path("_html") / "reviews" / "by-author/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "by series" page

    template = env.get_template("list_by_series.html")
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
    html = template.render(
        reviews=series_reviews,
        all_years=all_years,
        title="Books by series",
        active="by-series",
    )
    out_path = pathlib.Path("_html") / "reviews" / "by-series/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "currently reading" page

    all_reading = list(books.load_currently_reading())

    template = env.get_template("list_reading.html")
    html = template.render(
        all_reading=all_reading, title="Books I’m currently reading", active="reading"
    )

    out_path = pathlib.Path("_html") / "reading/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "want to read" page

    all_plans = list(books.load_to_read())

    all_plans = sorted(
        all_plans, key=lambda plan: plan.metadata["plan"]["date_added"], reverse=True
    )

    template = env.get_template("list_to_read.html")
    html = template.render(
        all_plans=all_plans, title="Books i want to read", active="to-read"
    )

    out_path = pathlib.Path("_html") / "to-read/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render feed

    all_events = all_plans + all_reading + all_reviews
    for element in all_events:
        element.relevant_date = get_relevant_date(element)
    all_events = sorted(all_events, key=lambda x: x.relevant_date, reverse=True)
    generate_events = all_events[:20]
    for event in generate_events:
        m = hashlib.md5()
        m.update(
            f"{event.metadata['book']['title']}:{event.entry_type}:{event.relevant_date}:{event.metadata['book'].get('goodreads', '')}".encode()
        )
        event.feed_uuid = str(uuid.UUID(m.hexdigest()))

    template = env.get_template("feed.atom")
    html = template.render(events=generate_events)
    out_path = pathlib.Path("_html") / "feed.atom"
    out_path.write_text(html)

    # Render the front page

    index_template = env.get_template("index.html")
    html = index_template.render(
        text=open("src/index.md").read(), reviews=all_reviews[:5]
    )

    index_path = pathlib.Path("_html") / "index.html"
    index_path.write_text(html)

    print("✨ Rendered HTML files to _html ✨")
