#!/usr/bin/env python3
"""
discover_web_rss.py — Discovery handler para fuentes tipo web_rss.

Plane.so, Anthropic news/engineering, etc. NO exponen RSS funcional. Este
módulo scrape la página índice de blog y extrae links a posts nuevos.
Dedup por URL completa contra el backlog.md.

API:
    discover_web_blog(source, backlog_text, limit) -> list[dict]
        cada dict: {url, slug, path}

El handler `watch.py` se encarga de loggear errores y de poblar backlog.
"""

from __future__ import annotations

import os
import re
import ssl
import urllib.parse
import urllib.request

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    if os.path.exists("/etc/ssl/cert.pem"):
        _SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    else:
        _SSL_CTX = ssl.create_default_context()

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


def _fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def discover_web_blog(
    source: dict, backlog_text: str = "", limit: int = 30
) -> list[dict]:
    """Scrape el índice HTML del blog y devuelve posts no vistos.

    Source debe declarar:
        url: URL de la página índice (ej. https://plane.so/blog)
        post_url_pattern: regex que matchea la ruta del post completo
            (default: r"^/[^/]+/[^/?#]+$" — un nivel anidado, sin trailing slug)

    Dedup: posts cuya URL completa ya aparezca en backlog_text se filtran.
    Devuelve lista de {url, slug, path, source_id}.
    """
    index_url = source["url"]
    pat_str = source.get("post_url_pattern", r"^/[^/]+/[^/?#]+$")
    post_re = re.compile(pat_str)
    parsed = urllib.parse.urlparse(index_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    html = _fetch(index_url)

    seen: set[str] = set()
    posts: list[dict] = []
    for m in re.finditer(r'href="([^"]+)"', html):
        href = m.group(1)
        if href.startswith("http"):
            p = urllib.parse.urlparse(href)
            if p.netloc != parsed.netloc:
                continue
            path = p.path
        else:
            path = href.split("?", 1)[0].split("#", 1)[0]
        if not post_re.match(path):
            continue
        full_url = urllib.parse.urljoin(base + "/", path)
        if full_url in seen:
            continue
        seen.add(full_url)
        if full_url in backlog_text:
            continue
        slug = path.rstrip("/").split("/")[-1]
        posts.append({
            "url": full_url,
            "slug": slug,
            "path": path,
            "source_id": source["id"],
        })
        if len(posts) >= limit:
            break
    return posts
