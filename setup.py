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
        "attrs==19.3.*",
        "click",
        "hyperlink==19.0.*",
        "inquirer==2.6.*",
        "jinja2==2.11.*",
        "markdown==3.1.*",
        "mastodon.py",
        "pillow==7.0.*",
        "python-dateutil",
        "python-frontmatter==0.5.*",
        "rauth",
        "requests",
        "smartypants==2.0.*",
        "unidecode==1.1.*",
        "tweepy",
    ],
)
