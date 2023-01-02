import datetime as dt
import hashlib
import pathlib
import uuid
from io import StringIO

import markdown
import smartypants
from jinja2 import Environment, FileSystemLoader, select_autoescape
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


def render_date(date_value):
    if isinstance(date_value, dt.date):
        return date_value.strftime("%Y-%m-%d")
    return date_value


ENV = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
ENV.filters["render_markdown"] = render_markdown
ENV.filters["render_quotes"] = render_quotes
ENV.filters["render_toc"] = render_toc
ENV.filters["strip_markdown"] = strip_markdown
ENV.filters["render_date"] = render_date
ENV.filters["smartypants"] = smartypants.smartypants


def render(template_name, path, **context):
    template = ENV.get_template(template_name)
    html = template.render(**context)
    out_path = pathlib.Path("_html") / path
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(html)


def render_string(path, string):
    out_path = pathlib.Path("_html") / path
    out_path.parent.mkdir(exist_ok=True, parents=True)
    out_path.write_text(string)
