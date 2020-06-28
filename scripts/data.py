import colorsys
from pathlib import Path

from PIL import Image
from sklearn.cluster import KMeans


def get_dominant_colours(path, *, count):
    """
    Return a list of the dominant RGB colours in the image at ``path``.

    :param path: Path to the image file.
    :param count: Number of dominant colours to find.

    """
    im = Image.open(path)

    # Resizing means less pixels to handle, so the *k*-means clustering converges
    # faster.  Small details are lost, but the main details will be preserved.
    im = im.resize((100, 100))

    # Ensure the image is RGB, and use RGB values in [0, 1] for consistency
    # with operations elsewhere.
    im = im.convert("RGB")
    colors = [(r / 255, g / 255, b / 255) for (r, g, b) in im.getdata()]

    return KMeans(n_clusters=count).fit(colors).cluster_centers_


def choose_spine_color(review):
    cover_path = Path("src/covers") / review.metadata["book"]["cover_image"]

    dominant_colors = get_dominant_colours(cover_path, count=3)
    hsv_candidates = {
        tuple(rgb_col): colorsys.rgb_to_hsv(*rgb_col) for rgb_col in dominant_colors
    }

    candidates_by_brightness_diff = {
        rgb_col: abs(hsv_col[2] * hsv_col[1])
        for rgb_col, hsv_col in hsv_candidates.items()
    }

    rgb_choice, _ = max(candidates_by_brightness_diff.items(), key=lambda t: t[1])
    hex_color = "#%02x%02x%02x" % tuple(int(v * 255) for v in rgb_choice)
    review.metadata["book"]["spine_color"] = hex_color
    review.save()
