# CLAUDE.md — Transcribo

## Mission

**Transcribo is the ingest front-end of a Karpathy-style LLM-maintained knowledge wiki.**

When the user drops a YouTube URL (or a whole channel), the expected end-to-end is:

```
URL  →  yt-dlp download
     →  MLX Whisper transcription
     →  {title}.knowledge.md in this folder (local working copy)
     →  copy to kDrive source dir (the immutable raw layer the wiki cites)
     →  ingest into /Users/shine/wiki-conocimiento/ (the Karpathy wiki)
```

Raw `.knowledge.md` files are kept in **two places**:
- `./` (transcribo root) — the working copy emitted by the pipeline.
- `/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/Administración/Colaboraciones, financiación, compras/Formaciones/0. Conocimiento Albert/`
  — the **canonical source directory** that `wiki-conocimiento/schema.md` points
  at. Every new `.knowledge.md` must be copied here so the wiki citations
  (`[source: filename.knowledge.md]`) resolve. Files here are **immutable**.

The wiki at `../wiki-conocimiento/` is the curated, cross-linked layer that the
LLM maintains.

Reference methodology: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## End-to-End Workflow (the default when given a URL)

1. **Transcribe.** Run `cli_pipeline.py` with `-l en` (or appropriate language).
   It downloads with yt-dlp, transcribes with MLX Whisper, and writes
   `{title}.knowledge.md` in the transcribo root. The pipeline auto-skips titles
   already processed (see `_output_exists_by_title` in `cli_pipeline.py`).

2. **Copy to the canonical source dir** so `[source:]` citations resolve:
   ```bash
   cp "{title}.knowledge.md" \
     "/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/Administración/Colaboraciones, financiación, compras/Formaciones/0. Conocimiento Albert/"
   ```
   Do this for every file produced in step 1 before touching the wiki.

3. **Ingest into the wiki.** For each new `.knowledge.md`, follow the Karpathy
   ingest workflow documented in `/Users/shine/wiki-conocimiento/CLAUDE.md`:
   - Classify into one of the existing categories in `wiki/` (or create one).
   - Append a `processed:` entry to `sources.yaml` with id, file, category, date.
   - Update or create the target `wiki/{category}/{page}.md` — integrate new
     claims with `[source: {filename}.knowledge.md]` citations and add
     `[see: other/page.md]` cross-references. Flag contradictions with older
     sources rather than overwriting.
   - Update `index.md` (bump counts, add new entities/tools/concepts).
   - Update `schema.md` entity index if new people/tools/concepts appear.
   - Append a dated entry to `log.md` with sources_added, pages_updated,
     new_entities, categories_touched.
   - Run `tools/check_links.sh` (fast) or `tools/lint_wiki.sh` (full) to verify
     no orphans or broken `[see:]` links were introduced.

4. **Report.** Summarize to the user: what was transcribed, what wiki pages
   were touched, any new entities, any contradictions flagged.

## Destination Defaults

- **Wiki** — `/Users/shine/wiki-conocimiento/` (Karpathy layout: `schema.md` +
  `index.md` + `log.md` + `wiki/{category}/*.md` + `sources.yaml`).
  Other wikis in `~` (wiki-kombo, wiki-nuclio, wiki-vault) are unrelated unless
  the user explicitly says otherwise.
- **Raw `.knowledge.md`** — stays in transcribo root. `config.yaml` sets
  `knowledge_base_destination: null` so nothing is auto-moved.
- **Language** — default to the one the user specifies. If batching a full
  channel and the user doesn't say, infer from video titles.

## Batch Ingestion from a Channel

To process a whole channel (user asks e.g. "baja los 30 del canal X"):

```bash
# 1. List videos from channel
source venv/bin/activate
yt-dlp --flat-playlist --print "%(id)s|%(title)s" --playlist-end 30 \
  "https://www.youtube.com/@CHANNEL/videos"

# 2. Save URLs to file (one per line)
# 3. Run batch
python3 cli_pipeline.py --from-file urls_{channel}.txt -l en

# 4. After all transcriptions complete, do a single bulk ingest pass into
#    wiki-conocimiento rather than ingesting one at a time.
```

`cli_pipeline.py` skips already-processed titles automatically. Premieres and
unavailable videos will fail; they're safe to retry later.

## Key Commands

```bash
source venv/bin/activate

# Unified pipeline (download + transcribe) — the default entry point
python3 cli_pipeline.py "https://youtube.com/watch?v=xxx" -l en

# Multiple URLs
python3 cli_pipeline.py "URL1" "URL2" "URL3" -l en

# From file
python3 cli_pipeline.py --from-file urls.txt -l en

# Local file only (skip download)
python3 cli_pipeline.py "video.mp4" -l en

# Raw scripts (usually cli_pipeline.py is what you want)
python3 simple_audio_to_text.py "file.mp4" -m base -l es
python3 video_to_knowledge_base_mlx.py "video.mp4" -m medium -l en  # Apple Silicon
python3 video_to_knowledge_base.py "video.mp4" -m medium -l en      # cross-platform

# Batch processing a folder of local files
python3 process_all_videos_parallel.py /path/to/videos

# Diagnostics
python3 setup_m4_optimization.py
```

## Architecture

- `core/` — shared modules (config, device detection, model cache, quality
  validation, importance assessment)
- `config.yaml` — centralized configuration
- `cli_pipeline.py` — main unified pipeline (URL → knowledge.md)
- `video_to_knowledge_base_mlx.py` — MLX-optimized generator (Apple Silicon)
- `video_to_knowledge_base.py` — cross-platform generator
- `simple_audio_to_text.py` — minimal transcription script

## Device / Models

Auto-detects MPS (Apple Silicon) > CUDA > CPU (`core/device.py`).
Default model: `medium`. Use `large-v3` for important content, `small`/`base`
for quick jobs. Importance is auto-scored from duration / filename / folder
(see `importance` block in `config.yaml`).

## Dependencies

All in `requirements.txt`. FFmpeg required externally. Optional:
`mlx-whisper` (Apple Silicon), `yt-dlp` (YouTube).

## Wiki Schema Quick Reference

The wiki at `/Users/shine/wiki-conocimiento/` has these categories (see its
`schema.md` for keyword lookup):

| Category | Folder |
|---|---|
| Claude Code | `claude-code` |
| Frontend & UI Design | `frontend-ui-design` |
| AI Coding Tools | `ai-coding-tools` |
| AI Agents & Strategy | `ai-agents-strategy` |
| Backend & Architecture | `backend-architecture` |
| Graph Databases & RAG | `graph-databases-rag` |
| Next.js & React | `nextjs-react` |
| SaaS & Startup Building | `saas-startup-building` |
| Sales & Marketing | `sales-marketing` |
| Business & Finance | `business-finance` |
| DevOps & Cloud | `devops-cloud` |
| Productivity Tools | `productivity-tools` |

Citation format in wiki pages: `[source: {filename}.knowledge.md]`.
Cross-references: `[see: category/page.md]`.

## Non-negotiables

- Raw `.knowledge.md` files are **immutable** once generated. Never edit them
  during ingest; edit only the wiki pages that cite them.
- Every wiki page change introduced by ingest must carry `[source:]` citations.
- Contradictions with prior sources get flagged in the wiki page, not silently
  overwritten.
- `index.md` + `log.md` must be updated in the same pass as any wiki page edit.
