import datetime as dt
import json
import subprocess
import textwrap

import tweepy
from mastodon import Mastodon


def _print_tweet(tweet_data):
    text = tweet_data["text"]
    media = tweet_data.get("media")
    print_lines = []
    lines = text.split("\n")
    if media:
        lines.append("")
        lines.append(f"* with media file {media}")
    text_width = 50
    buffer_width = text_width + 2
    for line in lines:
        print_lines += textwrap.wrap(line, text_width)
    print("┏" + "━" * buffer_width + "┓")
    print("┃" + " " * buffer_width + "┃")
    for line in print_lines:
        print("┃ " + line.ljust(text_width) + " ┃")
    print("┃" + " " * buffer_width + "┃")
    print("┗" + "━" * buffer_width + "┛")


def _send_tweet(tweet_data):
    auth_data = json.load(open("auth.json"))["twitter"]
    auth = tweepy.OAuthHandler(auth_data["api_key"], auth_data["api_secret"])
    auth.set_access_token(
        auth_data["access_token_key"], auth_data["access_token_secret"]
    )
    api = tweepy.API(auth)
    if tweet_data.get(
        "media"
    ):  # currently unused, cover image quality is too inconsistent
        result = api.update_with_media(
            tweet_data["media"],
            tweet_data["text"],
            in_reply_to_status_id=tweet_data.get(
                "in_reply_to"
            ),  # or "1276612774735511552",
        )
    else:
        result = api.update_status(
            tweet_data["text"],
            in_reply_to_status_id=tweet_data.get(
                "in_reply_to"
            ),  # or "1276612774735511552"
        )
    return result


def _send_toot(toot_data):
    auth = json.load(open("auth.json"))
    mastodon = Mastodon(
        access_token=auth["mastodon"]["access_token"],
        api_base_url="https://chaos.social",
    )
    result = mastodon.status_post(
        toot_data["text"], in_reply_to_id=toot_data.get("in_reply_to")
    )  # or "104412156609066689"
    return result


def tweet(review, tweet_data, dry_run=False):
    if review.metadata.get("social", {}).get("twitter", {}).get("id"):
        raise Exception("Already tweeted, aborting.")

    _print_tweet(tweet_data)
    print(f"Replying to https://twitter.com/rixxtr/status/{tweet_data['in_reply_to']}")
    if dry_run:
        return
    result = _send_tweet(tweet_data)
    tweet_data["id"] = str(result.id)
    tweet_data["datetime"] = dt.datetime.now()
    review.metadata["social"]["twitter"] = tweet_data
    review.save()


def toot(review, toot_data, dry_run=False):
    toot_data["text"] += " #rixxReads"
    if review.metadata.get("social", {}).get("mastodon", {}).get("id"):
        raise Exception("Already tooted, aborting.")

    _print_tweet(toot_data)
    print(f"Replying to https://chaos.social/web/statuses/{toot_data['in_reply_to']}")
    if dry_run:
        return
    result = _send_toot(toot_data)
    toot_data["id"] = str(result["id"])
    toot_data["datetime"] = dt.datetime.now()
    review.metadata["social"]["mastodon"] = toot_data
    review.save()


def post(review, number, in_reply_to=None, dry_run=False):
    text = review.metadata.get("review", {}).get("tldr")
    if not text:
        raise Exception("No tl;dr text found, aborting.")
    text = f"{number}/ {review.metadata['book']['title']} by {review.metadata['book']['author']}. {text}"
    print(f"Tweet length: {len(text) + 24}/280")
    if len(text) > (280 - 1 - 23):  # URLs are always 23 chars
        raise Exception("tl;dr too long")
    text = f"{text}\nhttps://books.rixx.de/{review.get_core_path()}/"

    if not review.metadata.get("social"):
        review.metadata["social"] = {}
    review.metadata["social"]["number"] = number

    tweet_data = {
        "text": text,
        "in_reply_to": in_reply_to.metadata.get("social", {}).get("twitter", {})["id"]
        if in_reply_to
        else None,
    }
    toot_data = {
        "text": text,
        "in_reply_to": in_reply_to.metadata.get("social", {}).get("mastodon", {})["id"]
        if in_reply_to
        else None,
    }
    tweet(review, tweet_data, dry_run=dry_run)
    toot(review, toot_data, dry_run=dry_run)


def post_next(dry_run=False):
    from .books import _load_entries

    current_year = dt.datetime.now().year
    reviews = _load_entries(dirpath=f"src/reviews/{current_year}")
    reviews = sorted(reviews, key=lambda x: x.relevant_date)

    last_review = None
    for review in reviews:
        social = review.metadata.get("social", {})
        if not review.metadata["review"].get("tldr"):
            subprocess.check_call(
                ["xdg-open", "_html/" + str(review.get_core_path() / "index.html")]
            )
            raise Exception(f"Missing tldr! Please fix: {review.path}")
        if social and social.get("twitter", "id") and social.get("mastodon", "id"):
            last_review = review
        else:
            break
    past_number = last_review.metadata["social"]["number"] if last_review else 0
    post(review, number=past_number + 1, in_reply_to=last_review, dry_run=dry_run)
