from contextlib import suppress


class Quote:
    def __init__(self, text, book=None, author=None, path=None, language=None):
        self.book = book
        self.author = author
        self.path = path
        self.language = language
        self.text = self.parse_text(text)

    def parse_text(self, text):
        # TODO last line beginning with # contains attribution
        return text.strip()

    def __str__(self):
        result = "Quote"
        if self.book:
            result = f"{result} by {self.book.author} in {self.book.title}"
        elif self.author:
            result = f"{result} by {self.author}"
        result += f": “{self.text[:40]}[…]”"
        return result


def parse_quote_file(path, author=None, book=None):
    with open(path) as fp:
        content = fp.read()

    quote_blocks = content.split("\n%\n")
    quotes = []
    for block in quote_blocks:
        if block.strip():
            with suppress(Exception):
                quotes.append(Quote(block, author=author, book=book, path=path))
    return quotes


if __name__ == "__main__":
    import glob

    has_linebreaks = set()
    quote_files = glob.glob("data/reviews/**/quotes*.txt") + glob.glob(
        "data/reviews/**/**/quotes*.txt"
    )
    all_quote_files = []
    for _file in quote_files:
        for quote in parse_quote_file(_file):
            if "\n" in quote.text:
                has_linebreaks.add(quote.path)
    for path in has_linebreaks:
        print(path)
