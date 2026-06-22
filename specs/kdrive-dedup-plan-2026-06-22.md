# kDrive Dedup Plan — 2026-06-22 (CORREGIDO 2026-06-23)

> **Nota:** el plan automático original reportaba 211 pares / 195 borrados seguros.
> Verificación autoritativa fichero-a-fichero (grep -rlF contra wiki-conocimiento, 2026-06-23)
> revela que el número real es **32 pares** y que **31 tienen ambos nombres citados** en la wiki.

- **Pares dup reales (plain + VIDEOID_) en kDrive:** 32
- **Movidos a cuarentena (verificados uncited, reversible):** 1 — `_dedup_quarantine_2026-06-23/`
- **Requieren reconciliación de citas ANTES de borrar (ambos citados):** 32

## Acción para el agente-wiki

Por cada par: elegir UNA forma como canónica — **la citada en MÁS páginas wiki**
(`sources.yaml` es cita débil; cuenta páginas `wiki/**`). En empate, preferir la `VIDEOID_`
(la que produce el cron, lleva id). Actualizar las páginas que citan la otra forma para que
apunten a la canónica, y solo entonces mover la forma no-canónica a cuarentena.
NO borrar hard (mover, reversible).

| Forma A (VIDEOID_) | A citada en | Forma B (plain) | B citada en |
|---|---|---|---|
| `tmnd3M1k5Jw_5 CLI Tools That Actually Changed How I Work in 2026.knowledge.md` | sources.yaml, wiki/claude-code/skills-and-mcps.md | `5 CLI Tools That Actually Changed How I Work in 2026.knowledge.md` | sources.yaml, wiki/claude-code/skills-and-mcps.md |
| `yrbnx0fYJXM_Agentic Apps： The Next Evolution of User Onboarding — Madison Packer, WorkOS ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md | `Agentic Apps： The Next Evolution of User Onboarding — Madison Packer, WorkOS ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md |
| `N5yJJA0NCU0_AI on campus.knowledge.md` | sources.yaml, wiki/claude-code/anthropic-talks-aie2026.md | `AI on campus.knowledge.md` | sources.yaml, wiki/ai-agents-strategy/ai-and-education-cluster.md, wiki/claude-code/anthropic-talks-aie2026.md |
| `I9aGC6Ui3eE_Anthropic’s philosopher answers your questions.knowledge.md` | sources.yaml | `Anthropic’s philosopher answers your questions.knowledge.md` | sources.yaml |
| `GIRpQEfYf3U_Any-to-Any： Building Native Multimodal Agents - Patrick Löber, Google DeepMind.knowledge.md` | sources.yaml | `Any-to-Any： Building Native Multimodal Agents - Patrick Löber, Google DeepMind.knowledge.md` | sources.yaml, wiki/claude-code/ai-engineer-summit-2026.md, wiki/claude-code/multimodal-voice-vision-2026.md |
| `V5S40cLnku8_Ben Gilbert & David Rosenthal in Conversation with Michael Grinich ｜ Acquired Unplugged 2026.knowledge.md` | sources.yaml, wiki/claude-code/enterprise-vc-founder-2026.md | `Ben Gilbert & David Rosenthal in Conversation with Michael Grinich ｜ Acquired Unplugged 2026.knowledge.md` | sources.yaml, wiki/claude-code/enterprise-vc-founder-2026.md |
| `hHEPGJs0EnU_Can AI Agents Actually Build iOS Apps？ – Evan Bacon, Expo ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/mcp-servers.md | `Can AI Agents Actually Build iOS Apps？ – Evan Bacon, Expo ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/mcp-servers.md |
| `fOxC44g8vig_Claude Agent Skills Explained.knowledge.md` | sources.yaml | `Claude Agent Skills Explained.knowledge.md` | sources.yaml, wiki/claude-code/skills-mcps-tutorials.md |
| `OwMu0pyYZBc_Claude Code modernizes a legacy COBOL codebase.knowledge.md` | sources.yaml | `Claude Code modernizes a legacy COBOL codebase.knowledge.md` | sources.yaml, wiki/claude-code/anthropic-feature-demos.md |
| `5KTHvKCrQ00_Claude ran a business in our office.knowledge.md` | sources.yaml, wiki/claude-code/anthropic-talks-aie2026.md | `Claude ran a business in our office.knowledge.md` | sources-classified.yaml, sources.yaml, wiki/claude-code/anthropic-feature-demos.md, wiki/claude-code/anthropic-talks-aie2026.md, wiki/claude-code/cowork-and-teams.md |
| `MiLBc4dTYqo_Craig Cannon's Absurd AI MCP Built on a 90s Movie Idea.knowledge.md` | sources.yaml | `Craig Cannon's Absurd AI MCP Built on a 90s Movie Idea.knowledge.md` | sources.yaml |
| `0vZ_UVLhSQQ_Getting started with Claude.ai.knowledge.md` | sources.yaml | `Getting started with Claude.ai.knowledge.md` | sources.yaml, wiki/claude-code/consumer-claude-experiences.md |
| `_jjSS0qGFbI_Getting started with connectors in Claude.ai.knowledge.md` | sources.yaml | `Getting started with connectors in Claude.ai.knowledge.md` | sources.yaml, wiki/claude-code/consumer-claude-experiences.md |
| `GJ5jTgcbRHA_Getting started with projects in Claude.ai.knowledge.md` | sources.yaml | `Getting started with projects in Claude.ai.knowledge.md` | sources.yaml, wiki/claude-code/consumer-claude-experiences.md |
| `9oOZ3PB6n4Y_Hermes ⧸goal is insane… just watch.knowledge.md` | sources.yaml | `Hermes ⧸goal is insane… just watch.knowledge.md` | sources.yaml, wiki/ai-coding-tools/slash-goal-feature.md |
| `NMrZARcSWg4_How AI Agents Are Changing Product Development — Panel Discussion ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md | `How AI Agents Are Changing Product Development — Panel Discussion ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md |
| `tJP6SKfo49c_How Anthropic uses Claude in Legal.knowledge.md` | sources.yaml | `How Anthropic uses Claude in Legal.knowledge.md` | sources.yaml, wiki/claude-code/claude-vertical-case-studies.md |
| `zmrPY6S1FwY_I Turned Karpathy's Second Brain Into an AI Operating System.knowledge.md` | sources.yaml, wiki/claude-code/karpathy-llm-wiki.md | `I Turned Karpathy's Second Brain Into an AI Operating System.knowledge.md` | sources.yaml, wiki/claude-code/karpathy-llm-wiki.md |
| `o_Byo2z7FnY_Inside the WorkOS Applied AI Showcase： WOW, Horizon, Case & Wallaby.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md, wiki/claude-code/agent-orchestration-2026.md | `Inside the WorkOS Applied AI Showcase： WOW, Horizon, Case & Wallaby.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md, wiki/claude-code/agent-orchestration-2026.md |
| `kgksikB9O4c_Mastering MCP for Next-Gen AI Agents - Rhys Sullivan, Executor ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/mcp-servers.md | `Mastering MCP for Next-Gen AI Agents - Rhys Sullivan, Executor ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/mcp-servers.md |
| `a1jx0H4cSWk_MCP Night： Agent Mode — Announcing auth.md ｜ Live WorkOS Event at Regency Ballroom, SF.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md | `MCP Night： Agent Mode — Announcing auth.md ｜ Live WorkOS Event at Regency Ballroom, SF.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md |
| `Pbc2gPhx4ng_MCP Night and the Agentic AI Foundation.knowledge.md` | sources.yaml | `MCP Night and the Agentic AI Foundation.knowledge.md` | sources.yaml |
| `7BGLTj7Fs8M_Open Source AI Just Got Its Defining Moment.knowledge.md` | sources.yaml, wiki/claude-code/mcp-creator-origin.md | `Open Source AI Just Got Its Defining Moment.knowledge.md` | sources.yaml, wiki/claude-code/mcp-creator-origin.md |
| `vNCY9kXXyDQ_Skill issue： Lessons from skilling up coding agents to use Langfuse - Marc Klingen, Clickhouse.knowledge.md` | sources.yaml | `Skill issue： Lessons from skilling up coding agents to use Langfuse - Marc Klingen, Clickhouse.knowledge.md` | sources.yaml, wiki/claude-code/ai-engineer-summit-2026.md, wiki/claude-code/evals-and-observability-2026.md |
| `PtF7jq6EYwE_Stop giving Claude your real credit card — Karen Serfaty, AgentCard ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md | `Stop giving Claude your real credit card — Karen Serfaty, AgentCard ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md |
| `ow1we5PzK-o_The Multi-Agent Architecture That Actually Ships — Luke Alvoeiro, Factory.knowledge.md` | sources.yaml, wiki/claude-code/agent-orchestration-2026.md | `The Multi-Agent Architecture That Actually Ships — Luke Alvoeiro, Factory.knowledge.md` | sources.yaml, wiki/claude-code/agent-orchestration-2026.md, wiki/claude-code/ai-engineer-summit-2026.md |
| `6WsG_q8-ORE_The Story Nobody Saw Coming： MCP's Rise to Prominence.knowledge.md` | sources.yaml, wiki/claude-code/mcp-creator-origin.md | `The Story Nobody Saw Coming： MCP's Rise to Prominence.knowledge.md` | sources.yaml, wiki/claude-code/mcp-creator-origin.md |
| `Dqp_b8GHLXU_Unlock Autonomous AI Agents with auth.md, Michael Grinich ｜ MCP Night： Agent Mode Keynote.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md, wiki/claude-code/agent-orchestration-2026.md | `Unlock Autonomous AI Agents with auth.md, Michael Grinich ｜ MCP Night： Agent Mode Keynote.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md, wiki/claude-code/agent-orchestration-2026.md |
| `Uh98_aGhAuY_What does AI mean for education？.knowledge.md` | sources.yaml, wiki/claude-code/anthropic-talks-aie2026.md | `What does AI mean for education？.knowledge.md` | sources.yaml, wiki/ai-agents-strategy/ai-and-education-cluster.md, wiki/claude-code/anthropic-talks-aie2026.md |
| `lvMMZLYoDr4_What is Al ＂reward hacking＂—and why do we worry about it？.knowledge.md` | sources.yaml, wiki/claude-code/anthropic-safety-cybercrime.md | `What is Al ＂reward hacking＂—and why do we worry about it？.knowledge.md` | sources.yaml, wiki/claude-code/anthropic-safety-cybercrime.md, wiki/claude-code/claude-thinking-and-fluency.md |
| `PLyCki2K0Lg_Why we built—and donated—the Model Context Protocol (MCP).knowledge.md` | sources.yaml | `Why we built—and donated—the Model Context Protocol (MCP).knowledge.md` | sources.yaml, wiki/claude-code/mcp-creator-origin.md |
| `s03kkJ66R10_Why your AI agent needs its own inbox — Adi Singh, AgentMail ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md | `Why your AI agent needs its own inbox — Adi Singh, AgentMail ｜ MCP Night.knowledge.md` | sources.yaml, wiki/claude-code/agent-infrastructure-primitives-2026.md |
