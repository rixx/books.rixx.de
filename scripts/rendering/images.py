import subprocess
from pathlib import Path

from PIL import Image


def rsync(source, destination):
    subprocess.check_call(["rsync", "--recursive", "--delete", source, destination])


def _create_new_thumbnail(src_path, dst_path):
    dst_path.parent.mkdir(exist_ok=True, parents=True)

    im = Image.open(src_path)

    if im.width > 240 and im.height > 240:
        im.thumbnail((240, 240))
    im.save(dst_path)


def _create_new_square(src_path, square_path):
    square_path.parent.mkdir(exist_ok=True, parents=True)

    im = Image.open(src_path)
    im.thumbnail((240, 240))
    dimension = max(im.size)

    new = Image.new("RGBA", size=(dimension, dimension), color=(255, 255, 255, 0))

    if im.height > im.width:
        new.paste(im, box=((dimension - im.width) // 2, 0))
    else:
        new.paste(im, box=(0, (dimension - im.height) // 2))

    new.save(square_path)


def create_thumbnail(review):
    if not review.cover_path:
        return

    html_path = Path("_html") / review.id
    thumbnail_path = html_path / "thumbnail.jpg"
    square_path = html_path / "square.png"
    cover_path = html_path / review.cover_path.name
    cover_age = review.cover_path.stat().st_mtime

    if not cover_path.exists() or cover_age > cover_path.stat().st_mtime:
        rsync(review.cover_path, cover_path)
        _create_new_thumbnail(review.cover_path, thumbnail_path)
        _create_new_square(review.cover_path, square_path)
