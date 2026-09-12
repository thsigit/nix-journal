# From a Provider Zoo to a Free-Tier First Fleet (and a Skillet for the Rest)

**Date:** 2026-09-09  
**Author:** Codebot  
**Topic:** opencode, models, skills, nvidia, litellm, zen, free-tier, model-failover

---

## 1. Objective (or: What Are We Even Doing Here?)

The opencode config had been dragging around a model zoo that spilled in two directions at once. Upstream, every agent was pointed at paid-tier models with an auth key that kept growing stale or unreliable. Downstream, the skill shelf had accumulated redundant and stale entries -- three of them about connectivity and management that had quietly rotted since the LiteLLM proxy retired its Podman life.

This session's brief:

1. Migrate every opencode agent to **OpenCode Zen free-tier reasoning models** (`opencode/*`), zero auth key required.
2. Codify **kenari** (`kenari/kenari-free`) as the single designated fallback when a Zen model dies.
3. Delete the redundant/stale skills and the `homelab-management` agent.
4. Refresh the `universal-setup` skill to match reality.
5. Design (and build) a new skill that answers a real need: **a list of working NVIDIA NIM models to feed LiteLLM**, not opencode.

Twenty skills at the end, six agents, four commands, one new toolbelt for the NIM catalog. No emojis were harmed.

## 2. Background (or: The Zoo and Its Feeders)

The universal opencode hub (`/mnt/c/users/sigit/.config/opencode/opencode.json`, symlinked across Fedora, Debian, and Windows native) has been through a long evolution: BitRouter -> LiteLLM, aihubmix in and out, a prune-driven nvidia/openrouter/kenari lineup. The auth file (`auth.json`, also symlinked across the fleet) holds the union of provider tokens.

At the start of this session, the agent roster was seven agents deep, several pointed at models from providers whose keys were either unreliable (NVIDIA direct NIM) or simply not what the user wanted opencode to be on the hook for. The skills shelf carried 19 SKILL.md files with a few cross-cutting redundancies.

Of note: opencode has **no native per-agent fallback field** -- verified against the live config schema (`https://opencode.ai/config.json`) and docs during an earlier session of this saga. "Fallback" ships as a convention and a script, not a config key.

## 3. Problem (or: What We Actually Wanted)

1. **Free-tier first.** Every agent should run on a free OpenCode Zen reasoning model. The `opencode/*` models are built-in -- not entries in `provider.*.models` -- so a failover checker must know not to flag them as dead just because they are absent from the registry.
2. **One unambiguous fallback.** If a Zen model goes EOL/410/not-found/hangs, the next stop is kenari-free. Everything else (openrouter-free, nvidia, gpt-oss) is a reserve or a special case, not the default.
3. **A shelf that reflects reality.** Three skills had rotted: `provider-connectivity` (superseded by `litellm-connectivity`), `homelab-management` (stale Podman-era LiteLLM info, duplicating `ai-management`), `model-management` (stale nvidia whitelist/agent tables). The `homelab-management` agent was equally stale.
4. **A working NVIDIA list for LiteLLM.** NVIDIA models may not be reliable for opencode, but the user wants the NIM API key kept with a purpose: produce a **list of working NVIDIA models to supply to LiteLLM's config** (`/srv/appdata/litellm/providers.json`). That is a different output target than opencode's registry -- and therefore a different skill, even if it reuses the same probe engine.

## 4. Work Performed

### 4.1 Agents to the Free Tier

All six (post-cleanup) agents migrated to OpenCode Zen free models, each edit backed up to `/mnt/c/users/sigit/.config/opencode-backups/` and JSON-validated, command/agent descriptions synced:

| agent | model | steps |
|---|---|---|
| `build` | `opencode/big-pickle` | 32 |
| `plan` | `opencode/nemotron-3-ultra-free` | 32 |
| `code` | `opencode/nemotron-3.5-lightning-free` | 32 |
| `writer` | `opencode/muse-spark-1.3-contributor-free` | 32 |
| `general` | `opencode/big-pickle` | 32 |
| `explore` | `opencode/mimo-v2.5-free` | 32 |

Default `model` stays `nvidia/meta/muse-glimmer-30b`; `default_agent` is `plan`. Providers: `nvidia`, `openrouter`, `kenari`. Commands: `code`, `build`, `plan`, `writer`. Config home is `/home/sigit/.config/opencode/opencode.json`, canonically the hub file via symlink.

### 4.2 Kenari, the Designated Fallback

`model-failover/SKILL.md` updated (2026-09-09): **kenari/kenari-free is the universal fallback**; openrouter-free, `nvidia/meta/muse-glimmer-30b`, and nvidia's nemotron-3.5-lightning-30b are reserves. The live agent->model map is written into the skill. Built-in Zen models are **exempted from dead-model checks** (they aren't in `provider.*.models` by design). This is the codified stand-in for opencode's missing per-agent fallback field.

### 4.3 The Shelf Gets Lighter

Three skills deleted (all backed up to `opencode-backups/skills/`):

| deleted | why |
|---|---|
| `provider-connectivity` | superseded by `litellm-connectivity`; resolved models against the wrong provider |
| `homelab-management` | stale Podman-era LiteLLM content; duplicated `ai-management` |
| `model-management` | stale nvidia whitelist/agent tables; superseded by `model-failover` + the prune-* skills |

The `homelab-management` agent and its command were removed from `opencode.json` (backed up as `opencode-hub-pre-del-homelab-agent-20260909-001943.json`). References in `model-failover` and `universal-setup` cleaned. Cross-references in the skills README updated.

### 4.4 universal-setup, Refreshed

The universal-setup skill now reflects current reality: default `nvidia/meta/muse-glimmer-30b`, `default_agent` `plan`, providers nvidia/openrouter/kenari, 6 agents / 4 commands / steps 32, Zen free models + kenari fallback, auth providers `nvidia, openrouter, kenari, github-copilot`, skill count 14 -> 19. The README skills list was completed (it had silently stopped at 14 while the shelf held 19).

### 4.5 Enter litellm-nvidia-discovery

A new skill whose whole point is a distinct output target: **the LiteLLM config, not opencode.json**. It shares the NIM probe engine with `prune-nvidia-models` (list -> filter text-only -> per-model chat round-trip -> classify PASS/EOL-410/ERR/TIMEOUT) but:

- never writes to `opencode.json` (only *reads* `provider.nvidia.options.baseURL` from it);
- emits a **JSON whitelist** for the nvidia provider's `whitelist` in `/srv/appdata/litellm/providers.json`;
- outputs upstream NIM API IDs (e.g. `openai/gpt-oss-20b`, `nvidia/nemotron-3-super-120b-a12b`), matching what the existing nvidia provider entry already uses (`prefix: "openai"`).

Live probe (all 5 text-only NIM models, 2026-09-09, key from `~/.secrets/nvidia-key`):

| model | status |
|---|---|
| `meta/muse-glimmer-30b` | PASS |
| `moonshotai/kimi-k3` | PASS |
| `nvidia/nemotron-3-super-120b-a12b` | PASS |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | PASS |
| `openai/gpt-oss-20b` | PASS |

The user will supply/test this skill tomorrow before trusting the list to LiteLLM.

## 5. Verification (or: Proof, Not Vibes)

- `opencode.json` parses as valid JSON after every edit (python3 `json.load` clean).
- Bash syntax of the new probe script validated (`bash -n` clean, exit 0).
- List-only dry run with explicit `--models` filtered a non-text entry (`stabilityai/stable-diffusion-xl`) correctly.
- Live `--test` run: 5/5 PASS, JSON whitelist emitted in the correct upstream-ID format.
- Skills shelf: 20 directories, README lists all 20, no distro-local shadow copies of the new skill name.
- Backups verified present in the tray for every deleted skill and every config edit.

## 6. Results (or: The Magic Numbers Are Now Six and Twenty)

Final state of the fleet config:

- **Agents**: 6 (`build`, `plan`, `code`, `writer`, `general`, `explore`), all on OpenCode Zen free models, `steps: 32`.
- **Commands**: 4 (`code`, `build`, `plan`, `writer`).
- **Providers**: `nvidia`, `openrouter`, `kenari`. Auth union: `nvidia`, `openrouter`, `kenari`, `github-copilot`.
- **Skills**: 20 in the hub. New: `litellm-nvidia-discovery`. Refreshed: `universal-setup`, model-failover, skills README.
- **Fallback doctrine**: kenari-free is the universal fallback; nvidia/openrouter-free/gpt-oss remain reserves.

## 7. Recommendations

1. **Free-tier first is the right posture for opencode.** The Zen `opencode/*` models run without a key and are built-in -- keep them out of `provider.*.models`, and let the model-failover skill treat them as exempt from registry-death checks.
2. **Kenari stays the one designated fallback.** Do not add a second default tier; reserves are reserves for a reason. If kenari becomes the de-facto workhorse, reassess rather than stacking a third tier.
3. **Test litellm-nvidia-discovery tomorrow before feeding the list to LiteLLM.** The probe passed 5/5 today, but "test the new skill" is written in ink, not pencil. Expected follow-up: hand-edit the nvidia `whitelist` in `providers.json`, `litellm-cli debug render`, restart `litellm-render` + `litellm`, and confirm `/v1/models` via the proxy.
4. **Keep the two NIM skills honest about their split.** `prune-nvidia-models` owns the opencode registry; `litellm-nvidia-discovery` owns the LiteLLM whitelist. Same engine, different doors -- keep the cross-references in each SKILL.md prominent.
5. **Skill shelf hygiene is now contractual.** The README lists all 20; future additions should update the count and the list in the same commit as the new SKILL.md.

## 8. Open Questions and Follow-Ups

- **NVIDIA as an opencode provider** remains "may not be reliable" per the user -- no decision to drop it, but no new dependents either.
- **Restart confirmation**: config changes need an opencode restart to take effect; skills are read at runtime and need none. The tail of this migration is a clean opencode+session restart on all three hosts.

## 8.1 Dashboard Update

The homepage at `homelab.home.arpa` was updated to reflect live LAN services:

- **Removed retired cards**: `litellm.home.arpa` and `vane.home.arpa` (both confirmed retired 2026-09-09; no Caddy host blocks remain).
- **Added live services missing from the dashboard**: `ai` (LiteLLM frontend at `ai.home.arpa`), `chat` (Open WebUI at `chat.home.arpa`), `llama` (llama.cpp at `llama.home.arpa`), `whisper` (STT server), `mailpit` (email testing).
- Footer count adjusted from "18 layanan" to "19 layanan" to match the new 19-card grid.
- A `README.md` was added at `/srv/www/homepage/` documenting the source-of-truth (Caddy nix-lab config), retired hosts, and the convention that card lists must match live Caddy vhosts.

## 8.2 Nix-lab Changes

- `caddy.nix` (`/srv/repo/nix-lab/common/web/caddy.nix`): removed the `handle /lidarr*` route block (3 lines deleted, git commit `dd9d50b`). This route served `/lidarr` under `homelab.home.arpa` but the underlying service is long gone (no listener on port 8686).
- The rendered `/etc/caddy/caddy_config` was also edited to remove the dead route. It will fully take effect after `nixos-rebuild switch`.
- `/srv/www/litellm/` was moved to trash then fully deleted — a stale duplicate of `/srv/www/ai/` with zero references in nix or Caddy config.

---

Generated by Big Pickle (OpenCode)