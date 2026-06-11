#!/usr/bin/env python3
"""
video_to_visual.py — Extract visual content (frames + OCR text) from videos.

For silent screencasts where audio transcription fails, this script:
  1. Downloads video (or uses local file)
  2. Detects scene changes via ffmpeg
  3. Extracts frames at scene boundaries + regular intervals
  4. Deduplicates very similar frames via perceptual hash
  5. Runs Tesseract OCR on each frame
  6. Produces markdown with embedded base64 frames + OCR text per frame

Usage:
    python3 video_to_visual.py "https://x.com/user/status/ID"
    python3 video_to_visual.py "video.mp4" --interval 3 --scene-threshold 0.2
    python3 video_to_visual.py --from-file urls.txt
"""

import argparse
import base64
import hashlib
import logging
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("visual")


# --- helpers ---------------------------------------------------------------

def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def is_url(s: str) -> bool:
    return s.startswith(("http://", "https://", "www."))


def sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def yt_dlp_download(url: str, outdir: Path) -> Path | None:
    cmd = [
        "yt-dlp",
        "-f", "best[height<=480]/best",
        "-o", str(outdir / "%(title)s.%(ext)s"),
        "--no-playlist",
        "--extractor-args", "youtube:player_client=android",
        url,
    ]
    r = run(cmd, timeout=600)
    if r.returncode != 0:
        log.warning("yt-dlp failed: %s", r.stderr[:300])
        return None
    files = sorted(outdir.iterdir(), key=lambda p: p.stat().st_mtime)
    vids = [f for f in files if f.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}]
    return vids[-1] if vids else None


def get_duration(video: Path) -> float:
    r = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(video),
    ])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def detect_scenes(video: Path, threshold: float) -> list[float]:
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "frame=pts_time",
        "-select_streams", "v:0", "-of", "csv=p=0",
        "-f", "lavfi", f"movie={shlex.quote(str(video))},select=gt(scene\\,{threshold})",
    ]
    r = run(cmd, timeout=300)
    ts = []
    for line in r.stdout.splitlines():
        try:
            ts.append(float(line.strip()))
        except ValueError:
            continue
    return ts


def extract_frame(video: Path, ts: float, out: Path) -> bool:
    r = run([
        "ffmpeg", "-y", "-ss", f"{ts:.3f}", "-i", str(video),
        "-vframes", "1", "-q:v", "2", str(out),
    ])
    return r.returncode == 0 and out.exists()


def phash_approx(img: Path) -> str:
    """Quick content hash: downsample via ffmpeg to 8x8 + hash. Good enough for dedup."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
        tpath = t.name
    try:
        run(["ffmpeg", "-y", "-i", str(img), "-vf", "scale=8:8,format=gray", tpath])
        if os.path.exists(tpath):
            return hashlib.md5(open(tpath, "rb").read()).hexdigest()
    finally:
        if os.path.exists(tpath):
            os.unlink(tpath)
    return ""


def ocr_frame(img: Path) -> str:
    r = run(["tesseract", str(img), "-", "--psm", "6", "-l", "eng"])
    text = (r.stdout or "").strip()
    # Collapse multi-blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def fmt_ts(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def b64_image(img: Path) -> str:
    return base64.b64encode(img.read_bytes()).decode()


# --- main pipeline ---------------------------------------------------------

def process_one(source: str, interval: float, threshold: float, max_frames: int, outdir: Path) -> Path | None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if is_url(source):
            log.info("Downloading %s", source)
            video = yt_dlp_download(source, tmp)
            if not video:
                log.warning("Download failed, skipping.")
                return None
        else:
            video = Path(source)
            if not video.exists():
                log.warning("Not found: %s", source)
                return None

        log.info("Video: %s (%.1f MB)", video.name, video.stat().st_size / 1024 / 1024)
        duration = get_duration(video)
        log.info("Duration: %.1fs", duration)

        # Collect candidate timestamps: scene changes + regular intervals
        scenes = detect_scenes(video, threshold)
        log.info("Scene changes: %d", len(scenes))
        interval_pts = [i for i in range(0, int(duration), int(interval)) if i > 0]
        candidates = sorted(set([round(t, 2) for t in scenes] + interval_pts))

        # Extract + dedup frames
        frames_dir = tmp / "frames"
        frames_dir.mkdir()
        picked = []  # [(ts, path)]
        seen_hashes = set()
        for ts in candidates:
            if len(picked) >= max_frames:
                break
            fp = frames_dir / f"f_{ts:07.2f}.jpg"
            if not extract_frame(video, ts, fp):
                continue
            h = phash_approx(fp)
            if h and h in seen_hashes:
                fp.unlink()
                continue
            seen_hashes.add(h)
            picked.append((ts, fp))
        log.info("Unique frames kept: %d", len(picked))

        # OCR each frame
        rows = []
        for ts, fp in picked:
            text = ocr_frame(fp)
            rows.append((ts, fp, text))

        # Compose markdown output
        title = video.stem
        out = outdir / f"{sanitize(title)}.visual.md"
        lines = [
            "---",
            f"title: {title!r}",
            f'source_video: "{video.name}"',
            f'generated: "{datetime.now().isoformat()}"',
            f"duration_s: {duration:.1f}",
            f"scene_threshold: {threshold}",
            f"frame_interval_s: {interval}",
            f"total_frames: {len(rows)}",
            f"ocr_engine: tesseract (eng)",
            "---",
            "",
            f"# {title}",
            "",
            f"*Visual extraction — {len(rows)} unique frames from a {duration:.0f}s silent screencast. No voice track.*",
            "",
        ]
        for ts, fp, text in rows:
            lines.append(f"## [{fmt_ts(ts)}]")
            lines.append("")
            lines.append(f"![frame at {fmt_ts(ts)}](data:image/jpeg;base64,{b64_image(fp)})")
            lines.append("")
            if text:
                lines.append("**OCR:**")
                lines.append("")
                lines.append("```")
                lines.append(text)
                lines.append("```")
            else:
                lines.append("*(no text detected)*")
            lines.append("")
        out.write_text("\n".join(lines), encoding="utf-8")
        log.info("Wrote: %s (%.1f MB)", out.name, out.stat().st_size / 1024 / 1024)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*", help="URLs or local video paths")
    ap.add_argument("--from-file", help="File with one URL per line")
    ap.add_argument("--interval", type=float, default=3.0, help="Seconds between sampled frames (default 3)")
    ap.add_argument("--scene-threshold", type=float, default=0.25, help="Scene change threshold (0-1)")
    ap.add_argument("--max-frames", type=int, default=40, help="Max frames per video (default 40)")
    ap.add_argument("--outdir", default=".", help="Output directory")
    args = ap.parse_args()

    sources = list(args.sources)
    if args.from_file:
        with open(args.from_file) as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    sources.append(ln)
    if not sources:
        ap.print_help()
        sys.exit(1)

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    for i, src in enumerate(sources, 1):
        log.info("=" * 60)
        log.info("[%d/%d] %s", i, len(sources), src[:70])
        try:
            out = process_one(src, args.interval, args.scene_threshold, args.max_frames, outdir)
            if out:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            log.error("Error: %s", e)
            fail += 1

    log.info("=" * 60)
    log.info("DONE: %d ok, %d failed", ok, fail)
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
