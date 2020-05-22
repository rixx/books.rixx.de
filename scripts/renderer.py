import datetime as dt
import itertools
import os
import pathlib
import subprocess

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


def render_individual_review(env, *, review_entry):
    template = env.get_template("review.html")
    html = template.render(
        review_entry=review_entry,
        title=f"My review of {review_entry.book.title}",
        active="read",
    )

    out_name = review_entry.out_path() / "index.html"
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

    all_reviews = books.get_all_reviews()
    all_reviews = sorted(
        all_reviews, key=lambda review: str(review.review.date_read), reverse=True
    )

    # Render single review pages

    for review_entry in all_reviews:
        render_individual_review(env, review_entry=review_entry)

    # Render the "all reviews" page

    this_year = str(dt.datetime.now().year)
    all_years = sorted(
        list(set(str(review.review.date_read)[:4] for review in all_reviews)),
        reverse=True,
    )
    template = env.get_template("list_reviews.html")
    for (year, reviews) in itertools.groupby(
        all_reviews, key=lambda rev: str(rev.review.date_read)[:4]
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
            sorted(all_reviews, key=lambda rev: rev.book.title),
            key=lambda rev: (
                rev.book.title[0].upper() if rev.book.title[0].isalpha() else "_"
            ),
        )
    ]
    title_reviews = sorted(title_reviews, key=lambda x: (not x[0].isalpha(), x[0]))
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
                        sorted(all_reviews, key=lambda rev: rev.book.author),
                        key=lambda review: review.book.author,
                    )
                ],
                key=lambda x: x[0],
            ),
            key=lambda pair: (pair[0][0].upper() if pair[0][0].isalpha() else "_"),
        )
    ]
    author_reviews = sorted(author_reviews, key=lambda x: (not x[0].isalpha(), x[0]))
    html = template.render(
        reviews=author_reviews,
        all_years=all_years,
        title="Books by author",
        active="by-author",
    )
    out_path = pathlib.Path("_html") / "reviews" / "by-author/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "currently reading" page

    all_reading = list(books.get_currently_reading())

    template = env.get_template("list_reading.html")
    html = template.render(
        all_reading=all_reading, title="Books I’m currently reading", active="reading"
    )

    out_path = pathlib.Path("_html") / "reading/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "want to read" page

    all_plans = list(books.get_to_read())

    all_plans = sorted(all_plans, key=lambda plan: plan.plan.date_added, reverse=True)

    template = env.get_template("list_to_read.html")
    html = template.render(
        all_plans=all_plans, title="Books i want to read", active="to-read"
    )

    out_path = pathlib.Path("_html") / "to-read/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the front page

    index_template = env.get_template("index.html")
    html = index_template.render(
        text=open("src/index.md").read(), reviews=all_reviews[:5]
    )

    index_path = pathlib.Path("_html") / "index.html"
    index_path.write_text(html)

    print("✨ Rendered HTML files to _html ✨")
