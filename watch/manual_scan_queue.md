# 🔍 Manual Scan Queue — X & otras fuentes que necesitan sesión humana

> El watch agent NO puede scrapear X en cron (rate limit + login + bot challenges).
> Cuando puedas, pídele a Claude: *"Scan estas entradas del manual queue"*
> Claude usará Chrome MCP para revisar @bcherny, @karpathy, etc.
>
> **Scope (importante):** esta sesión (transcribo) solo cubre **vídeo transcribible** (X-native video
> → yt-dlp → kDrive). El **texto** (hilos de Boris/Karpathy) es alto valor pero NO transcribible y
> es lane del **agente-wiki** (lectura + ingest), no de aquí.

---

## ✅ Escaneo 2026-06-23 (vídeo, Chrome MCP) — resultado: 0 transcribable

Búsqueda `from:CUENTA filter:videos since:2026-05-11` (40 días) en las 3 cuentas prioritarias:

| Cuenta | Tweets-vídeo | Nota |
|---|---|---|
| `claudeai_x` (@AnthropicAI) | 1 | "Claude's Constitution audiobook" — **45s promo**, sin valor transcribible → skip |
| `bcherny_x` (@bcherny) | **0** | "no hay resultados" — Boris postea texto, no vídeo |
| `karpathy_x` (@karpathy) | **0** | "no hay resultados" — ídem |

**Conclusión:** el backfill de X-vídeo está vacío de contenido transcribible. Ver memoria
`reference-x-video-backfill-empty`. El valor real de estas cuentas (hilos de texto) → agente-wiki.

---

- [x] **escaneado 2026-06-23** · `claudeai_x` · @AnthropicAI → 1 vídeo (45s promo, skip)
- [x] **escaneado 2026-06-23** · `bcherny_x` · @bcherny → 0 vídeos
- [x] **escaneado 2026-06-23** · `bcherny_x_search` · from:bcherny → cubierto por @bcherny (0)
- [x] **escaneado 2026-06-23** · `karpathy_x` · @karpathy → 0 vídeos
- [x] **escaneado 2026-06-23** · `karpathy_x_search` · from:karpathy → cubierto por @karpathy (0)

> Re-escanear solo si el operador quiere texto-para-wiki (lane agente-wiki) o si una cuenta
> empieza a postear vídeo nativo con frecuencia.
