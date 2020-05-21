import json
import pathlib

import click
import inquirer

from . import utils


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
    auth_data["shelves"] = utils.get_shelves(auth_data)
    open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")
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
    while True:
        action = inquirer.list_input(
            message="What do you want to do?",
            choices=["Add a new book", "Change book status", "Build the site", "quit"],
        )
        if action == "quit":
            break
        if action == "Build the site":
            build()
            break
        if action == "Add a new book":
            utils.add_book(auth=auth)
        elif action == "Change book status":
            utils.change_book(auth=auth)


@cli.command()
def build():
    utils.build()
