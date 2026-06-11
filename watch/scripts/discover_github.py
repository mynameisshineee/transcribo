#!/usr/bin/env python3
"""
discover_github.py — Descubre actividad pública de un usuario/repo GitHub
vía atom feeds (sin API key, sin auth).

GitHub expone:
  - https://github.com/{user}.atom   → actividad pública del usuario
  - https://github.com/{user}.atom?  → idem para org
  - https://github.com/{owner}/{repo}/commits/main.atom → commits del repo en main
  - https://github.com/{owner}/{repo}/releases.atom → releases
  - https://gist.github.com/{user}.atom → gists públicos

Estos feeds son la forma oficial de monitorear sin API key.
"""

from __future__ import annotations

import datetime
import os
import re
import ssl
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

ATOM_NS = "{http://www.w3.org/2005/Atom}"

# macOS workaround: usa certifi como CA bundle si está disponible
# (evita "SSL: CERTIFICATE_VERIFY_FAILED" en venvs)
_SSL_CTX = None
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    if os.path.exists("/etc/ssl/cert.pem"):
        _SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def fetch_atom(url: str, timeout: int = 30) -> list[dict] | None:
    """Descarga + parsea un atom feed. Devuelve lista de entries o None si error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "wiki-watch/1.0 (+BiK)"})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            data = resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        print(f"  ERROR parsing atom from {url}: {e}")
        return None

    entries = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        eid = entry.findtext(f"{ATOM_NS}id", default="")
        title = (entry.findtext(f"{ATOM_NS}title", default="") or "").strip()
        updated = entry.findtext(f"{ATOM_NS}updated", default="")
        link_el = entry.find(f"{ATOM_NS}link")
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        content = (entry.findtext(f"{ATOM_NS}content", default="") or "")[:500]
        # author
        author_el = entry.find(f"{ATOM_NS}author/{ATOM_NS}name")
        author = author_el.text.strip() if (author_el is not None and author_el.text) else ""

        entries.append({
            "id": eid,
            "title": title,
            "updated": updated,
            "link": link,
            "author": author,
            "content_excerpt": content,
        })
    return entries


def parse_iso8601(s: str) -> datetime.datetime | None:
    if not s:
        return None
    # 2026-05-11T07:14:23Z → quitar Z
    s = s.replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        return None


def discover_github_user(source: dict, since_days: int = 7) -> list[dict]:
    """Actividad reciente de un usuario."""
    feed_url = source.get("feed_url") or f"https://github.com/{source['handle']}.atom"
    print(f"[{source['id']}] GitHub user feed: {feed_url}")
    entries = fetch_atom(feed_url)
    if entries is None:
        return []

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=since_days)
    recent = []
    for e in entries:
        dt = parse_iso8601(e["updated"])
        if dt and dt >= cutoff:
            recent.append({
                "source_id": source["id"],
                "type": "github_user_activity",
                "id": e["id"],
                "title": e["title"],
                "link": e["link"],
                "updated": e["updated"],
                "author": e["author"],
                "excerpt": e["content_excerpt"],
            })
    print(f"  {len(recent)} eventos en últimos {since_days} días")
    return recent


def discover_github_repo(source: dict, since_days: int = 7) -> list[dict]:
    """Eventos recientes de un repo (commits o releases)."""
    base = source["url"].rstrip("/")
    feed_type = source.get("feed_type", "commits")
    if feed_type == "releases":
        feed_url = f"{base}/releases.atom"
    elif feed_type == "commits":
        # asume rama main; si no existe atom devolverá 404 silenciosamente
        feed_url = f"{base}/commits/main.atom"
    else:
        feed_url = f"{base}.atom"

    print(f"[{source['id']}] GitHub repo {feed_type} feed: {feed_url}")
    entries = fetch_atom(feed_url)
    if entries is None:
        return []

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=since_days)
    recent = []
    for e in entries:
        dt = parse_iso8601(e["updated"])
        if dt and dt >= cutoff:
            recent.append({
                "source_id": source["id"],
                "type": f"github_repo_{feed_type}",
                "id": e["id"],
                "title": e["title"],
                "link": e["link"],
                "updated": e["updated"],
                "author": e["author"],
                "excerpt": e["content_excerpt"],
            })
    print(f"  {len(recent)} {feed_type} en últimos {since_days} días")
    return recent


if __name__ == "__main__":
    # CLI test
    import sys
    if len(sys.argv) < 2:
        print("Usage: discover_github.py <handle>")
        sys.exit(1)
    handle = sys.argv[1]
    items = discover_github_user({"id": "test", "handle": handle})
    for it in items[:10]:
        print(f"  {it['updated'][:10]} | {it['title'][:80]}")
