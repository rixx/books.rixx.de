import json
import pathlib
import sys
from functools import wraps

import click
from rauth.service import OAuth1Service

from .books import change_book, create_book
from .goodreads import get_shelves
from .renderer import build_site


def show_help_if_no_args(func):
    """
    This decorator shows meaningful message in case of no parameters passed
    to CLI callback
    TODO: to remove it when https://github.com/pallets/click/pull/804 will be
    merged
    :param func:
    :return:
    """

    @wraps(func)
    def inner(*args, **kwargs):
        # filter all None values,
        res = filter(lambda x: x is not None, kwargs.itervalues())
        # check if all values are boolean with False
        if len(res) == res.count(False):
            click.echo("No parameters passed please use -h/--help for usage")
            sys.exit(1)
        return func(*args, **kwargs)

    return inner


@click.group()
@show_help_if_no_args
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

    click.echo(
        "All done. You can now add books with `books add` or change them with `books edit`, and the changes will be pushed to Goodreads."
    )


@cli.command()
def build():
    """ Build the site, putting output into _html/ """
    build_site()


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to load goodreads credentials from, defaults to auth.json",
)
def new(auth):
    """ Add a new book """
    auth_data = json.load(open(auth))
    create_book(auth=auth_data)


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to load goodreads credentials from, defaults to auth.json",
)
def edit(auth):
    """ Edit a book """
    auth_data = json.load(open(auth))
    change_book(auth=auth_data)


@cli.command()
def load():
    """ Import book data from a goodreads-to-sqlite database. """
    from .importer import import_books

    import_books()
