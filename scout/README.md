# Anthropic Orbit Scout

Daily content-discovery cron for transcribo.

## What it does

Crawls Anthropic + key-individuals surfaces, diffs against a manifest of
already-seen URLs, and appends only NEW URLs to two queue files:

- `urls_pending_anthropic.txt` — videos for `cli_pipeline.py`
- `articles_pending_anthropic.txt` — text articles for local article ingest

The script itself does NO transcription, NO ingest, NO downloads.
Discovery only. Processing is the operator's local job.

## Sources tracked

| Source | Type | Crawler |
|---|---|---|
| anthropic.com/news | text | HTML regex |
| anthropic.com/research | text | HTML regex |
| anthropic.com/engineering | text | HTML regex |
| claude.com/resources/tutorials | text | HTML regex |
| claude.com/resources/use-cases | text | HTML regex |
| youtube.com/@anthropic-ai | video | yt-dlp + HTML fallback |
| youtube.com/@AndrejKarpathy | video | yt-dlp + HTML fallback |
| youtube.com/@JEVanClief | video | yt-dlp + HTML fallback |
| karpathy.github.io/feed.xml | text | RSS (Atom) |

X (Twitter) timelines for @bcherny and @karpathy are NOT in scope here —
they require Chrome MCP which isn't available in the remote CCR env.
Handled by a separate local launchd job.

## Files

```
scout/
  anthropic_orbit_scout.py   # the crawler (stdlib only, no deps)
  README.md                  # this file
manifests/
  anthropic_manifest.json    # seen-URL set, per source
urls_pending_anthropic.txt   # video queue
articles_pending_anthropic.txt  # article queue
```

## Run locally

```bash
python3 scout/anthropic_orbit_scout.py
echo "exit code: $?"   # 0 = no new, 2 = new items, 1 = error
```

## Run as cron (remote routine)

A claude.ai routine triggers this script daily at 06:00 UTC (08:00 Madrid CEST).
The routine prompt runs the script, and if it exits 2, opens a PR to main with
the manifest + queue updates.
