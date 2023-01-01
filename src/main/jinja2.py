
from django.contrib.staticfiles.storage import staticfiles_storage
import datetime as dt
import hashlib
import pathlib
import uuid
from io import StringIO

import markdown
import smartypants
from jinja2 import Environment, FileSystemLoader, select_autoescape, Markup
from markdown.extensions.smarty import SmartyExtension
from markdown.extensions.toc import TocExtension


def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
markdown.Markdown.output_formats["plain"] = unmark_element
plain_markdown = markdown.Markdown(output_format="plain")
plain_markdown.stripTopLevelTags = False
md = markdown.Markdown(
    extensions=[SmartyExtension(), TocExtension(marker="", baselevel=2)]
)
md_quotes = markdown.Markdown(
    extensions=[SmartyExtension(), "nl2br"]
)


def render_markdown(text):
    md.reset()
    return md.convert(text)


def render_quotes(text):
    md_quotes.reset()
    return md_quotes.convert(text)


def render_toc(text):
    md.reset()
    md.convert(text)
    return md.toc


def strip_markdown(text):
    return plain_markdown.convert(text)


def render_date(date_value, link=True):
    if isinstance(date_value, dt.date):
        date_value = date_value.strftime("%Y-%m-%d")
    if not date_value:
        return
    if not link:
        return date_value
    year, rest = date_value.split("-", maxsplit=1)
    return Markup(f'<a href="/reviews/{year}">{year}</a>-{rest}')


def environment(**options):
    options["loader"]=FileSystemLoader(pathlib.Path(__file__).parent / "templates")
    options["autoescape"]=select_autoescape(["html", "xml"])
    
    env = Environment(**options)
    env.globals.update({"static": staticfiles_storage.url
                        })
    env.filters["render_markdown"] = render_markdown
    env.filters["render_quotes"] = render_quotes
    env.filters["render_toc"] = render_toc
    env.filters["strip_markdown"] = strip_markdown
    env.filters["render_date"] = render_date
    env.filters["smartypants"] = smartypants.smartypants
    return env


def render_feed(events, path):
    for event in events:
        m = hashlib.md5()
        m.update(
            f"{event.metadata['book']['title']}:{event.entry_type}:{event.relevant_date}:{event.metadata['book'].get('goodreads', '')}".encode()
        )
        event.feed_uuid = str(uuid.UUID(m.hexdigest()))

    render("feed.atom", path, events=events)
