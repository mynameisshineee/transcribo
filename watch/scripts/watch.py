#!/usr/bin/env python3
"""
watch.py — BiK Wiki Watch Agent

Discovery + download + transcripción automática para fuentes configuradas en sources.yaml.
La INGESTA al wiki queda manual (Claude interactivo) — este script SOLO baja material y
deja entradas pendientes en backlog.md para revisión humana.

Uso:
    python3 watch.py             # corre todas las fuentes con frequency != manual según día
    python3 watch.py --force-all # ignora frequency, escanea todo
    python3 watch.py --source claude_anthropic_youtube  # solo una fuente
    python3 watch.py --discover-only  # listar nuevos sin bajar/transcribir
    python3 watch.py --dry-run   # listar acciones sin ejecutarlas

Diseñado para correr con launchctl macOS diariamente a las 07:00.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# Make sibling discoverers importable
sys.path.insert(0, str(SCRIPTS_DIR))
from discover_github import discover_github_user, discover_github_repo  # noqa: E402
from discover_youtube_search import discover_youtube_search  # noqa: E402
from discover_web_rss import discover_web_blog  # noqa: E402

SOURCES_PATH = ROOT / "sources.yaml"
STATE_PATH = ROOT / "state.yaml"
BACKLOG_PATH = ROOT / "backlog.md"
MANUAL_QUEUE_PATH = ROOT / "manual_scan_queue.md"
LOGS_DIR = ROOT / "logs"

YT_DLP_FLAGS = [
    "--cookies-from-browser", "chrome",
    "--remote-components", "ejs:github",
]


def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    daily_log = LOGS_DIR / f"watch-{datetime.date.today().isoformat()}.log"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with daily_log.open("a") as fp:
        fp.write(line + "\n")


def load_sources() -> dict:
    with SOURCES_PATH.open() as fp:
        return yaml.safe_load(fp)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"state": {}}
    with STATE_PATH.open() as fp:
        return yaml.safe_load(fp) or {"state": {}}


def save_state(state: dict) -> None:
    with STATE_PATH.open("w") as fp:
        yaml.safe_dump(state, fp, default_flow_style=False, sort_keys=False)


def known_titles_from_wiki() -> set[str]:
    """Devuelve los basenames normalizados de todos los .knowledge.md existentes
    para evitar reprocesar lo que ya está bajado.

    Reúne tres fuentes:
    - Filenames de *.knowledge.md y *.m4a en PROJECT_ROOT
    - IDs explícitos en backlog.md (líneas con `youtube ID` o URL youtube)
    - Normalización tanto del nombre original como sin caracteres especiales
    """
    known = set()
    for f in PROJECT_ROOT.glob("*.knowledge.md"):
        # quitar sufijo .knowledge.md
        name = f.stem.replace(".knowledge", "")
        known.add(name.lower())
        # versión normalizada sin caracteres especiales para fuzzy match
        norm = re.sub(r"[^\w\s]", "", name).lower().strip()
        norm_compact = re.sub(r"\s+", "_", norm)
        known.add(norm)
        known.add(norm_compact)
    # también incluye IDs y filenames de m4a
    for f in PROJECT_ROOT.glob("*.m4a"):
        known.add(f.stem.lower())
        norm = re.sub(r"[^\w\s]", "", f.stem).lower().strip()
        known.add(norm)
        known.add(re.sub(r"\s+", "_", norm))
    # cosechar IDs de YouTube y de X explícitos en backlog.md
    if BACKLOG_PATH.exists():
        text = BACKLOG_PATH.read_text()
        # IDs estilo YouTube `xxxxxxxxxxx` (11 chars) entre comillas o backticks
        for m in re.finditer(r"[`']([A-Za-z0-9_-]{11})[`']", text):
            known.add(m.group(1).lower())
        # URLs youtube.com/watch?v=ID
        for m in re.finditer(r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})", text):
            known.add(m.group(1).lower())
        # status IDs de X
        for m in re.finditer(r"status[ /](\d{15,20})", text):
            known.add(m.group(1).lower())
    return known


def should_run(source: dict, today: datetime.date) -> bool:
    freq = source.get("frequency", "manual")
    if freq == "manual":
        return False
    if freq == "daily":
        return True
    if freq == "weekly":
        # corre los lunes
        return today.weekday() == 0
    return False


def discover_youtube_channel(source: dict, limit: int, known: set[str]) -> list[dict]:
    """Usa yt-dlp para enumerar vídeos del canal.

    Si la fuente declara `backfill_since: YYYY-MM-DD`, usa modo full-metadata
    (más lento, sin --flat-playlist) con --dateafter para captar todo el rango.
    En modo normal, usa --flat-playlist (rápido, sin upload_date confiable).

    Devuelve sólo los que no están en `known`.
    """
    url = source["url"]
    backfill = source.get("backfill_since")  # "YYYY-MM-DD" o None

    log(f"[{source['id']}] descubriendo {url} (limit={limit}{', backfill since '+backfill if backfill else ''})")
    cmd = [
        "yt-dlp", *YT_DLP_FLAGS,
        "--flat-playlist",
        "--print", "%(id)s\t%(title)s\t%(duration)s\t%(upload_date)s",
        "--playlist-end", str(limit),
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        log(f"[{source['id']}] TIMEOUT en discovery", level="ERROR")
        return []
    if result.returncode != 0:
        log(f"[{source['id']}] yt-dlp error: {result.stderr[-500:]}", level="ERROR")
        return []
    # `backfill_since` se aplica en download_and_transcribe via --dateafter

    new = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip() or "\t" not in line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        vid_id = parts[0].strip()
        title = parts[1].strip() if len(parts) > 1 else ""
        duration_s = parts[2].strip() if len(parts) > 2 else ""
        upload_date = parts[3].strip() if len(parts) > 3 else ""
        try:
            duration = int(float(duration_s)) if duration_s and duration_s != "NA" else None
        except (ValueError, TypeError):
            duration = None

        # filtros — solo coincidencia exacta de ID o de título normalizado
        if vid_id.lower() in known:
            continue
        title_norm = re.sub(r"[^\w\s]", "", title).lower().strip()
        title_norm_compact = re.sub(r"\s+", "_", title_norm)
        if title_norm and (title_norm in known or title_norm_compact in known):
            continue

        new.append({
            "id": vid_id,
            "title": title,
            "duration": duration,
            "upload_date": upload_date,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "source_id": source["id"],
            "source_handle": source.get("handle", ""),
            "language": source.get("language", "en"),
            "backfill_since": backfill,  # propagar al download
        })
    log(f"[{source['id']}] {len(new)} candidatos nuevos")
    return new


def filter_by_duration(items: list[dict], min_s: int, max_s: int) -> list[dict]:
    out = []
    for it in items:
        d = it.get("duration")
        if d is None:
            out.append(it)  # sin info de duración, lo dejamos pasar (se evaluará al bajar)
            continue
        if d < min_s:
            log(f"  skip (corto {d}s): {it['title'][:60]}")
            continue
        if d > max_s:
            log(f"  skip (largo {d}s): {it['title'][:60]}")
            continue
        out.append(it)
    return out


def sanitize_filename(s: str) -> str:
    s = re.sub(r"[/\\:*?\"<>|]", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s[:120]


def download_and_transcribe(item: dict, output_dir: Path, whisper_model: str, dry_run: bool) -> Path | None:
    """Baja el audio y lo transcribe. Devuelve el path al .knowledge.md."""
    safe_title = sanitize_filename(item["title"])
    audio_basename = f"{item['id']}_{safe_title}"
    audio_tmpl = output_dir / f"{audio_basename}.%(ext)s"
    knowledge_path = output_dir / f"{audio_basename}.knowledge.md"

    if knowledge_path.exists():
        log(f"  YA EXISTE knowledge: {knowledge_path.name}")
        return knowledge_path

    if dry_run:
        log(f"  [DRY-RUN] bajaría + transcribiría: {item['url']} -> {knowledge_path.name}")
        return None

    # download
    log(f"  bajando audio: {item['url']}")
    cmd = [
        "yt-dlp", *YT_DLP_FLAGS,
        # Audio nativo SIN re-encode: ffmpeg 8.0 rompe el encode a AAC/m4a
        # ("audio conversion failed" / m4a corrupto). mlx-whisper decodifica
        # webm/opus directamente vía ffmpeg, así que no hace falta convertir.
        "-f", "bestaudio/best",
        "-o", str(audio_tmpl),
    ]
    # Filtro por fecha si la fuente declara backfill_since (YYYY-MM-DD)
    backfill = item.get("backfill_since")
    if backfill:
        cmd += ["--dateafter", backfill.replace("-", "")]
    cmd.append(item["url"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT bajando {item['url']}", level="ERROR")
        return None
    if result.returncode != 0:
        log(f"  ERROR bajando: {result.stderr[-500:]}", level="ERROR")
        return None
    # Resolver el fichero de audio real (extensión nativa: webm/opus/m4a…)
    audio_path = next(
        (p for p in sorted(output_dir.iterdir())
         if p.name.startswith(audio_basename + ".")
         and not p.name.endswith(".knowledge.md")),
        None,
    )
    if audio_path is None:
        log(f"  audio no encontrado tras download: {audio_basename}.*", level="ERROR")
        return None

    log(f"  audio OK ({audio_path.stat().st_size // 1024} KB), transcribiendo...")

    # transcribe (usa el script de transcripción del proyecto)
    transcribe_script = PROJECT_ROOT / "video_to_knowledge_base_mlx.py"
    cmd = [
        sys.executable, str(transcribe_script),
        str(audio_path),
        "-m", whisper_model,
        "-l", item.get("language", "en"),
    ]
    # cambiar cwd al PROJECT_ROOT para que escriba ahí
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=PROJECT_ROOT)
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT transcribiendo", level="ERROR")
        return None
    if result.returncode != 0:
        log(f"  ERROR transcribiendo: {result.stderr[-500:]}", level="ERROR")
        return None

    if knowledge_path.exists():
        log(f"  knowledge OK: {knowledge_path.name}")
        # limpiar el audio fuente: la transcripción ya está a salvo (root + canonical).
        # Evita que el .webm/.m4a se acumule en output_dir en cada run.
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            pass
        return knowledge_path
    log(f"  knowledge no encontrado tras transcripción", level="WARN")
    return None


def copy_to_canonical(knowledge_path: Path, canonical_dir: Path, dry_run: bool) -> None:
    """Copia el .knowledge.md al source dir inmutable que cita el wiki."""
    dst = canonical_dir / knowledge_path.name
    if dst.exists():
        log(f"  YA EXISTE en canonical: {dst.name}")
        return
    if dry_run:
        log(f"  [DRY-RUN] copiaría a canonical: {dst}")
        return
    import shutil
    shutil.copy2(knowledge_path, dst)
    log(f"  copiado a canonical: {dst.name}")


def append_to_backlog(item: dict, knowledge_path: Path) -> None:
    """Añade una entrada al backlog.md para revisión humana posterior."""
    today = datetime.datetime.now().isoformat(timespec="minutes")
    duration_h = ""
    if item.get("duration"):
        m = item["duration"] // 60
        s = item["duration"] % 60
        duration_h = f"{m}:{s:02d}"
    upload = item.get("upload_date", "")
    if upload and len(upload) == 8:
        upload = f"{upload[:4]}-{upload[4:6]}-{upload[6:8]}"
    # source_handle puede no existir si viene de youtube_search; usa channel o source_id como fallback
    handle = item.get("source_handle") or item.get("channel") or item.get("source_id", "?")
    entry = f"""
## {today} — auto-descubierto · {handle}

### `{knowledge_path.stem}`
- **Source**: {item.get('source_id', '?')} · `{item['id']}` · {duration_h or '?:??'} · upload {upload or '?'}
- **URL**: {item['url']}
- **Pista**: [PENDIENTE leer transcripción y resumir]
- **Sugerencia ingest**: [PENDIENTE clasificar al wiki]
- **Estado**: `.knowledge.md` en `{knowledge_path.parent.name}/` + canonical kDrive
"""
    with BACKLOG_PATH.open("a") as fp:
        fp.write(entry)
    log(f"  añadido al backlog: {knowledge_path.stem}")


def append_manual_scan_entry(source: dict) -> None:
    """Para fuentes x_account/x_search: deja una entrada en manual_scan_queue.md
    para que el operador lo revise con Claude + Chrome MCP cuando pueda.
    """
    today = datetime.datetime.now().isoformat(timespec="minutes")
    handle = source.get("handle", "")
    query = source.get("query", "")
    url = source.get("url", "")
    descriptor = handle or query
    entry = f"""
- [ ] **{today}** · `{source['id']}` · {source.get('type')} · {descriptor}
    - URL: {url}
    - Notas: {source.get('notes', '')}
"""
    MANUAL_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not MANUAL_QUEUE_PATH.exists():
        MANUAL_QUEUE_PATH.write_text(
            "# 🔍 Manual Scan Queue — X & otras fuentes que necesitan sesión humana\n\n"
            "> El watch agent NO puede scrapear X en cron (rate limit + login + bot challenges).\n"
            "> Cuando puedas, pídele a Claude: *\"Scan estas entradas del manual queue\"*\n"
            "> Claude usará Chrome MCP para revisar @bcherny, @karpathy, etc., extraer lo relevante\n"
            "> y dejar los hallazgos en `backlog.md` para ingest posterior.\n\n"
            "---\n"
        )
    with MANUAL_QUEUE_PATH.open("a") as fp:
        fp.write(entry)
    log(f"  [{source['id']}] añadido a manual_scan_queue.md")


def append_web_article_to_backlog(post: dict, source: dict) -> None:
    """Posts de blog (sin transcripción) — sólo metadata + URL para revisión humana.
    El operador (o Claude interactivo) decidirá si vale la pena scrapear cada
    post + ingestarlo al wiki.
    """
    today = datetime.datetime.now().isoformat(timespec="minutes")
    handle = source.get("handle") or source["id"]
    entry = f"""
## {today} — auto-descubierto · web · {handle}

### {post['slug']}
- **Source**: web `{source['id']}` · index `{source.get('url', '')}`
- **URL**: {post['url']}
- **Tipo**: web_article (sin transcripción — scrape on-demand)
- **Pista**: [PENDIENTE leer el post y resumir]
- **Sugerencia ingest**: [PENDIENTE clasificar al wiki]
"""
    with BACKLOG_PATH.open("a") as fp:
        fp.write(entry)
    log(f"  web post añadido al backlog: {post['slug']}")


def append_github_event_to_backlog(event: dict, source: dict) -> None:
    """Eventos GitHub no se descargan/transcriben — se anotan en backlog
    con link directo. Útil para 'Boris pushed a release v2.0'.
    """
    today = datetime.datetime.now().isoformat(timespec="minutes")
    updated_short = event.get("updated", "")[:10]
    entry = f"""
## {today} — auto-descubierto · github · {source.get('handle', source.get('url', ''))}

### {event.get('title', 'untitled')[:120]}
- **Source**: github `{source['id']}` · {updated_short}
- **URL**: {event.get('link', '')}
- **Tipo**: {event.get('type', 'unknown')}
- **Autor**: {event.get('author', '')}
- **Excerpt**: {(event.get('excerpt') or '').strip()[:200]}
- **Pista**: [PENDIENTE leer y resumir]
- **Sugerencia ingest**: [PENDIENTE — sólo si la actividad es de fondo/insight notable]
"""
    with BACKLOG_PATH.open("a") as fp:
        fp.write(entry)
    log(f"  github event añadido al backlog: {event.get('title', '')[:60]}")


def run(args: argparse.Namespace) -> int:
    sources_data = load_sources()
    state = load_state()
    config = sources_data.get("config", {})
    today = datetime.date.today()

    output_dir = Path(config.get("output_dir", PROJECT_ROOT))
    canonical_dir = Path(config.get("canonical_source_dir", ""))
    yt_limit = int(config.get("youtube_scan_limit", 30))
    yt_search_limit = int(config.get("youtube_search_limit", 15))
    gh_limit = int(config.get("github_activity_limit", 30))
    min_dur = int(config.get("min_duration_seconds", 180))
    max_dur = int(config.get("max_duration_seconds", 18000))
    min_views = int(config.get("min_views_for_mention", 500))
    max_age_days = int(config.get("max_age_days", 30))
    whisper_model = config.get("whisper_model", "medium")

    known = known_titles_from_wiki()
    log(f"known set: {len(known)} entradas")

    selected_sources = []
    for src in sources_data.get("sources", []):
        if args.source and src["id"] != args.source:
            continue
        if not args.source and not args.force_all and not should_run(src, today):
            log(f"[{src['id']}] skip (frequency={src['frequency']} hoy={today.strftime('%a')})")
            continue
        selected_sources.append(src)

    log(f"sources seleccionadas: {len(selected_sources)}")

    new_total = 0
    for src in selected_sources:
        stype = src.get("type", "")
        try:
            if stype == "youtube_channel":
                discovered = discover_youtube_channel(src, yt_limit, known)
                discovered = filter_by_duration(discovered, min_dur, max_dur)
                if args.discover_only:
                    for it in discovered:
                        log(f"  NEW: {it['title']} ({it['duration']}s) {it['url']}")
                else:
                    for it in discovered:
                        kp = download_and_transcribe(it, output_dir, whisper_model, args.dry_run)
                        if kp and not args.dry_run:
                            if canonical_dir.exists():
                                copy_to_canonical(kp, canonical_dir, args.dry_run)
                            append_to_backlog(it, kp)
                            known.add(it["id"].lower())
                            new_total += 1

            elif stype == "youtube_search":
                candidates = discover_youtube_search(src, yt_search_limit, min_views, max_age_days)
                # filtrar contra known set + duración
                fresh = []
                for c in candidates:
                    if c["id"].lower() in known:
                        continue
                    title_norm = re.sub(r"[^\w\s]", "", c["title"]).lower().strip()
                    if title_norm in known:
                        continue
                    fresh.append(c)
                fresh = filter_by_duration(fresh, min_dur, max_dur)
                if args.discover_only:
                    for it in fresh:
                        log(f"  SEARCH NEW: [{it['views']:,}v] {it['title']} {it['url']}")
                else:
                    for it in fresh:
                        kp = download_and_transcribe(it, output_dir, whisper_model, args.dry_run)
                        if kp and not args.dry_run:
                            if canonical_dir.exists():
                                copy_to_canonical(kp, canonical_dir, args.dry_run)
                            append_to_backlog(it, kp)
                            known.add(it["id"].lower())
                            new_total += 1

            elif stype == "github_user":
                events = discover_github_user(src, since_days=7)
                if args.discover_only:
                    for ev in events[:gh_limit]:
                        log(f"  GH EVT: {ev['updated'][:10]} | {ev['title'][:80]}")
                else:
                    for ev in events[:gh_limit]:
                        # dedup: usa el id del atom como marker
                        marker = ev.get("id", "") or ev.get("link", "")
                        if marker and marker in known:
                            continue
                        if not args.dry_run:
                            append_github_event_to_backlog(ev, src)
                            known.add(marker)
                            new_total += 1

            elif stype == "github_repo_activity":
                events = discover_github_repo(src, since_days=7)
                if args.discover_only:
                    for ev in events[:gh_limit]:
                        log(f"  REPO EVT: {ev['updated'][:10]} | {ev['title'][:80]}")
                else:
                    for ev in events[:gh_limit]:
                        marker = ev.get("id", "") or ev.get("link", "")
                        if marker and marker in known:
                            continue
                        if not args.dry_run:
                            append_github_event_to_backlog(ev, src)
                            known.add(marker)
                            new_total += 1

            elif stype in ("x_account", "x_search"):
                if args.discover_only or args.dry_run:
                    log(f"  X (manual): {src.get('url') or src.get('query')}")
                else:
                    append_manual_scan_entry(src)

            elif stype == "web_rss":
                # plane.so / anthropic.com no exponen RSS real — scrapeamos
                # el índice HTML y dedup contra URLs ya anotadas en backlog.md.
                backlog_text = BACKLOG_PATH.read_text() if BACKLOG_PATH.exists() else ""
                web_limit = int(src.get("scan_limit", 30))
                posts = discover_web_blog(src, backlog_text=backlog_text, limit=web_limit)
                log(f"  [{src['id']}] {len(posts)} posts nuevos en {src.get('url','?')}")
                for post in posts:
                    log(f"  POST: {post['url']}")
                    if not args.discover_only and not args.dry_run:
                        append_web_article_to_backlog(post, src)
                        new_total += 1

            else:
                log(f"  [{src['id']}] tipo desconocido '{stype}' — SKIP")
                continue

        except Exception as e:
            log(f"[{src['id']}] EXCEPCIÓN: {e}", level="ERROR")
            continue

        # update state
        state.setdefault("state", {})[src["id"]] = {
            "last_run": datetime.datetime.now().isoformat(timespec="seconds"),
        }

    save_state(state)
    log(f"DONE total nuevos procesados: {new_total}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Watch Agent BiK")
    p.add_argument("--force-all", action="store_true", help="ignorar frequency, escanear todo")
    p.add_argument("--source", help="solo una fuente por id")
    p.add_argument("--discover-only", action="store_true", help="solo listar nuevos sin bajar/transcribir")
    p.add_argument("--dry-run", action="store_true", help="no ejecutar acciones, solo loggear")
    args = p.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
