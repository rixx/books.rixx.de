from setuptools import setup

setup(
    name="books-rixx-de",
    author="Tobias Kunze",
    author_email="r@rixx.de",
    url="https://github.com/rixx/books.rixx.de",
    packages=["scripts"],
    entry_points="""
        [console_scripts]
        books=scripts.cli:cli
    """,
    install_requires=[
        "aiohttp==3.7.*",
        "attrs==19.3.*",
        "bs4",
        "click",
        "hyperlink==19.0.*",
        "inquirer==2.6.*",
        "jinja2==2.11.*",
        "markdown==3.1.*",
        "mastodon.py",
        "networkx==2.5.*",
        "pillow==8.4.*",
        "python-dateutil",
        "python-frontmatter==0.5.*",
        "rauth",
        "requests",
        "sklearn",
        "smartypants==2.0.*",
        "unidecode==1.1.*",
        "tweepy",
    ],
)
