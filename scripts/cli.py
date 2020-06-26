import json
import pathlib
import sys

import click
import inquirer
from rauth.service import OAuth1Service

from .books import change_book, change_tags, create_book
from .goodreads import get_shelves
from .renderer import build_site


@click.group(invoke_without_command=True)
@click.version_option()
def cli(*lol, **trololol):
    "Interact with the data fueling books.rixx.de"
    if len(sys.argv) > 1:
        return
    inquirer.list_input(
        message="What do you want to do?",
        choices=(
            ("Add a new book", create_book),
            ("Edit an existing book", change_book),
            ("Tag books", change_tags),
            ("Build the site", build_site),
        ),
    )()


@cli.command()
def auth():
    "Save authentication credentials to a JSON file"
    auth = "auth.json"
    auth_data = {}
    if pathlib.Path(auth).exists():
        auth_data = json.load(open(auth))
    click.echo(
        "Create a Goodreads developer key at https://www.goodreads.com/api/keys and paste it here:"
    )
    developer_key = click.prompt(
        "Developer key", default=auth_data.get("goodreads_developer_key", "")
    )
    click.echo("Please also paste the secret:")
    developer_secret = click.prompt(
        "Developer secret", default=auth_data.get("goodreads_developer_secret")
    )
    click.echo()
    click.echo(
        "Please enter your Goodreads user ID (numeric) or just paste your Goodreads profile URL."
    )
    user_id = click.prompt(
        "User-ID or URL", default=auth_data.get("goodreads_user_id", "")
    )
    user_id = user_id.strip("/").split("/")[-1].split("-")[0]
    if not user_id.isdigit():
        raise Exception(
            "Your user ID has to be a number! {} does not look right".format(user_id)
        )
    auth_data["goodreads_developer_key"] = developer_key
    auth_data["goodreads_developer_secret"] = developer_secret
    auth_data["goodreads_user_id"] = user_id
    auth_data["shelves"] = get_shelves(auth_data)

    open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")

    if not (
        auth_data.get("goodreads_user_access_token")
        and auth_data.get("goodreads_user_access_secret")
    ):
        oauth_service = OAuth1Service(
            consumer_key=auth_data["goodreads_developer_key"],
            consumer_secret=auth_data["goodreads_developer_secret"],
            name="goodreads",
            request_token_url="https://www.goodreads.com/oauth/request_token",
            authorize_url="https://www.goodreads.com/oauth/authorize",
            access_token_url="https://www.goodreads.com/oauth/access_token",
            base_url="https://www.goodreads.com/",
        )
        request_token, request_token_secret = oauth_service.get_request_token(
            header_auth=True
        )
        authorize_url = oauth_service.get_authorize_url(request_token)
        click.prompt("Visit this URL in your browser: " + authorize_url)
        session = oauth_service.get_auth_session(request_token, request_token_secret)
        auth_data["goodreads_user_access_token"] = session.access_token
        auth_data["goodreads_user_access_secret"] = session.access_token_secret

        open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")

    click.echo(
        "All done. You can now add books with `books add` or change them with `books edit`, and the changes will be pushed to Goodreads."
    )


@cli.command()
def build():
    """ Build the site, putting output into _html/ """
    build_site()


@cli.command()
def new():
    """ Add a new book """
    create_book()


@cli.command()
def add():
    """ Add a new book """
    create_book()


@cli.command()
def edit():
    """ Edit a book """
    change_book()


@cli.command()
def load():
    """ Import book data from a goodreads-to-sqlite database. """
    from .importer import import_books

    import_books()


@cli.command()
@click.option("--dry-run", "dry_run", default=False, type=bool, is_flag=True)
def social(dry_run):
    """ Import book data from a goodreads-to-sqlite database. """
    from .social import post_next

    post_next(dry_run=dry_run)
