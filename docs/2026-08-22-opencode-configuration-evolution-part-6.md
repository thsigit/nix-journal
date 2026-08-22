# OpenCode Configuration Evolution - Part 6 (FINAL)

*The agent CLI path: OpenClaw to Hermes Agent to OpenCode*

**Date:** 2026-08-22  
**Author:** Codebot  
**Topic:** OpenCode, Hermes Agent, openclaw, agents, evolution, homelab

---

## 1. Objective

Document the evolutionary path of the homelab's primary CLI agent across three tools - OpenClaw, Hermes Agent, and OpenCode - using the blog archive itself as evidence. This closes the arc that Parts 1-5 of this series covered only from the OpenCode side: how OpenCode became the daily driver, why each migration happened, and what carried over at each step.

## 2. Background

Three agent generations in roughly eight weeks:

| Generation | Tool | Era | Primary role |
|---|---|---|---|
| 1 | OpenClaw | before 2026-06-29 | First satisfying CLI agent |
| 2 | Hermes Agent | 2026-06-29 to 2026-07-22 | More powerful successor; blogging began here |
| 3 | OpenCode | 2026-07-16 onwards (sole driver since 2026-07-22) | Current agent |

The OpenClaw era predates AI blogging entirely - no session reports were written while it was in service. Its footprint survives only indirectly, inside articles drafted under Hermes Agent (and later edited under OpenCode) and in migration/cleanup notes.

## 3. Evidence Trail

### 3.1 OpenClaw era (indirect evidence)

No contemporaneous posts exist. The tool is documented only when Hermes Agent replaced it:

- `2026-06-29-openclaw-dementia-and-config-backups.md` - diagnoses "OpenClaw's inability to reach configured models" (nicknamed dementia) and establishes config backup practices for Hermes Agent equivalent to OpenClaw's JSON config. Confirms OpenClaw used a plain JSON configuration worth mirroring.
- `2026-06-29-hermes-claw-migrate-dry-run.md` - dry-run of `hermes claw migrate` importing settings, memories, skills, and API keys from OpenClaw into Hermes. Confirms OpenClaw held accumulated state worth migrating.
- `2026-06-29-provider-and-fallback-chain-part-3.md` - Gemini migration notes warn that "credential propagation to external tools (OpenCode, OpenClaw)" must avoid plaintext shell profiles - proof OpenClaw still ran alongside during the transition window.

### 3.2 Hermes Agent era (2026-06-29 to 2026-07-22)

Blogging itself started under Hermes Agent:

- `2026-06-29-a-day-with-hermes.md` - resilient failover across free-tier providers; memory upgraded from SQLite to mem0.
- Provider and Fallback Chain Parts 1-5 (`2026-06-20` to `2026-07-20`) - the whole provider/failover struggle (lean stack audit, OpenRouter, Gemini, multi-layer fallback, retiring Fireworks) played out against Hermes.
- `2026-06-29-blogging-skill-evolution-part-1.md` - first blogging skill was a Hermes Agent skill.

### 3.3 The transition (2026-07-16 to 2026-07-22)

Hermes Agent model setup for free tiers proved painful; this is where OpenCode entered:

- `2026-07-16-the-agent-that-didnt-get-to-upgrade.md` - earliest OpenCode appearance as an installed tool (v1.15.10 on NixOS, twice-failed upgrade).
- `2026-07-18-building-a-multi-agent-workflow-orchestrator.md`, `2026-07-20-pm-assistant-v0.4-crash-safe-and-configurable.md`, `2026-07-21-pm-assistant-builds-a-text-editor.md` - new development shifted to OpenCode while Hermes Agent aged.
- `2026-07-22-cleaning-up-hermes-and-widening-the-shell-history.md` - the cutoff: `~/.hermes/` deleted entirely, Ollama config stripped of Hermes Agent blocks. Remaining integrations list names both `openclaw` and `opencode` - Hermes Agent gone, OpenClaw reduced to an unused leftover entry.
- `2026-07-22-opencode-configuration-evolution-part-1.md` - same day, the agent roster established OpenCode's specialized routing (thinking, coding, reviewing, vision, fast, cheap).

### 3.4 OpenCode era (2026-07-22 to present)

This series, Parts 1-5, plus adjacent arcs:

- OpenCode Configuration Evolution Parts 1-5 - agent roster, persistent context, provider cleanup, multi-provider config, NVIDIA whitelist.
- Blogging Skill Evolution Parts 2-5 - blogging rebuilt on OpenCode, standardized, and published via Zensical.
- The LiteLLM Gateway Evolution Parts 1-14 - the gateway OpenCode consumes.
- Mem0 Memory Integration Parts 1-4 - persistent memory behind OpenCode.

## 4. Diagnosis

Why each hop happened:

1. **OpenClaw to Hermes Agent** - capability ceiling, then reliability. OpenClaw was satisfying but Hermes Agent was more powerful; ironically OpenClaw's own model-reachability failure (the dementia episode) sharpened the config-backup discipline Hermes Agent inherited.
2. **Hermes Agent to OpenCode** - free-model configuration friction. Hermes Agent made multi-provider free-tier setup laborious exactly when the provider count exploded; OpenCode's registry-driven provider model (models.dev plus explicit `provider.*` blocks) and per-agent model routing removed that pain. The agent roster (Part 1) was the payoff: right model for right job without manual swapping.

## 5. What Carried Over

| Step | Mechanism | Payload |
|---|---|---|
| OpenClaw to Hermes Agent | `hermes claw migrate` dry run | Settings, memories, skills, API keys |
| Hermes Agent to OpenCode | Manual reconfiguration | Skills recreated (blogging Part 2), providers redefined (Part 4), memory re-attached via Mem0 (Mem0 Integration series) |

The second hop lost the automatic migration but gained a cleaner separation: credentials in sops/auth.json, catalog in models.dev plus explicit config, memory in Mem0, gateway in LiteLLM.

## 6. Current State (Closing Snapshot)

- **Agent**: OpenCode, sole CLI driver since 2026-07-22.
- **Routing**: seven specialized agents (chat, reason, code, review, vision, fast, cheap).
- **Gateway**: native LiteLLM systemd service (no Podman, no DB), 400+ models from nvidia/openrouter/zai/ollama.
- **Memory**: Mem0 via official plugin, project/session/global scoping.
- **Publishing**: Zensical static site at reports.home.arpa, auto-rebuilt on markdown change.

## 7. Solution Summary

The path OpenClaw to Hermes Agent to OpenCode traces a straight line: each tool died on configuration friction (model reachability, then free-tier setup) and each successor absorbed its predecessor's lessons as structure - JSON backups became sops secrets, ad-hoc memories became Mem0, single-model compromise became per-agent rosters behind a unified gateway.

## 8. Verification Plan

Not applicable - historical synthesis. Cross-checks: every claim above links a dated report in this archive; dates and quotes were taken directly from the cited files.

## 9. Pending Actions

None for this arc. OpenClaw's last trace is the unused integration entry noted on 2026-07-22; remove it whenever the integration list is next touched.

## 10. Recommendations

- When adopting a new agent, migrate deliberately (dry-run first, as the `hermes claw migrate` dry run did) and keep the old tool's config until the new one passes a real work week.
- Keep per-tool configuration discipline (backups, secret handling) so the next migration is a port, not a rebuild.
- Record tool transitions in the blog even when the tool is unglamorous - this report could only be written because Hermes-era articles mentioned OpenClaw in passing.

Generated with x-preview-f-free (OpenCode)
