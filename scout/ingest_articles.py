#!/usr/bin/env python3
"""
Local-only article ingest for transcribo (text counterpart of cli_pipeline.py).

For each URL in a list:
  1. Skip if `<slug>.knowledge.md` already exists in the transcribo root.
  2. Fetch the page via trafilatura (clean article extraction).
  3. Write `<slug>.knowledge.md` in the same shape as transcript files
     (YAML frontmatter + body), so wiki ingest treats both uniformly.
  4. Copy to the kDrive source dir if KDRIVE_DEST exists.
  5. Print a wiki-ingest hint at the end (operator runs that manually
     to keep the wiki author-in-the-loop).

This script does NOT touch the wiki. It only emits .knowledge.md files
and copies them to the kDrive immutable raw layer.

Usage:
    python3 scout/ingest_articles.py --from-file articles_pending_anthropic.txt
    python3 scout/ingest_articles.py "https://www.anthropic.com/news/foo"
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
from pathlib import Path

import trafilatura

ROOT = Path(__file__).resolve().parent.parent
KDRIVE_DEST = Path(
    "/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/"
    "Administración/Colaboraciones, financiación, compras/Formaciones/"
    "0. Conocimiento Albert"
)


def slug_from_url(url: str) -> str:
    """Derive a filesystem-safe slug from a URL's last path segment."""
    path = url.rstrip("/").rsplit("/", 1)[-1]
    # Strip trailing query/fragments, fall back to host if path is empty
    path = re.sub(r"[?#].*$", "", path)
    if not path:
        path = url.rstrip("/").rsplit("/", 1)[-1] or "index"
    # Normalize to ascii-safe filename
    path = re.sub(r"[^A-Za-z0-9._-]+", "_", path)
    return path[:120]


def extract_article(url: str) -> tuple[str, str, str] | None:
    """Returns (title, body_markdown, author) or None on failure."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    body_md = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_links=True,
        include_images=False,
        include_tables=True,
        include_comments=False,
        favor_precision=True,
    )
    if not body_md:
        return None
    meta = trafilatura.extract_metadata(downloaded)
    title = (meta.title if meta else None) or slug_from_url(url)
    author = (meta.author if meta else None) or ""
    return title, body_md, author


def write_knowledge_md(url: str, slug: str, title: str, body_md: str, author: str) -> Path:
    """Mirror the transcript .knowledge.md shape so wiki ingest handles both."""
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    # Escape double quotes in YAML scalars
    safe_title = title.replace('"', '\\"')
    safe_author = author.replace('"', '\\"')
    front = (
        "---\n"
        f'title: "{safe_title}"\n'
        f'source_url: "{url}"\n'
        f"source_type: web_article\n"
        f'fetched: "{now}"\n'
        f'extraction_engine: "trafilatura"\n'
        f'author: "{safe_author}"\n'
        "---\n\n"
    )
    body = f"# {title}\n\n## Full Content\n\n{body_md}\n"
    out = ROOT / f"{slug}.knowledge.md"
    out.write_text(front + body)
    return out


def copy_to_kdrive(path: Path) -> bool:
    if not KDRIVE_DEST.exists():
        return False
    shutil.copy2(path, KDRIVE_DEST / path.name)
    return True


def load_urls(args) -> list[str]:
    urls: list[str] = []
    if args.from_file:
        for line in Path(args.from_file).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    urls.extend(args.urls)
    # Dedupe preserving order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", nargs="*", help="URLs to ingest")
    ap.add_argument("--from-file", "-f", help="File with one URL per line")
    ap.add_argument(
        "--no-kdrive",
        action="store_true",
        help="Skip copy to kDrive (testing only)",
    )
    args = ap.parse_args()

    urls = load_urls(args)
    if not urls:
        ap.error("provide URLs as args or --from-file")

    stats = {"done": 0, "skipped": 0, "failed": 0, "kdrive_copied": 0}
    written: list[Path] = []

    for i, url in enumerate(urls, 1):
        slug = slug_from_url(url)
        target = ROOT / f"{slug}.knowledge.md"
        prefix = f"[{i}/{len(urls)}]"

        if target.exists():
            print(f"{prefix} SKIP (exists): {target.name}")
            stats["skipped"] += 1
            continue

        try:
            result = extract_article(url)
        except Exception as exc:
            print(f"{prefix} FAIL (exception): {url} :: {exc}", file=sys.stderr)
            stats["failed"] += 1
            continue

        if not result:
            print(f"{prefix} FAIL (no content): {url}", file=sys.stderr)
            stats["failed"] += 1
            continue

        title, body_md, author = result
        path = write_knowledge_md(url, slug, title, body_md, author)
        print(f"{prefix} DONE: {path.name}  ({len(body_md)} chars)")
        stats["done"] += 1
        written.append(path)

        if not args.no_kdrive and copy_to_kdrive(path):
            stats["kdrive_copied"] += 1

    print(
        f"\n== SUMMARY == done={stats['done']} skipped={stats['skipped']} "
        f"failed={stats['failed']} kdrive_copied={stats['kdrive_copied']}"
    )

    if written:
        print("\nNext: ingest these into the wiki at ~/wiki-conocimiento/")
        print("(follow the workflow in CLAUDE.md — sources.yaml, wiki page, index, log, schema, link-check)")

    return 0 if stats["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
