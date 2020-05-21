# books.rixx.de

This is the source code for <https://books.rixx.de>, where track the books I've read, and that I want to read.
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

- `helferlein auth` to get and save your Goodreads credentials
- `helferlein books` to add or modify books. This is an interactive command that will let you search and modify books,
  pull data from Goodreads, or push data to Goodreads.
- `helferlein build` to build the site

## Related work

Thanks go to Lexie who inspired me with [books.alexwlchan.net](https://books.alexwlchan.net/)
([source](https://git.alexwlchan.net/?a=summary&p=books.alexwlchan.net)) and allowed me to nick the data input scripts.
