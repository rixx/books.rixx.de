import colorsys
from pathlib import Path

import requests
from PIL import Image
from sklearn.cluster import KMeans


def get_dominant_colours(path, count):
    im = Image.open(path)

    # Resizing means less pixels to handle, so the *k*-means clustering converges
    # faster.  Small details are lost, but the main details will be preserved.
    im = im.resize((100, 100))

    # Ensure the image is RGB, and use RGB values in [0, 1] for consistency
    # with operations elsewhere.
    im = im.convert("RGB")
    colors = [(r / 255, g / 255, b / 255) for (r, g, b) in im.getdata()]

    return KMeans(n_clusters=count).fit(colors).cluster_centers_


def choose_spine_color(review, cluster_count=3):
    cover_path = Path("src/covers") / review.metadata["book"]["cover_image"]

    dominant_colors = get_dominant_colours(cover_path, count=cluster_count)
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


def get_google_data(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    response = requests.get(url).json()
    google_id = response["items"][0]["id"]
    data = requests.get(
        f"https://www.googleapis.com/books/v1/volumes/{google_id}"
    ).json()
    return data["volumeInfo"]


def get_openlib_data(isbn):
    data = requests.get(
        f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&jscmd=details&format=json"
    ).json()
    return data[list(data.keys())[0]]


def fix_publication_year(review, google_data, openlib_data):
    review_year = review.metadata["book"].get("publication_year")
    google_year = google_data.get("publishedDate", "")[:4]  # "1995"
    openlib_year = openlib_data.get("publish_date", "")[-4:]
    for external_year in [google_year, openlib_year]:
        if external_year and not review_year:
            review_year = external_year
        elif external_year and external_year != review_year:
            review_year = (
                external_year if int(external_year) < int(review_year) else review_year
            )
    review.metadata["book"]["publication_year"] = review_year


def fix_page_number(review, google_data, openlib_data):
    review_pages = int(review.metadata["book"].get("pages", 0) or 0)
    google_pages = int(google_data.get("pageCount", 0) or 0)
    openlib_pages = int(openlib_data.get("number_of_pages", 0) or 0)
    review.metadata["book"]["pages"] = max([review_pages, google_pages, openlib_pages])


def fix_dimensions(review, google_data, openlib_data):
    review_dimensions = review.metadata["book"].get("dimensions") or {}
    google_dimensions = google_data.get("dimensions") or {}
    openlib_dimensions = openlib_data.get("physical_dimensions") or {}
    if openlib_dimensions:
        numbers = openlib_dimensions.split()
        factor = 2.54 if numbers[-1] == "inches" else 1
        openlib_dimensions = {
            "height": round(factor * float(numbers[0]), 1),
            "width": round(factor * float(numbers[2]), 1),
            "thickness": round(factor * float(numbers[4]), 1),
        }
    if google_dimensions:

        def fix_google_dimension(data, key):
            value = data.get(key)
            if not value:
                return None
            value = value.split()
            factor = 2.54 if value[-1] != "cm" else 1
            return round(factor * float(value[0]), 1)

        google_dimensions = {
            "height": fix_google_dimension(google_dimensions, "height"),
            "width": fix_google_dimension(google_dimensions, "width"),
            "thickness": fix_google_dimension(google_dimensions, "thickness"),
        }
    dimensions = {}
    for key in ("height", "width", "thickness"):
        candidates = [
            number
            for number in [
                review_dimensions.get(key),
                google_dimensions.get(key),
                openlib_dimensions.get(key),
            ]
            if number
        ]
        if candidates:
            dimensions[key] = max(candidates)
    review.metadata["book"]["dimensions"] = dimensions


def update_book_data(review):
    try:
        google_data = get_google_data(review.isbn)
        openlib_data = get_openlib_data(review.isbn)
    except:
        return

    fix_publication_year(review, google_data, openlib_data)
    fix_page_number(review, google_data, openlib_data)
    fix_dimensions(review, google_data, openlib_data)
    review.save()