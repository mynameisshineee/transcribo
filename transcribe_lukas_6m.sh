#!/usr/bin/env bash
# Backfill 6m @lukas-margerie — 2026-06-04
# Para cada URL: download (cookies) → cli_pipeline → cp a kDrive
set -u
cd /Users/shine/videoatexto
source venv/bin/activate
KDRIVE="/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/Administración/Colaboraciones, financiación, compras/Formaciones/0. Conocimiento Albert"
LOG="lukas_6m_$(date +%Y%m%d_%H%M).log"
ok=0; fail=0; total=$(wc -l < urls_lukas_6m.txt | tr -d ' ')
i=0
while read -r url; do
  i=$((i+1))
  id=$(echo "$url" | sed 's|.*v=||')
  echo "[$i/$total] $id" | tee -a "$LOG"
  # Skip if knowledge.md already in kDrive (defense-in-depth re-check)
  if ls "$KDRIVE/" 2>/dev/null | grep -q "^${id}_"; then
    echo "  SKIP ya en kDrive" | tee -a "$LOG"; continue
  fi
  # Download with cookies
  yt-dlp --cookies-from-browser chrome -x --audio-format m4a \
    -o "%(id)s_%(title).100B.%(ext)s" "$url" >> "$LOG" 2>&1
  m4a=$(ls ${id}_*.m4a 2>/dev/null | head -1)
  if [ -z "$m4a" ]; then
    echo "  FAIL no audio" | tee -a "$LOG"; fail=$((fail+1)); continue
  fi
  # Transcribe (mlx-whisper small for 10-min clips)
  python3 cli_pipeline.py "$m4a" -l en -m small >> "$LOG" 2>&1
  km="${m4a%.m4a}.knowledge.md"
  if [ ! -f "$km" ]; then
    echo "  FAIL no knowledge.md" | tee -a "$LOG"; fail=$((fail+1)); continue
  fi
  # Copy to kDrive
  cp "$km" "$KDRIVE/" && echo "  ✓ kDrive" | tee -a "$LOG" && ok=$((ok+1))
done < urls_lukas_6m.txt
echo "" | tee -a "$LOG"
echo "============================================================" | tee -a "$LOG"
echo "DONE: $ok OK / $fail FAIL / $total total" | tee -a "$LOG"
