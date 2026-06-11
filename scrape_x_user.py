#!/usr/bin/env python3
"""
Scrape tweets from an X/Twitter user since a given date, filtering for videos.

Uses twikit for the X API + browser_cookie3 to reuse an active Chrome session
(no password prompt). Outputs status URLs (one per line) to stdout.

Usage:
    python3 scrape_x_user.py @planepowers --since 2026-01-01 --videos-only
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone

import browser_cookie3
from twikit import Client


def load_chrome_cookies() -> dict:
    cj = browser_cookie3.chrome(domain_name=".x.com")
    return {c.name: c.value for c in cj}


async def fetch_user_tweets(screen_name: str, since_date: datetime, videos_only: bool):
    cookies = load_chrome_cookies()
    for required in ("auth_token", "ct0"):
        if required not in cookies:
            raise RuntimeError(
                f"Cookie '{required}' not found in Chrome for .x.com — log into x.com in Chrome first."
            )

    client = Client("en-US")
    client.set_cookies(cookies)

    user = await client.get_user_by_screen_name(screen_name.lstrip("@"))
    print(f"# User: @{user.screen_name} ({user.id}) -- {user.followers_count} followers", file=sys.stderr)

    total_seen = 0
    yielded = 0
    tweets = await user.get_tweets("Tweets")
    while tweets:
        for t in tweets:
            total_seen += 1
            # tweet.created_at is a string like "Wed Apr 16 20:38:00 +0000 2026"
            created = datetime.strptime(t.created_at, "%a %b %d %H:%M:%S %z %Y")
            if created < since_date:
                # Past the date boundary -- since the timeline is reverse-chronological,
                # we can stop pagination once we hit an older tweet.
                print(f"# Hit date boundary at tweet {t.id} ({created}). Stopping.", file=sys.stderr)
                return

            has_video = False
            if t.media:
                for m in t.media:
                    if getattr(m, "type", None) == "video":
                        has_video = True
                        break

            if videos_only and not has_video:
                continue

            yielded += 1
            url = f"https://x.com/{user.screen_name}/status/{t.id}"
            snippet = (t.text or "").replace("\n", " ")[:80]
            print(f"{url}  # {created:%Y-%m-%d}  {snippet}")

        print(f"# {total_seen} tweets scanned, {yielded} videos emitted so far...", file=sys.stderr)
        try:
            tweets = await tweets.next()
        except Exception as e:
            print(f"# Pagination stopped: {e}", file=sys.stderr)
            break

    print(f"# Done. {total_seen} tweets scanned, {yielded} videos total.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("screen_name", help="X user (with or without @)")
    parser.add_argument("--since", required=True, help="ISO date, e.g. 2026-01-01")
    parser.add_argument("--videos-only", action="store_true", help="Only emit status URLs with video media")
    args = parser.parse_args()

    since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    asyncio.run(fetch_user_tweets(args.screen_name, since, args.videos_only))


if __name__ == "__main__":
    main()
