# BIK Competitive Watch — Digest 2026-06-22 (curado + verificado 2026-06-23)

> Borrador de la rutina cloud `trig_01YVvLjF6i9AVxwwx1LhaeRD` (lun 06-22), re-escaneado
> y **verificado en fuente** por el curador. Entrega para `crm-pm-front/specs/competitive-watch.md`.
> El commit a crm-pm-front lo hace producto (no se commitea desde esta sesión).

## Headline

Los **3 competidores convergen en agent-native / MCP**, justo el diferenciador de BIK.
**Linear** es el movimiento de la semana: el 18-jun integró el framework de agentes **Vercel Eve**
y (11-jun) lanzó *Coding sessions* — su agente ya escribe código vía **Claude Code + Codex**.
**ClickUp** está en "infra hold" para "dos features muy grandes" inminentes. **Plane** sin release
material en la ventana (último: 31-may, MCP Marketplace).

## Linear (verificado en linear.app/changelog)

| Feature | Fecha | Impacto BIK |
|---|---|---|
| Coding sessions — el agente escribe código (Claude Code + Codex) con diffs | 11-jun | **NEW-THREAT-MOAT** |
| Integración con **Vercel Eve** (framework OSS de Vercel p/ construir agentes) | 18-jun | **NEW-THREAT-MOAT** |
| Agent-assisted project updates ("Write with Agent") | 18-jun | **CLOSES-GAP** |
| Shared skills for Linear Agent | 4-jun | WATCH-DESIGN |
| Private sub-teams · Release pipeline changelogs · OAuth manifests | 18-jun | WATCH-DESIGN / LAG-minor / IGNORE |

## Plane (clean-room — observar, NO copiar código AGPL)

| Feature | Fecha | Impacto BIK |
|---|---|---|
| MCP app publishing desde Marketplace (mcp.plane.so) | 31-may | **NEW-THREAT-MOAT** |
| Private dashboards | 31-may | **CLOSES-GAP** |
| Epics como work-item type · Due-date reminders | 31-may | PARITY |
| v2.6.3 (ops patch, self-hosted); sin release material 15-22 jun | 19-jun | — |
| Q2 Launch Week (8-12 jun) — full list no renderizó, revisar manual | jun | WATCH-DESIGN |

## ClickUp

| Feature | Fecha | Impacto BIK |
|---|---|---|
| "Infra hold" — 2 features grandes inminentes (monitor diario) | 15-jun | WATCH-DESIGN |
| Outlook connected search en Brain (4.05) | 9-jun | **CLOSES-GAP** |
| AI Notetaker en SyncUps (4.05) | 9-jun | PARITY |
| MCP Server (public beta) · Super Agents · @Codegen | may | **NEW-THREAT-MOAT ×3** |
| Gantt Baselines (4.04) | 5-may | **CLOSES-GAP** |

## Acciones BIK

1. **⬆️ capability-map:** el moat agent-native lo tocan los 3. Linear *coding-agent* (Claude Code/Codex) + Vercel Eve = la apuesta de BIK ahora tiene competencia directa. **Pushear BYOA/Fleet Cockpit ya.**
2. **ClickUp infra-hold** → monitor diario del changelog (drop grande inminente).
3. **CLOSES-GAP recurrentes:** búsqueda universal (ClickUp Outlook) + Gantt (Baselines) siguen siendo huecos de BIK.
4. **Plane Q2 Launch Week** (8-12 jun): revisar manual la lista completa (no renderizó vía fetch).

---
*Notas de curador: "Vercel Eve" verificado = framework de Vercel integrado por Linear (no construido por Linear). "Coding sessions" (11-jun) lo añadí yo — el escaneo automático lo omitió. Resto de fechas/nombres verificados en fuente.*
