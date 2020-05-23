import json
import pathlib

import click
import inquirer
from rauth.service import OAuth1Service

from .books import change_book, create_book
from .goodreads import get_shelves
from .renderer import build_site


@click.group()
@click.version_option()
def cli():
    "Interact with the data fueling books.rixx.de"


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save tokens to, defaults to ./auth.json.",
)
def auth(auth):
    "Save authentication credentials to a JSON file"
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


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to load goodreads credentials from, defaults to auth.json",
)
def books(auth):
    while True:
        action = inquirer.list_input(
            message="What do you want to do?",
            choices=["Add a new book", "Change book status", "Build the site", "quit"],
            carousel=True,
        )
        if action == "quit":
            break
        if action == "Build the site":
            build_site()
            break
        if action == "Add a new book":
            create_book(auth=auth)
        elif action == "Change book status":
            change_book(auth=auth)


@cli.command()
def build():
    """ Build the site, putting output into _html/ """
    build_site()


@cli.command()
def load():
    """ Import book data from a sqlite database, in the format provided by goodreads-to-sqlite. """
    from .importer import import_books

    import_books()
