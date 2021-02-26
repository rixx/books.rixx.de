import colorsys
from collections import defaultdict
from statistics import median_high

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
    cover_path = review.cover_path

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
    except Exception:
        return

    fix_publication_year(review, google_data, openlib_data)
    fix_page_number(review, google_data, openlib_data)
    fix_dimensions(review, google_data, openlib_data)
    review.save()


def normalize_series_height(books: list):
    from .books import Spine

    heights = [
        book.metadata["book"].get("dimensions", {}).get("height") for book in books
    ]
    heights = [h for h in heights if h]
    if heights:
        height = median_high(heights)
    else:
        height = Spine.random_height(None)
    for book in books:
        if not book.metadata["book"].get("dimensions"):
            book.metadata["book"]["dimensions"] = {}
        if (
            "height" not in book.metadata["book"]["dimensions"]
            or book.metadata["book"]["dimensions"]["height"] != height
        ):
            book.metadata["book"]["dimensions"]["height"] = height
            print(f"Fixing height of {book.id}")
        book.save()


def normalize_series_related_books(books: list):
    books = sorted(
        books, key=lambda book: float(book.metadata["book"]["series_position"])
    )
    first_book = [
        book for book in books if book.metadata["book"]["series_position"] == "1"
    ]
    if first_book:
        first_book = first_book[0]
    else:
        first_book = None

    for index, book in enumerate(books):
        related = book.metadata.get("related_books") or []
        related_ids = [rel.get("book") for rel in related]

        if index > 0:
            previous_book = books[index - 1]
        else:
            previous_book = None
        if index + 1 < len(books):
            next_book = books[index + 1]

        if (
            previous_book
            and previous_book.id not in related_ids
            and previous_book.entry_type == "reviews"
            and previous_book != book
        ):
            related.append(
                {"book": previous_book.id, "text": "The previous book in the series."}
            )
            print(f"Adding previous book {previous_book.id} to {book.id}")

        if (
            next_book
            and next_book.id not in related_ids
            and next_book.entry_type == "reviews"
            and next_book != book
        ):
            related.append(
                {"book": next_book.id, "text": "The next book in the series."}
            )
            print(f"Adding next book {next_book.id} to {book.id}")

        if (
            first_book
            and book != first_book
            and previous_book != first_book
            and next_book != first_book
            and first_book.id not in related_ids
            and first_book.entry_type == "reviews"
        ):
            related.append(
                {"book": first_book.id, "text": "The first book in the series."}
            )
            print(f"Adding first book {first_book.id} to {book.id}")

        book.metadata["related_books"] = related
        book.save()


def normalize_series():
    from .books import load_reviews, load_to_read

    reviews = list(load_reviews()) + list(load_to_read())
    by_series = defaultdict(list)
    for r in reviews:
        if r.metadata["book"].get("series"):
            by_series[r.metadata["book"]["series"]].append(r)
    by_series = {key: value for key, value in by_series.items() if len(value) > 1}

    for books in by_series.values():
        normalize_series_height(books)
        normalize_series_related_books(books)


def find_duplicates():
    from scripts.books import load_reviews, load_to_read

    to_read = set(review.id for review in load_to_read())
    reviews = set(review.id for review in load_reviews())

    for double in to_read & reviews:
        print(double)
