# 👁️ Wiki Watch Agent — BiK

> Discovery + descarga + transcripción automática de fuentes priorizadas.
> La **ingesta al wiki es manual** (Claude interactivo) — el watch SOLO te trae el material.

## Arquitectura (TL;DR)

```
┌──────────────────────┐
│  launchctl 07:00     │  cron diario macOS
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  watch.py            │  lee sources.yaml + state.yaml + known set
│  ├─ discover YT      │  yt-dlp --flat-playlist
│  ├─ filter (dur, ya) │  shorts <3min skip, ya-procesados skip
│  ├─ download m4a     │  yt-dlp bestaudio
│  ├─ transcribe MLX   │  video_to_knowledge_base_mlx.py
│  ├─ copy → kDrive    │  capa raw inmutable
│  └─ append backlog   │  entrada con pista [PENDIENTE]
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  backlog.md          │  TÚ lo revisas + ingieres con Claude
└──────────────────────┘
```

## Fuentes configuradas (sources.yaml)

| ID | Tipo | Frecuencia | Notas |
|---|---|---|---|
| `claude_anthropic_youtube` | youtube | **daily** | Canal oficial @claudeai |
| `anthropic_blog` | rss/web | daily | (handler RSS pendiente) |
| `bcherny_x` | x | **manual** | Necesita Chrome MCP + Claude interactivo |
| `karpathy_youtube` | youtube | weekly | Karpathy publica raro |
| `karpathy_x` | x | manual | Chrome MCP |
| `karpathy_gists` | rss | weekly | (handler RSS pendiente) |
| `seedrocket_tv_youtube` | youtube | weekly | Caso uso B2B España |

Edita `sources.yaml` para añadir más fuentes.

## Uso manual

```bash
# Activar venv
source /Users/shine/videoatexto/venv/bin/activate

# Solo ver qué descubriría sin bajar nada
python3 /Users/shine/videoatexto/watch/scripts/watch.py --discover-only --force-all

# Solo una fuente
python3 /Users/shine/videoatexto/watch/scripts/watch.py --force-all --source claude_anthropic_youtube

# Dry-run (no ejecuta acciones, solo loggea)
python3 /Users/shine/videoatexto/watch/scripts/watch.py --dry-run --force-all

# Ejecución real (descarga + transcripción)
python3 /Users/shine/videoatexto/watch/scripts/watch.py --force-all
```

## Operación cron (launchctl)

```bash
# Estado
launchctl list | grep bik

# Próxima ejecución + estado completo
launchctl print gui/$(id -u)/com.bik.wiki-watch

# Recargar tras editar el plist
launchctl unload ~/Library/LaunchAgents/com.bik.wiki-watch.plist
launchctl load ~/Library/LaunchAgents/com.bik.wiki-watch.plist

# Ejecutar manualmente fuera de horario
launchctl start com.bik.wiki-watch

# Desinstalar
launchctl unload ~/Library/LaunchAgents/com.bik.wiki-watch.plist
rm ~/Library/LaunchAgents/com.bik.wiki-watch.plist
```

Logs en `/Users/shine/videoatexto/watch/logs/`.

## Cómo ingerir desde el backlog (workflow Claude)

1. Abre `backlog.md` y elige una entrada (las nuevas se añaden al final).
2. En Claude: *"Ingiere al wiki la entrada de `nombre_del_archivo.knowledge.md`"*.
3. Claude lee el `.knowledge.md`, clasifica al category, genera la página wiki, actualiza index/log/schema/sources.yaml y verifica check_links.
4. Marca la entrada del backlog como ingerida (manualmente o con prefijo `✅ INGERIDA YYYY-MM-DD`).

## Pendientes (futuras iteraciones)

- [ ] Handler RSS para Anthropic blog + Karpathy gists
- [ ] Handler X (semiautomático con Chrome MCP) para Boris Cherny / Karpathy / @claudeai
- [ ] Notificación push macOS cuando hay backlog pendiente
- [ ] Skill `/ingest-backlog` que automatice los 4 pasos del workflow Claude
- [ ] Métrica de progreso del backlog (cuántas entradas pendientes vs ingeridas)
