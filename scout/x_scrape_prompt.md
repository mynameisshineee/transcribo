# X Timeline Scrape — daily

Scrape new content from key X accounts via the Chrome MCP server.

## Accounts to scrape (priority order)

1. **@bcherny** — Boris Cherny, Anthropic. PRIORITY #1.
2. **@karpathy** — Andrej Karpathy, Anthropic.

## Steps

For each account, in order:

1. Navigate Chrome to `https://x.com/<handle>` (skip if already on timeline).
2. Use the search filter: `from:<handle> since:<yesterday-YYYY-MM-DD>` to bound to last 24h only.
3. Read each tweet/thread in order. Classify each as:
   - **Signal** — substantive (engineering insight, product update, opinion that matters).
   - **Noise** — likes/RTs/banter without standalone value.
4. For SIGNAL tweets only, emit one `.knowledge.md` file at the repo root using this naming:
   - `x_<handle>_<YYYY-MM-DD>_<short-slug>.knowledge.md`
   - Body shape mirrors transcript files: YAML frontmatter + `# title` + `## Full Content`.
   - Frontmatter must include: `source_url`, `source_type: x_thread`, `author: "@<handle>"`, `fetched: <UTC>`.
5. After writing locally, copy to the kDrive source dir:
   `/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/Administración/Colaboraciones, financiación, compras/Formaciones/0. Conocimiento Albert/`
6. Print a one-line summary per account: `<handle>: N signals saved, M noise skipped`.

## Hard rules

- NEVER write Noise — if in doubt, skip.
- NEVER follow links into other accounts. One account per pass.
- NEVER click reply/like — read-only.
- If Chrome MCP is unavailable, exit 1 with a clear message; do not retry.
- Per the operator's memory `feedback_boris_cherny_priority`, Boris Cherny is priority #1 — flag any contradiction with the existing wiki in his favor.
- Per memory `feedback_no_anchor_see_links`, do NOT use `[see:]` links with `§` or `#anchor` — they break check_links.sh.

## After scraping

Run the wiki ingest manually using the Karpathy workflow documented in
`/Users/shine/wiki-conocimiento/CLAUDE.md` (classify category, append to
sources.yaml, update target wiki page, bump index.md, append log.md,
schema.md updates if new entities, run tools/check_links.sh).
