import datetime as dt
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx

from . import books, sqlite
from .rendering import images, stats, template


def isfloat(value):
    try:
        float(value)
        return True
    except Exception:
        return False


def sort_reviews(reviews):
    return sorted(reviews, key=lambda x: x.relevant_date, reverse=True)


def build_site(db=None, **kwargs):
    print("✨ Starting to build the site … ✨")
    this_year = dt.datetime.now().strftime("%Y")

    print("📔 Loading reviews from files")
    review_lookup = {review.id: review for review in books.load_reviews()}

    all_reviews = sort_reviews(review_lookup.values())
    all_plans = sort_reviews(books.load_to_read())
    all_events = sort_reviews(all_plans + all_reviews)

    tags = defaultdict(list)
    reviews_by_year = defaultdict(list)
    redirects = []

    # Render single review pages
    print("🖋 Rendering review pages")
    for review in all_reviews:
        review.spine = books.Spine(review)
        review.word_count = len(review.text.split())
        try:
            review.related_books = [
                {
                    "review": review_lookup[related["book"]],
                    "text": related["text"],
                }
                for related in review.metadata.get("related_books", [])
            ]
        except KeyError as e:
            print(f"Cannot find related book for {review.path}!")
            print(str(e))
            sys.exit(-1)
        for timestamp in review.metadata["review"]["date_read"]:
            year = timestamp.strftime("%Y")
            reviews_by_year[year].append(review)
            if int(year) <= 2020:
                redirects.append(
                    (
                        f"reviews/{year}/{review.slug}",
                        review.id,
                    )
                )
        for tag in review.metadata["book"].get("tags", []):
            tags[tag].append(review)
        template.render(
            "review.html",
            Path(review.id) / "index.html",
            review=review,
            title=f"Review of {review.metadata['book']['title']}",
            active="read",
        )

    template.render("redirects.conf", "redirects.conf", redirects=redirects)

    # Render tag pages
    print("🔖 Rendering tag pages")
    tags = {
        books.Tag(tag): sorted(
            reviews,
            key=lambda rev: (
                5 - (rev.metadata["review"]["rating"] or 5),
                rev.metadata["book"]["author"],
                rev.metadata["book"].get("series", ""),
                float(rev.metadata["book"].get("series_position", 0) or 0),
                rev.metadata["book"]["title"],
            ),
        )
        for tag, reviews in tags.items()
    }

    for tag, reviews in tags.items():
        template.render(
            "tag.html",
            f"lists/{tag.slug}/index.html",
            tag=tag,
            reviews=reviews,
            active="lists",
            title="List: " + (tag.metadata.get("title") or tag.slug),
        )

    template.render("tags.html", "lists/index.html", tags=tags, active="lists")

    # Render the "want to read" page

    mapped_plans = {tag.slug: {"tag": tag, "books": []} for tag in tags}
    mapped_plans[None] = {"books": [], "tag": None}
    for plan in all_plans:
        book_tags = plan.metadata["book"].get("tags")
        if book_tags:
            for tag in book_tags:
                mapped_plans[tag]["books"].append(plan)
        else:
            mapped_plans[None]["books"].append(plan)

    mapped_plans = sorted(
        list(mapped_plans.values()),
        key=lambda r: (r["tag"].slug if r["tag"] else "zzz"),
    )
    for plan in mapped_plans:
        plan["books"] = sorted(plan["books"], key=lambda r: r.metadata["book"]["title"])

    template.render(
        "list_to_read.html",
        "to-read/index.html",
        mapped_plans=mapped_plans,
        title="Books I want to read",
        active="to-read",
    )

    print("📷 Generating thumbnails")
    for event in all_events:
        images.create_thumbnail(event)

    images.rsync(source="static/", destination="_html/static/")

    # Render feeds
    print("📰 Rendering feed pages")
    template.render_feed(all_reviews[:20], "feed.atom")
    template.render_feed(all_reviews[:20], "reviews.atom")

    # Render the front page
    template.render(
        "index.html",
        "index.html",
        text=open("data/index.md").read(),
        reviews=all_reviews[:5],
        shelf_books=sorted(all_reviews, key=lambda x: x.metadata["book"]["author"]),
    )

    # Render graph page
    print("🕸  Rendering graphs")
    graph = nx.Graph()
    for review in all_reviews:
        other = review.metadata.get("related_books")
        if not other:
            continue
        graph.add_node(review.id)
        for related in other:
            graph.add_node(related["book"])
            graph.add_edge(review.id, related["book"])
    nodes = []
    for node in graph.nodes:
        review = review_lookup[node]
        nodes.append(
            {
                "id": node,
                "name": review.metadata["book"]["title"],
                "cover": bool(review.cover_path),
                "author": review.metadata["book"]["author"],
                "series": review.metadata["book"].get("series"),
                "rating": int(review.metadata["review"]["rating"]),
                "color": review.metadata["book"].get("spine_color"),
                "connections": len(list(graph.neighbors(node))),
                "search": [
                    term
                    for term in review.metadata["book"]["title"].lower().split()
                    + review.metadata["book"]["author"].lower().split()
                    + review.metadata["book"].get("series", "").lower().split()
                    + [f"tag:{tag}" for tag in review.metadata["book"].get("tags", [])]
                    + (
                        [f"rating:{review.metadata['review'].get('rating')}"]
                        if review.metadata["review"].get("rating")
                        else []
                    )
                    if term
                ],
            }
        )
    edges = [{"source": source, "target": target} for source, target in graph.edges]
    search_tags = [
        {
            "slug": tag.slug,
            "name": tag.metadata.get("title") or tag.slug,
            "search": (tag.metadata.get("title") or tag.slug).lower().split(),
        }
        for tag in tags.keys()
    ]
    template.render_string(
        "search.json", json.dumps({"books": nodes, "tags": search_tags})
    )
    template.render_string("graph.json", json.dumps({"nodes": nodes, "links": edges}))
    template.render(
        "graph.html",
        "graph/index.html",
        node_count=graph.number_of_nodes(),
        edge_count=graph.number_of_edges(),
        missing_nodes=len(all_reviews) - graph.number_of_nodes(),
        parts=nx.number_connected_components(graph),
        is_connected=nx.is_connected(graph),
        active="graph",
    )
    template.render(
        "random.html",
        "random/index.html",
        active="random",
    )

    # Render quotes
    print("💬 Rendering quotes")

    # Render database
    if db:
        print("🏭 Rendering database")
        sqlite.render_db(
            db=db,
            reviews=all_reviews,
            plans=all_plans,
        )

    print("✨ Rendered HTML files to _html ✨")
