import mimetypes
from pathlib import Path

from aiohttp import web


def insert_js(html):
    html = html.decode()
    head, body = html.split("</head>", maxsplit=1)
    head += '<script src="/static/editor.js"></script>'
    return f"{head}</head>{body}".encode()


async def handle_get(request):
    path = Path(__file__).parent.parent / "_html" / str(request.path.strip("/"))
    if not path.exists() or not path.is_file():
        path = path / "index.html"
        if not path.exists() or not path.is_file():
            print(f"404 {path}")
            return web.Response(text="", status=404)
    print(f"200 {request.path}")
    content_type = mimetypes.guess_type(path)[0]
    content = open(path, "rb").read()
    if content_type == "text/html":
        content = insert_js(content)
    return web.Response(body=content, content_type=content_type)


def run_server():
    # load all data
    app = web.Application()
    app.add_routes(
        [
            web.get(r"/{path:.*}", handle_get),
        ]
    )
    web.run_app(app)
