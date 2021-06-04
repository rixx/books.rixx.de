import json
import click
import inquirer
from pathlib import Path
from .books import load_reviews

YEAR = 2021
SQUARES = {
    "A1": {
        "title": "Five SFF Short Stories",
        "description": "Any short story as long as there are five of them.",
        "hard_mode": "Read an entire SFF anthology or collection.",
    },
    "A2": {
        "title": "Set in Asia",
        "description": "Any book set in Asia or an analogous fantasy setting that is based on a real-world Asian setting.",
        "hard_mode": "Written by an Asian author.",
    },
    "A3": {
        "title": "A Selection from the r/Fantasy A to Z Genre Guide",
        "description": "https://www.reddit.com/r/Fantasy/wiki/index/a-to-z-genre-guide",
        "hard_mode": "A book by a BIPOC author.",
    },
    "A4": {
        "title": "Found Family",
        "description": "Family of Choice. Often not biologically related, these relationships in a group typically form through bonds of shared experiences and become as important (in some cases more) as family members.",
        "hard_mode": "Featuring an LGBTQ+ character as a member of the found family.",
    },
    "A5": {
        "title": "First Person POV",
        "description": "defined as: a literary style in which the narrative is told from the perspective of a narrator speaking directly about themselves.",
        "hard_mode": "There is more than one perspective, but each perspective is written in First Person.",
    },
    "B1": {
        "title": "Book Club OR Readalong Book",
        "description": "Shelf: https://www.goodreads.com/group/bookshelf/107259-r-fantasy-discussion-group?page=1&per_page=100&utf8=%E2%9C%93.",
        "hard_mode": "Must read a current selection of either a book club or readalong and participate in the discussion: https://www.goodreads.com/group/show/107259-r-fantasy-discussion-group.",
    },
    "B2": {
        "title": "New to You Author",
        "hard_mode": "Not only have you never read their work before but you've not heard much about this author or their work before deciding to try a book by them.",
    },
    "B3": {
        "title": "Gothic Fantasy",
        "description": ' "a style of writing that is characterized by elements of fear, horror, death, and gloom, as well as romantic elements, such as nature, individuality, and very high emotion. These emotions can include fear and suspense.".',
        "hard_mode": "NOT one of the ten titles listed in the Book Riot article: https://bookriot.com/gothic-fantasy/",
    },
    "B4": {
        "title": "Backlist Book",
        "description": "Older titles that are not the author's latest published book or part of a currently running series (no further sequels announced when you read it). The author must also be a currently publishing author.",
        "hard_mode": "Published before the year 2000.",
    },
    "B5": {
        "title": "Revenge-Seeking Character",
        "description": "Book has a character whose main motivation in the story is revenge.",
        "hard_mode": "Revenge is central to the plot of the entire book.",
    },
    "C1": {
        "title": "Mystery Plot",
        "description": "The main plot of the book centers around solving a mystery.",
        "hard_mode": "Not a primary world Urban Fantasy (secondary world urban fantasy is okay!)",
    },
    "C2": {
        "title": "Comfort Read",
        "description": "Any book that brings you comfort while reading it. You can use a reread on this square and it WON'T count for your '1 reread'.",
        "hard_mode": "Don't use a reread, find a brand new comfort read!",
    },
    "C3": {
        "title": "Published in 2021",
        "description": "No reprints or new editions.",
        "hard_mode": "It's also a debut novel--as in it's the author's first published novel.",
    },
    "C4": {
        "title": "Cat Squasher: 500+ Pages",
        "hard_mode": "Lion Squasher - a book that is over 800 pages.",
    },
    "C5": {
        "title": "SFF-Related Nonfiction",
        "hard_mode": "Published within the last five years.",
    },
    "D1": {
        "title": "Latinx or Latin American Author",
        "hard_mode": "Book has fewer than 1000 Goodreads ratings.",
    },
    "D2": {
        "title": "Self-Published",
        "hard_mode": "Self-pubbed and has fewer than 50 ratings on Goodreads.",
    },
    "D3": {
        "title": "Forest Setting",
        "description": "This setting must be used be for a good portion of the book.",
        "hard_mode": "The entire book takes place in this setting.",
    },
    "D4": {
        "title": "Genre Mashup",
        "description": "A book that utilizes major elements from two or more genres. Examples: a romance set in a fantasy world, a book that combines science fiction and fantasy, etc.",
        "hard_mode": "Three or more genres are combined.",
    },
    "D5": {
        "title": "Has Chapter Titles",
        "description": "Each chapter has a title (other than numbers or a character's name).",
        "hard_mode": "Chapter title is more than a single word FOR EVERY SINGLE CHAPTER",
    },
    "E1": {
        "title": "Title: _____ of _____",
        "hard_mode": "_____ of ______ and ________.",
    },
    "E2": {
        "title": "First Contact",
        "hard_mode": "War does not break out as a result of contact.",
    },
    "E3": {
        "title": "Trans or Nonbinary Character",
        "description": "A book featuring a trans or nonbinary character that isn't an alien or a robot.",
        "hard_mode": "This character is a main protagonist.",
    },
    "E4": {
        "title": "Debut Author",
        "description": "An author's debut novel or novella.",
        "hard_mode": "The author has participated in an AMA: https://www.reddit.com/r/Fantasy/wiki/amalinks.",
    },
    "E5": {
        "title": "Witches",
        "description": "A book featuring witches. Note - characters practicing what is traditionally in their culture referred to as witchcraft would also count. For example brujos or brujas would count for this square.",
        "hard_mode": "A witch is a main protagonist.",
    },
}


def load_reddit_data():
    with open(Path(__file__).parent / "../data/reddit.json") as f:
        try:
            data = json.load(f)
        except Exception:
            print("No file, creating new data.")
            data = {}
    return data


def write_reddit_data(data):
    with open(Path(__file__).parent / "../data/reddit.json", "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def date_ok(review_date):
    return (review_date.year == YEAR and review_date.month > 3) or (
        review_date.year == (YEAR + 1) and review_date.month < 4
    )


def add_book_squares(data, book):
    click.echo(
        f"Selecting squares for {book.metadata['book']['title']} by {book.metadata['book']['author']}:"
    )
    book_string = book.metadata["book"]["title"]
    pages = book.metadata["book"].get("pages")
    year = book.metadata["book"].get("publication_year")
    if pages and year:
        book_string = f"{book_string} ({pages}p., {year})"
    elif pages:
        book_string = f"{book_string} ({pages}p.)"
    elif year:
        book_string = f"{book_string} ({year})"
    for name, square in SQUARES.items():  # inquirer rudely cuts off even wrapped text
        click.echo("─" * 70)
        click.echo(square["title"])
        if "description" in square:
            click.echo(square["description"])
        click.echo("Hard mode: " + square["hard_mode"])
        question = [
            inquirer.List(
                "q",
                message=book_string,
                choices=[("No", False), ("Yes", True), ("Hard mode woo", 2)],
                default=False,
                carousel=True,
            )
        ]
        answer = inquirer.prompt(question)["q"]
        if answer is False:
            continue
        elif answer is True:
            if name in data:
                data[name]["normal"].append(book.id)
            else:
                data[name] = {"normal": [book.id], "hard": []}
        elif answer == 2:
            if name in data:
                data[name]["hard"].append(book.id)
            else:
                data[name] = {"hard": [book.id], "normal": []}
    if not "hacky" in data:
        data["hacky"] = {"hack": [book.id]}
    else:
        data["hacky"]["hack"].append(book.id)
    click.echo("─" * 70)
    return data


def run_reddit():
    known_data = load_reddit_data()
    known_books = set(
        book
        for value in known_data.values()
        for entry in value.values()
        for book in entry
    )

    all_reviews = load_reviews()
    relevant_books = [book for book in all_reviews if date_ok(book.relevant_date)]
    for book in relevant_books:
        if book.id in known_books:
            continue
        known_data = add_book_squares(known_data, book)
    write_reddit_data(known_data)
