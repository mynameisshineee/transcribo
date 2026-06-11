#!/bin/bash
# Espera a que el pipeline de Tokyo termine y copia CUALQUIER .knowledge.md nuevo a kDrive (sin nombre hardcodeado).
KD="/Users/shine/kDrive/Dropbox/Ministry of Innovation/1 BiK/Administración/Colaboraciones, financiación, compras/Formaciones/0. Conocimiento Albert"
while pgrep -f "GiqyYQdYoIY" >/dev/null; do sleep 300; done
sleep 10
N=0
find /Users/shine/videoatexto -maxdepth 1 -name "*.knowledge.md" -newer /tmp/tokyo_ref_marker | while IFS= read -r f; do
  base=$(basename "$f")
  [ -f "$KD/$base" ] || { cp "$f" "$KD/" && echo "copiado: $base"; }
done
echo "tokyo copier FIN $(date '+%H:%M')"
