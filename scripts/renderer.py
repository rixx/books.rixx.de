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


def render_tag_page(tag, reviews, render):
    render(
        "tag.html",
        f"lists/{tag.slug}/index.html",
        tag=tag,
        reviews=reviews,
        active="lists",
        title="List: " + (tag.metadata.get("title") or tag.slug),
    )


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


def xml_element(name, content, **kwargs):
    attribs = " ".join(
        f'{key.strip("_").replace("_", "-")}="{value}"' for key, value in kwargs.items()
    ).strip()
    attribs = f" {attribs}" if attribs else ""
    content = content or ""
    return f"<{name}{attribs}>{content}</{name}>"


def generate_svg(
    data, key, max_month, max_year, primary_color, secondary_color, offset
):
    current_year = dt.datetime.now().year
    fallback_color = "#ebedf0"
    content = ""
    year_width = 45
    rect_width = 15
    gap = 3
    block_width = rect_width + gap
    stats_width = 6 * block_width
    total_width = (block_width * 12) + year_width + stats_width
    total_height = block_width * len(data)
    for row, year in enumerate(data):
        year_content = (
            xml_element(
                "text",
                year["year"],
                x=year_width - gap * 2,
                y=row * 18 + 13,
                width=year_width,
                text_anchor="end",
            )
            + "\n"
        )
        for column, month in enumerate(year["months"]):
            total = month.get(f"total_{key}")
            title = xml_element("title", f"{month['date']}: {total}")
            if total:
                color = primary_color.format((total + offset) / max_month)
            elif year["year"] == current_year:
                continue
            else:
                color = fallback_color
            rect = xml_element(
                "rect",
                title,
                width=rect_width,
                height=rect_width,
                x=column * block_width + year_width,
                y=row * block_width,
                fill=color,
                _class="month",
            )
            year_content += (
                xml_element("a", rect, href=f"/reviews/{year['year']}/#{month['date']}")
                + "\n"
            )

        total = year.get(f"total_{key}")
        title = xml_element("title", f"{year['year']}: {total}")
        rect = xml_element(
            "rect",
            title,
            width=total * stats_width / max_year,
            height=rect_width,
            x=12 * block_width + year_width,
            y=row * block_width,
            fill=secondary_color.format(0.42),
            _class="total",
        )
        content += year_content + rect + "\n"

    return xml_element(
        "svg", content, style=f"width: {total_width}px; height: {total_height}px"
    )


def get_stats(reviews, years):
    stats = {}
    time_lookup = defaultdict(list)
    for review in reviews:
        key = review.relevant_date.strftime("%Y-%m")
        time_lookup[key].append(review)

    most_monthly_books = 0
    most_monthly_pages = 0
    most_yearly_books = 0
    most_yearly_pages = 0
    numbers = []
    for year in years:
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
            most_monthly_books = max(most_monthly_books, book_count)
            most_monthly_pages = max(most_monthly_pages, page_count)
            months.append(
                {
                    "month": written_month,
                    "date": written_date,
                    "total_books": book_count,
                    "total_pages": page_count,
                }
            )
        most_yearly_books = max(most_yearly_books, total_books)
        most_yearly_pages = max(most_yearly_pages, total_pages)
        numbers.append(
            {
                "year": year,
                "months": months,
                "total_pages": total_pages,
                "total_books": total_books,
            }
        )

    stats["pages"] = generate_svg(
        numbers,
        "pages",
        max_month=most_monthly_pages,
        max_year=most_yearly_pages,
        primary_color="rgba(0, 113, 113, {})",
        secondary_color="rgba(153, 0, 0, {})",
        offset=1000,
    )
    stats["books"] = generate_svg(
        numbers,
        "books",
        max_month=most_monthly_books,
        max_year=most_yearly_books,
        primary_color="rgba(153, 0, 0, {})",
        secondary_color="rgba(0, 113, 113, {})",
        offset=1,
    )

    return stats


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

    all_reviews = sorted(all_reviews, key=lambda x: x.relevant_date, reverse=True)
    all_plans = sorted(all_plans, key=lambda x: x.relevant_date, reverse=True)
    all_events = sorted(all_events, key=lambda x: x.relevant_date, reverse=True)
    tags = defaultdict(list)

    # Render single review pages
    redirects = []

    for review in all_reviews:
        render(
            "review.html",
            review.get_url_path() / "index.html",
            review=review,
            title=f"Review of {review.metadata['book']['title']}",
            active="read",
        )
        redirects.append(
            (
                f"reviews/{review.relevant_date.year}/{review.metadata['book']['slug']}",
                review.get_url_path()
            )
        )
        review.spine = books.Spine(review)
        for tag in review.metadata["book"].get("tags", []):
            tags[tag].append(review)

    render("redirects.conf", "redirects.conf", redirects=redirects)
    tags = {
        books.Tag(tag): sorted(
            tags[tag],
            key=lambda rev: (
                5 - (rev.metadata["review"]["rating"] or 5),
                rev.metadata["book"]["author"],
                rev.metadata["book"].get("series", ""),
                float(rev.metadata["book"].get("series_position", 0) or 0),
                rev.metadata["book"]["title"],
            ),
        )
        for tag in sorted(tags.keys())
    }

    # Render tag pages

    for tag, reviews in tags.items():
        render_tag_page(tag, reviews, render)

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
        shelf_books=sorted(all_reviews, key=lambda x: x.metadata["book"]["author"]),
    )

    # Render stats page

    stats = get_stats(reviews=all_reviews, years=all_years)
    stats["table"] = [
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
        "stats.html", "stats/index.html", stats=stats,
    )

    render("tags.html", "lists/index.html", tags=tags, active="lists")

    print("✨ Rendered HTML files to _html ✨")
