import csv
import json
import pathlib
import sys

import click


@click.group()
@click.version_option()
def cli():
    "Save data from Goodreads to a SQLite database"


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
    saved_user_id = auth_data.get("goodreads_user_id")
    click.echo(
        "Create a Goodreads developer key at https://www.goodreads.com/api/keys and paste it here:"
    )
    personal_token = click.prompt("Developer key")
    click.echo()
    click.echo(
        "Please enter your Goodreads user ID (numeric) or just paste your Goodreads profile URL."
    )
    user_id = click.prompt("User-ID or URL", default=saved_user_id)
    user_id = user_id.strip("/").split("/")[-1].split("-")[0]
    if not user_id.isdigit():
        raise Exception(
            "Your user ID has to be a number! {} does not look right".format(user_id)
        )
    auth_data["goodreads_personal_token"] = personal_token
    auth_data["goodreads_user_id"] = user_id
    open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")
    auth_suffix = (" -a " + auth) if auth != "auth.json" else ""
    click.echo()
    click.echo(
        "Your authentication credentials have been saved to {}. You can now pull or push data by running".format(
            auth
        )
    )
    click.echo()
    click.echo("    helferlein books books.db")
    click.echo()


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to load goodreads credentials from, defaults to auth.json",
)
def books(auth):
    """Save books for a specified user, e.g. rixx"""
    pass


@cli.command()
def build():
    pass
