#!/usr/bin/env python3
"""
Anthropic Orbit Scout — daily content discovery for transcribo.

Crawls Anthropic-orbit sources, diffs against manifests/anthropic_manifest.json,
appends NEW URLs to queue files for the user to process locally.

Sources:
  - anthropic.com/{news,research,engineering}        (HTML)
  - claude.com/resources/{tutorials,use-cases}       (HTML)
  - youtube.com/@anthropic-ai, @AndrejKarpathy,
    @JEVanClief                                       (yt-dlp --flat-playlist)
  - karpathy.github.io/feed.xml                       (RSS)

Outputs:
  - urls_pending_anthropic.txt        (videos, one URL per line)
  - articles_pending_anthropic.txt    (text articles, one URL per line)
  - manifests/anthropic_manifest.json (updated in place)

Exit codes:
  0 — no new items
  2 — new items found (caller should commit + open PR)
  1 — unrecoverable error

The script tolerates per-source failures (logs + continues). It only exits 1
if it cannot read the manifest or cannot write the outputs.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "manifests" / "anthropic_manifest.json"
VIDEO_QUEUE = ROOT / "urls_pending_anthropic.txt"
ARTICLE_QUEUE = ROOT / "articles_pending_anthropic.txt"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _make_ssl_context() -> ssl.SSLContext:
    # Prefer certifi bundle (works on macOS python.org distributions where the
    # system trust store is not wired to python by default). Fall back to the
    # OS default context, then to SSL_CERT_FILE env if set.
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    cafile = os.environ.get("SSL_CERT_FILE")
    if cafile and Path(cafile).exists():
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


_SSL_CTX = _make_ssl_context()


def canonical(url: str) -> str:
    """Normalize URLs so diffing is stable across http/https and trailing slash."""
    url = url.strip()
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    # Drop trailing slash on blog-style article paths but keep on root
    if url.endswith("/") and url.count("/") > 3:
        url = url[:-1]
    return url

# --- HTML sources -----------------------------------------------------------
# Each entry: (manifest_key, listing_url, link_regex, is_video, base_origin)
# link_regex must capture the path portion (group 1) that we join with origin.
HTML_SOURCES = [
    (
        "anthropic_news",
        "https://www.anthropic.com/news",
        re.compile(r'href="(/news/[a-z0-9][a-z0-9\-]+)"'),
        False,
        "https://www.anthropic.com",
    ),
    (
        "anthropic_research",
        "https://www.anthropic.com/research",
        re.compile(r'href="(/research/[A-Za-z0-9][A-Za-z0-9\-]+)"'),
        False,
        "https://www.anthropic.com",
    ),
    (
        "anthropic_engineering",
        "https://www.anthropic.com/engineering",
        re.compile(r'href="(/engineering/[A-Za-z0-9][A-Za-z0-9\-]+)"'),
        False,
        "https://www.anthropic.com",
    ),
    (
        "claude_tutorials",
        "https://claude.com/resources/tutorials",
        re.compile(r'href="(/resources/tutorials/[a-z0-9][a-z0-9\-]+)"'),
        False,
        "https://claude.com",
    ),
    (
        "claude_use_cases",
        "https://claude.com/resources/use-cases",
        re.compile(r'href="(/resources/use-cases/[a-z0-9][a-z0-9\-]+)"'),
        False,
        "https://claude.com",
    ),
]

# --- YouTube sources --------------------------------------------------------
YOUTUBE_SOURCES = [
    ("youtube_anthropic_ai", "https://www.youtube.com/@anthropic-ai/videos"),
    ("youtube_karpathy", "https://www.youtube.com/@AndrejKarpathy/videos"),
    ("youtube_van_clief", "https://www.youtube.com/@JEVanClief/videos"),
    ("youtube_taylor_haren", "https://www.youtube.com/@TaylorAHaren/videos"),
]

# --- RSS sources ------------------------------------------------------------
RSS_SOURCES = [
    ("karpathy_blog", "https://karpathy.github.io/feed.xml"),
]


def http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def crawl_html(listing_url: str, link_re: re.Pattern, origin: str) -> set[str]:
    try:
        html = http_get(listing_url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  ! fetch failed: {exc}", file=sys.stderr)
        return set()
    paths = set(link_re.findall(html))
    return {canonical(origin + p) for p in paths}


YT_ID_RE = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def crawl_youtube(channel_url: str) -> set[str]:
    # Prefer yt-dlp (robust), fall back to HTML regex on the channel page.
    try:
        out = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--print",
                "%(id)s",
                "--playlist-end",
                "60",
                channel_url,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if out.returncode == 0 and out.stdout.strip():
            ids = {line.strip() for line in out.stdout.splitlines() if line.strip()}
            return {canonical(f"https://www.youtube.com/watch?v={vid}") for vid in ids}
        print(f"  ! yt-dlp rc={out.returncode}: {out.stderr[:200]}", file=sys.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"  ! yt-dlp unavailable ({exc}); falling back to HTML", file=sys.stderr)

    try:
        html = http_get(channel_url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  ! HTML fallback failed: {exc}", file=sys.stderr)
        return set()
    ids = set(YT_ID_RE.findall(html))
    return {canonical(f"https://www.youtube.com/watch?v={vid}") for vid in ids}


def crawl_rss(feed_url: str) -> set[str]:
    try:
        xml = http_get(feed_url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"  ! RSS fetch failed: {exc}", file=sys.stderr)
        return set()
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        print(f"  ! RSS parse failed: {exc}", file=sys.stderr)
        return set()
    urls = set()
    # Atom: entry/link[@href]   |   RSS 2.0: item/link (text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//a:entry", ns):
        link = entry.find("a:link", ns)
        if link is not None and link.get("href"):
            urls.add(canonical(link.get("href")))
    for item in root.findall(".//item"):
        link = item.find("link")
        if link is not None and link.text:
            urls.add(canonical(link.text))
    return urls


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"manifest missing at {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text())

    new_videos: list[str] = []
    new_articles: list[str] = []
    per_source_new: dict[str, list[str]] = {}

    def diff_and_record(key: str, found: set[str], is_video: bool) -> None:
        known = set(manifest.get(key, []))
        delta = sorted(found - known)
        if not delta:
            print(f"  = {key}: 0 new ({len(found)} total)")
            return
        per_source_new[key] = delta
        manifest[key] = sorted(known | set(delta))
        if is_video:
            new_videos.extend(delta)
        else:
            new_articles.extend(delta)
        print(f"  + {key}: {len(delta)} new")

    print("== HTML sources ==")
    for key, url, link_re, is_video, origin in HTML_SOURCES:
        print(f"- {key} <- {url}")
        diff_and_record(key, crawl_html(url, link_re, origin), is_video)

    print("== YouTube channels ==")
    for key, url in YOUTUBE_SOURCES:
        print(f"- {key} <- {url}")
        diff_and_record(key, crawl_youtube(url), is_video=True)

    print("== RSS feeds ==")
    for key, url in RSS_SOURCES:
        print(f"- {key} <- {url}")
        diff_and_record(key, crawl_rss(url), is_video=False)

    total_new = len(new_videos) + len(new_articles)
    if total_new == 0:
        print("\nNo new items.")
        return 0

    # Append to queues (idempotent: only add lines not already present)
    def append_queue(path: Path, urls: list[str]) -> None:
        existing = set()
        if path.exists():
            existing = {line.strip() for line in path.read_text().splitlines() if line.strip()}
        to_add = [u for u in urls if u not in existing]
        if not to_add:
            return
        with path.open("a") as fh:
            for u in to_add:
                fh.write(u + "\n")

    append_queue(VIDEO_QUEUE, sorted(new_videos))
    append_queue(ARTICLE_QUEUE, sorted(new_articles))

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"\n== SUMMARY: {total_new} new items ==")
    for key, items in per_source_new.items():
        print(f"\n### {key} ({len(items)})")
        for u in items:
            print(f"- {u}")

    return 2


if __name__ == "__main__":
    sys.exit(main())
