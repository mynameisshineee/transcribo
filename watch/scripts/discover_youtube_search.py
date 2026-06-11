#!/usr/bin/env python3
"""
discover_youtube_search.py — busca vídeos YouTube por query y filtra los nuevos.

Usa yt-dlp con ytsearchN: prefix (sin API key).

Limitaciones documentadas:
- yt-dlp ytsearch devuelve resultados ordenados por relevancia (no fecha)
- Para captar SOLO recientes filtramos por upload_date y conteo de views
- View count actúa como filtro de calidad (mucho ruido si no se filtra)
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess


YT_DLP_FLAGS = [
    "--cookies-from-browser", "chrome",
    "--remote-components", "ejs:github",
]


def discover_youtube_search(source: dict, limit: int = 15, min_views: int = 500,
                             max_age_days: int = 30) -> list[dict]:
    """Busca en YouTube y devuelve candidatos recientes con views >= min_views.

    Usa ytsearchdate prefix para ordenar por fecha descendente (recientes primero).
    Esto evita capturar el catálogo histórico cada vez que se busca.
    """
    query = source["query"]
    # Usa la URL de búsqueda YouTube con filtro sp=CAI%253D (sort by upload date descendente).
    # ytsearch builtin solo soporta sort-by-relevance, lo cual mete el catálogo histórico
    # de cada autor en cada scan.
    import urllib.parse
    q_enc = urllib.parse.quote_plus(query)
    search_url = f"https://www.youtube.com/results?search_query={q_enc}&sp=CAI%253D"
    print(f"[{source['id']}] YouTube search (sort by date): '{query}' (limit={limit})")

    cmd = [
        "yt-dlp", *YT_DLP_FLAGS,
        "--flat-playlist",
        "--playlist-end", str(limit),
        "--print", "%(id)s\t%(title)s\t%(channel)s\t%(duration)s\t%(view_count)s\t%(upload_date)s",
        search_url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT")
        return []

    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-300:]}")
        return []

    cutoff = datetime.date.today() - datetime.timedelta(days=max_age_days)
    candidates = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip() or "\t" not in line:
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        vid_id, title, channel, duration_s, views_s, upload_s = (p.strip() for p in parts[:6])

        # parse duration
        try:
            duration = int(float(duration_s)) if duration_s and duration_s != "NA" else None
        except (ValueError, TypeError):
            duration = None

        # parse views
        try:
            views = int(views_s) if views_s and views_s != "NA" else 0
        except (ValueError, TypeError):
            views = 0

        # parse upload date YYYYMMDD
        upload_date = None
        if upload_s and len(upload_s) == 8 and upload_s.isdigit():
            try:
                upload_date = datetime.date(int(upload_s[:4]), int(upload_s[4:6]), int(upload_s[6:8]))
            except ValueError:
                pass

        # filters
        if upload_date and upload_date < cutoff:
            continue
        if views < min_views:
            continue

        candidates.append({
            "source_id": source["id"],
            "type": "youtube_search_result",
            "id": vid_id,
            "title": title,
            "channel": channel,
            "duration": duration,
            "views": views,
            "upload_date": upload_date.isoformat() if upload_date else "",
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "language": source.get("language", "en"),
        })

    print(f"  {len(candidates)} resultados tras filtros (>= {min_views} views, <= {max_age_days}d)")
    return candidates


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: discover_youtube_search.py <query>")
        sys.exit(1)
    items = discover_youtube_search({"id": "test", "query": " ".join(sys.argv[1:])})
    for it in items:
        print(f"  {it['upload_date']} | {it['views']:>7,} views | {it['channel'][:25]:<25} | {it['title'][:60]}")
