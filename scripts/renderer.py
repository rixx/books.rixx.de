import datetime
import itertools
import os
import pathlib
import subprocess
import sys

import attr
import frontmatter
import markdown
import smartypants
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown.extensions.smarty import SmartyExtension
from PIL import Image


def rsync(source, destination):
    subprocess.check_call(["rsync", "--recursive", "--delete", source, destination])


@attr.s
class Book:
    title = attr.ib()
    author = attr.ib()
    publication_year = attr.ib()
    cover_image = attr.ib(default="")
    cover_description = attr.ib(default="")
    series = attr.ib(default=None)
    series_position = attr.ib(default=None)

    isbn10 = attr.ib(default="")
    isbn13 = attr.ib(default="")


@attr.s
class Review:
    text = attr.ib()
    date_read = attr.ib()
    date_started = attr.ib(default=None)
    format = attr.ib(default=None)
    rating = attr.ib(default=None)
    did_not_finish = attr.ib(default=False)


@attr.s
class ReviewEntry:
    path = attr.ib()
    book = attr.ib()
    review = attr.ib()

    def out_path(self):
        name = self.path.with_suffix("").name
        return pathlib.Path(f"reviews/{name}")


@attr.s
class CurrentlyReading:
    text = attr.ib()


@attr.s
class CurrentlyReadingEntry:
    path = attr.ib()
    book = attr.ib()
    reading = attr.ib()


def _parse_date(value):
    if isinstance(value, datetime.date):
        return value
    else:
        return datetime.datetime.strptime(value, "%Y-%m-%d").date()


@attr.s
class Plan:
    text = attr.ib()
    date_added = attr.ib(converter=_parse_date)


@attr.s
class PlanEntry:
    path = attr.ib()
    book = attr.ib()
    plan = attr.ib()


def get_review_entry_from_path(path):
    post = frontmatter.load(path)

    kwargs = {}
    for attr_name in Book.__attrs_attrs__:
        try:
            kwargs[attr_name.name] = post["book"][attr_name.name]
        except KeyError:
            pass

    book = Book(**kwargs)
    review = Review(**post["review"], text=post.content)
    return ReviewEntry(path=path, book=book, review=review)


def get_reading_entry_from_path(path):
    post = frontmatter.load(path)

    book = Book(**post["book"])
    reading = CurrentlyReading(text=post.content)

    return CurrentlyReadingEntry(path=path, book=book, reading=reading)


def get_plan_entry_from_path(path):
    post = frontmatter.load(path)
    book = Book(**post["book"])
    plan = Plan(date_added=post["plan"]["date_added"], text=post.content)
    return PlanEntry(path=path, book=book, plan=plan)


def get_entries(dirpath, constructor):
    for dirpath, _, filenames in os.walk(dirpath):
        for f in filenames:
            if not f.endswith(".md"):
                continue

            path = pathlib.Path(dirpath) / f

            try:
                yield constructor(path)
            except Exception:
                print(f"Error parsing {path}", file=sys.stderr)
                raise


def render_markdown(text):
    return markdown.markdown(text, extensions=[SmartyExtension()])


def render_date(date_value):
    if isinstance(date_value, datetime.date):
        return date_value.strftime("%Y-%m-%d")
    return date_value


def render_individual_review(env, *, review_entry):
    template = env.get_template("review.html")
    html = template.render(
        review_entry=review_entry, title=f"My review of {review_entry.book.title}", active="read",
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

    all_reviews = list(
        get_entries(dirpath="src/reviews", constructor=get_review_entry_from_path)
    )
    all_reviews = sorted(
        all_reviews, key=lambda review: str(review.review.date_read), reverse=True
    )

    # Render single review pages

    for review_entry in all_reviews:
        render_individual_review(env, review_entry=review_entry)

    # Render the "all reviews" page

    this_year = str(datetime.datetime.now().year)
    all_years = sorted(list(set(str(review.review.date_read)[:4] for review in all_reviews)), reverse=True)
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

        out_path = pathlib.Path("_html") / "reviews" / (str(year) or "other") / "index.html"
        out_path.parent.mkdir(exist_ok=True, parents=True)
        out_path.write_text(html)
        if year == this_year:
            out_path = pathlib.Path("_html") / "reviews/index.html"
            out_path.write_text(html)

    # Render the "currently reading" page

    all_reading = list(
        get_entries(
            dirpath="src/currently_reading", constructor=get_reading_entry_from_path
        )
    )

    template = env.get_template("list_reading.html")
    html = template.render(all_reading=all_reading, title="Books I’m currently reading", active="reading")

    out_path = pathlib.Path("_html") / "reading/index.html"
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)

    # Render the "want to read" page

    all_plans = list(
        get_entries(dirpath="src/to_read", constructor=get_plan_entry_from_path)
    )

    all_plans = sorted(all_plans, key=lambda plan: plan.plan.date_added, reverse=True)

    template = env.get_template("list_to_read.html")
    html = template.render(all_plans=all_plans, title="Books i want to read", active="to-read")

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
