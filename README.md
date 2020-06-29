# books.rixx.de

This is the source code for <https://books.rixx.de>, where I track the books I've read, and that I want to read.
This repo contains both the scripts that build the site, and the source data used by the scripts.

## How it works

Each book is a text file, with a bit of metadata at the top, and Markdown text in the body. When I run the build script,
it reads all these files, and turns them into a set of HTML files. I upload a copy of those HTML files to my web server,
where they're served by nginx.

The data entry is eased by a data entry script that allows me to add books to any of the three piles, and can also pull
(book) data from Goodreads or push data (my reading state) to Goodreads. But this repo and its contents are the primary
data source.

## Usage

In a virtualenv, run `pip install -e .`. Then you can run:

- `books` to get to a menu that allows you to add/edit books, or bulk-edit tags.
- `books auth` to get and save your Goodreads credentials
- `books social` to post to social media. My nick and name are currently hardcoded.
- `books build` to build the site, creates the `_html` directory
- `books load` to bulk-import book data from a database in the format created by
  [goodreads-to-sqlite](https://github.com/rixx/goodreads-to-sqlite). It's very specific to my stuff and you probably
  want to touch it up before using it.

## Related work

Thanks go to Lexie who inspired me with [books.alexwlchan.net](https://books.alexwlchan.net/)
([source](https://git.alexwlchan.net/?a=summary&p=books.alexwlchan.net)) and allowed me to nick the data input scripts.
