# Retiring BitRouter: LiteLLM Becomes the Homelab's Single Gateway

**Date:** 2026-09-01  
**Author:** Codebot  
**Topic:** bitrouter, litellm, gateway, nix, providers, nvidia, freetheai

---

## 1. Objective (or: One Router to Rule Them All)

Last session we learned BitRouter can't actually *chat* through a custom
provider - it will happily advertise `nvidia` and `freetheai` models in
`/v1/models` and then throw `no outbound dispatch registered for protocol
'openai'` the moment you call one. We reverted to its one working job:
`openrouter/free`.

That was the last straw in a long-running question: does the homelab need *two*
LLM gateways? The answer this session was a decisive **no**. We set out to
retire BitRouter entirely and make LiteLLM the single custom LLM gateway -
plus fold in the bits we actually liked about BitRouter along the way.

The concrete roadmap had five items:

1. Retire BitRouter (nix config, container, archive its config)
2. Add FreeTheAI models to the LiteLLM catalog
3. Fold the curated nvidia whitelist + blacklist pruning into `providers.json`
4. Mint per-client virtual keys (best-effort)
5. Point opencode at `litellm.home.arpa` only

The user accepted all five and said two words that have launched a thousand
sessions: "Now execute."

## 2. Background

### 2.1 Where We Left Off

The previous report (`2026-09-01-bitrouter-alpha-27-add-providers.md`) ended
with the verdict that BitRouter alpha.27's dispatch table simply has no adapter
for custom OpenAI-compatible providers. LiteLLM, meanwhile, already ran
nvidia/freetheai/openrouter successfully. Two gateways, one of which could only
route a single model - and that one model is now blacklisted in LiteLLM's
curated set anyway (`cohere/north-mini-code:free`, more on that later).

### 2.2 How the LiteLLM Setup Actually Works

This is worth pinning down, because it's the friction point that shaped the
whole session. The homelab runs **litellm-cli**, a NixOS+CLI wrapper around
LiteLLM. Its "source of truth" is an admin-owned JSON file:

```
/srv/appdata/litellm/providers.json   (root:root 644, survives reinstall)
```

But `providers.json` is **not** a live drop-in. The effective model list is
produced by a pipeline:

```
providers.json (admin)          -> defines providers, keys, whitelist/blacklist, models
/run/litellm-cli/models.json    -> auto-discovered model catalog (fetched from each provider)
      |
      v
lib/render.sh (jq)              -> joins the two into model_list entries
      |
      v
/var/lib/litellm/config.yaml    -> what the litellm daemon actually reads
      |
      v
systemctl restart litellm       -> daemon picks up the new config
```

The catch: `render.sh` lives inside the nix-flake `litellm-cli` input, so
changing *how* models render requires a `nixos-rebuild` (which per `AGENTS.md`
only the user runs). Editing model *lists* is easy; editing the *render logic*
is build-coupled.

## 3. Problem

BitRouter is redundant, LiteLLM is the workhorse, and we want a single gateway.
To get there we need to:

- Remove BitRouter from the nix config, shut down its container, archive its
  config.
- Make LiteLLM the exclusive gateway and fix the pieces that needed it
  (freetheai models, nvidia whitelist, pruned blacklist, working fallbacks).
- Repoint opencode's providers and agent models at litellm only.

Plus the recurring background problem that nagged us the whole time: **NVIDIA's
upstream API is degraded** (old-gen 410 EOL, current-gen 503/timeouts), and
FreeTheAI's chat was intermittently 503. The gateway can't fix upstream health -
but it should at least route cleanly to whatever *is* healthy.

## 4. Work Performed

### 4.1 Getting BitRouter Ready for the Scrap Heap

The nix changes were the surgical part. Three files in `/srv/repo/nix-lab`:

- `common/ai/default.nix` - dropped the `./bitrouter.nix` import
- `flake.nix` - removed the `bitrouter` flake input and its `commonSpecialArgs`
  entry
- `common/security/pki.nix` - removed `bitrouter.home.arpa` from `extraDomains`
  (and a stale comment mention)

We also refreshed `flake.lock` because the `litellm-cli` input's narHash had
gone stale from all the local edits - the rebuild was rejecting it with a NAR
hash mismatch. `nix flake lock --update-input litellm-cli` recomputed that entry
(and, happily, pruned the now-unused `bitrouter` lock node too).

The user ran the rebuild themselves (per `AGENTS.md:30-41`, the agent never runs
`nixos-rebuild`). That's what took the container down - by the time we checked,
only `linkding` and `vane` were running; the `bitrouter` container was gone.

### 4.2 The Archive (and a Small Concession to Convention)

We archived what needed preserving: the BitRouter nix module moved to
`archive/ai/bitrouter/bitrouter.nix` (git detected it as a clean rename, so
history is preserved), and we stashed a copy of the runtime appdata in the
archive.

Then we looked at the existing `archive/` convention: it tracks **only** `.nix`
config files - zero `.db`, `.cache`, or `.log`. The big `bitrouter.db` (a 144K
SQLite file), the `.cache/registry.json`, and the logs didn't belong in git. We
scanned them for secrets anyway (clean - the registry only referenced env var
*names*, never values), then dropped the binaries to keep the archive
consistent. The BitRouter YAML config it actually needed to reproduce behavior
was already captured in the `.nix` module.

### 4.3 LiteLLM: New Providers, Curated Models, Pruned Blacklist

The `providers.json` edits were the meat:

**FreeTheAI** - added as a provider with `prefix: "openai"` (so LiteLLM uses its
OpenAI adapter against `api.freetheai.xyz`) and four manual GLM models:
`glm/glm-4.5`, `glm/glm-4.5-air`, `glm/glm-5.3`, `glm/glm-5.3-flash`.

**NVIDIA** - replaced the old 57-item blacklist with an **11-model whitelist**.
This is the "fold the template" part: instead of "everything except these," we
now say "these and only these." Before shipping we corrected two whitelist IDs
for NVIDIA's real prefix scheme - hosted models are *unprefixed*
(`mistralai/mistral-nemotron`), while nvidia-branded models are *double-prefixed*
(`nvidia/nvidia/nemotron-3-super-120b-a12b`). All 11 IDs were verified present
in the live inventory before wiring the whitelist.

**OpenRouter** - trimmed the free tier to what we actually route: `:free`
suffix models plus the bare `openrouter/free` fallback. Notably blacklisted
`cohere/north-mini-code:free` (which the opencode `code` agent was using),
`stepfun/step-3.7-flash`, and `minimax/minimax-m3`.

**Routing** - added a fallback arm so requests to `openrouter/openrouter/free`
that fail fall through to `freetheai/glm/glm-4.5`.

To make the whitelist actually do anything, we patched `lib/render.sh` to honor
a `whitelist` key (a jq filter after the existing blacklist filter). The diff is
two lines:

```diff
   | (\$cfg.blacklist // []) as \$disabled
+  | (\$cfg.whitelist // null) as \$allow
   | (\$inventory + \$manual)
   | map(select(.id as \$id | (\$disabled | index(\$id)) | not))
+  | map(select(.id as \$id | (if \$allow != null then (\$allow | index(\$id) != null) else true end)))
```

Here's the rub: this `render.sh` change only takes effect **after a rebuild**,
because the running render binary is a stale `/nix/store` copy. We staged all
the config edits for the user's rebuild (see item 4.1), and the whitelist would
come along with it.

### 4.4 Render, Reload, Restart (an Experiment in Patience)

Once the user's rebuild landed, it was time to apply the new config. Tiny
detour: we tried `POST /v1/reload` first - **404**. This LiteLLM build doesn't
expose a reload endpoint. So it was `systemctl restart litellm`.

First render-cum-restart attempt raced the daemon's startup and returned empty
JSON. A quick poll loop found the answer: LiteLLM needs a few seconds past
"systemctl active" before it answers `/v1/models`. Second try, all good.

The new `/v1/models` listing confirmed the curated set:

```
{'nvidia': 11, 'openrouter': 17, 'freetheai': 4}   # 32 total
```

with exactly the 11 nvidia whitelist entries, the 4 freetheai GLMs, and the
openrouter `:free`-only set.

### 4.5 Round-Trips (and the Two Upstreams We Can't Fix)

Then we actually called the models through the gateway:

| Model | Result |
|---|---|
| `openrouter/openrouter/free` | 200 - routed, "Okay, the user said..." |
| `freetheai/glm/glm-4.5` | 503 from upstream (provider temporarily unavailable) |
| `nvidia/google/gemma-4-31b-it` | 000 timeout |

Not a gateway bug. We verified both problem upstreams **directly**, bypassing
LiteLLM:

- FreeTheAI direct chat: `503 provider temporarily unavailable` (took 21s to
  admit it) - a free-tier upstream outage, resumable on its own.
- NVIDIA direct chat: `000` after 50s - the ongoing NVIDIA NIM degradation from
  the previous report, still not accepting chat.

So the gateway config is correct and serving; the two sick upstreams will start
working through LiteLLM automatically when their APIs recover. LiteLLM
faithfully routes to whatever is healthy - which today is openrouter.

### 4.6 Item 4: Virtual Keys - a Structural No

We tried to mint per-client virtual keys via `POST /key/generate` with a 30-day
budget and the full 32-model allow-list. LiteLLM answered:

```
{'error': {'message': "{'error': 'DB not connected. See
https://docs.litellm.ai/docs/proxy/virtual_keys'}", ...}}
```

Virtual keys require a LiteLLM **database** (SQLite/Postgres). There's no
`database_url` in the config - by design, since it would drag in the very
Prisma/Postgres dependency we're avoiding. One clean, structural 500 was enough;
per the user's "if it doesn't work after 3 tries, leave it be," we left it be on
attempt one. The master key stays in opencode for now.

### 4.7 Repointing opencode

The last mile: edit opencode's config so it talks to litellm only. Backed up
`opencode.json` to the backup tray first (per the backup-opencode skill), then:

- Removed the entire `bitrouter` provider block (and its `brvk_` key).
- Removed the now-inert standalone `nvidia` whitelist block.
- Changed the default model from `litellm/nvidia/meta/llama-3.3-70b-instruct`
  (NOT in the new nvidia whitelist - would 404) to
  `litellm/nvidia/google/gemma-4-31b-it`.
- Repointed the `code` agent off the blacklisted
  `litellm/openrouter/cohere/north-mini-code:free` -> `litellm/openrouter/openrouter/free`.

Validated: JSON parses, `provider.litellm` is the only provider left, default
model and code-agent model both resolve to currently-served set.

### 4.8 Committing It All

Two repos, both clean:

**nix-lab** `a9bde43` - `ai: retire bitrouter; archive config to archive/ai/bitrouter`
- BitRouter nix module renamed into `archive/ai/bitrouter/`, plus the
  default.nix/flake.nix/pki.nix edits and flake.lock refresh (a pre-existing
  `pki.nix` mode change 755->644 rode along).

**litellm-cli** `f3c3bef` - `litellm-cli: add whitelist support to render; update stats/status`
- Per user's choice, all modified tracked files in one commit (render.sh
  whitelist + pre-existing stats.sh/litellm-cli diffs). The untracked debug
  files `default.nix.backup` / `default.nix.broken` were left alone.

## 5. Diagnosis

We came in to retire BitRouter and ended up re-architecting how LiteLLM gets its
config. Two findings crystallized:

1. **BitRouter's only reliable route (`openrouter/free`) was now blacklisted in
   LiteLLM anyway** - which is to say, the thing BitRouter did, LiteLLM now does
   (on a model the opencode config no longer references). Full redundancy
   achieved by subtraction.
2. **LiteLLM's config ergonomics are the real story.** `providers.json` is a
   declarative source of truth, but the render pipeline - and the fact that
   render logic ships in a nix flake - means "I want to change how a provider
   works" still needs a rebuild. Adding *models* is a file edit; changing
   *provider handling* is not.

## 6. Preliminary Assessment

- The single-gateway consolidation succeeded: LiteLLM is now the homelab's only
  custom LLM gateway, serving a curated 32-model set.
- The two degraded upstreams (nvidia, freetheai chat) are upstream problems, not
  config problems; they'll surface automatically when healthy.
- Virtual keys are out of reach without adding a DB - a deliberate tradeoff to
  keep the Prisma/Postgres weight out of the tree.
- The config-ergonomics friction is real and worth a follow-up (it's now a
  documented task).

## 7. Solution Summary

BitRouter retired and archived. LiteLLM now serves a curated, whitelisted model
set (11 nvidia + 4 freetheai + 17 openrouter-free) with a working openrouter ->
freetheai fallback. opencode points at litellm only, uses only models that are
actually served. The render pipeline gained whitelist support (the nvidia
"fold"). Everything committed across two repos.

What we deliberately did *not* run: `podman rm -f bitrouter` (the container was
already gone from the rebuild), and only one `/key/generate` attempt (structural
blocker, left per instruction).

## 8. Verification Plan

- [x] Nix rebuild succeeded (user-run); bitrouter container gone.
- [x] `nv liteLLM /v1/models` = 11 nvidia + 4 freetheai + 17 openrouter (32).
- [x] openrouter `openrouter/openrouter/free` round-trip 200 through gateway.
- [x] freetheai/nvidia round-trips fail `only` because upstreams are down (verified direct).
- [x] `opencode.json` JSON-valid; litellm is the only provider; default + code
      agent models point at served models.
- [x] Both repos committed clean.
- [ ] (Deferred) Virtual keys - blocked on a DB, not attempted further.
- [ ] (Pending) NVIDIA/FreeTheAI chats resume automatically when upstreams heal.

## 9. Pending Actions

- Confirm `podman rm -f bitrouter` for any leftover image (container already
  stopped by rebuild; a stray image may remain).
- Revisit virtual keys only if we ever accept a LiteLLM database (and with it,
  the Prisma/Postgres weight) - or switch to a gateway with built-in keys on
  no-DB (see Recommendations and the open task).
- Evaluate the config-ergonomics follow-up captured in
  `~/.config/opencode/tasks/pending-custom-gateway-option-b.md`.

## 10. Recommendations

1. **LiteLLM is now the single gateway - keep it that way.** One router that
   works beats two that mostly don't.
2. **Fix the config ergonomics, don't replace the gateway.** The real annoyance
   is that changing *provider handling* needs a rebuild. The documented,
   lowest-risk next step is decoupling the render logic from the nix build (a
   runtime render script + editable providers file), which sidesteps the
   Prisma/rebuild pain entirely without leaving nixpkgs.
3. **If ergonomics alone can't be fixed acceptably, research re-verified:** no
   LLM gateway other than litellm is merged in nixpkgs today. The credible
   replacements are third-party flakes - **Ollmo/LigmaGate** (Rust, single
   hot-reloaded TOML config dir, no DB) or **openziti/llm-gateway** (Go, one
   YAML, no DB, has virtual keys). Only if both are rejected does hand-rolling
   (task option B) become justified.
4. **Keep the no-DB stance.** Virtual keys are a nice-to-have; the Prisma /
   Postgres weight they'd drag in is not. If key management ever matters, pick a
   gateway that does keys with zero DB (openziti does) rather than enabling a
   database on litellm.
5. **Remember the two-line lesson:** a "model advertised" is not a "model
   callable," and an upstream that's down is not the gateway's fault - test
   direct before blaming the proxy.

## Relevant Files

- `/srv/repo/nix-lab` - `a9bde43` retire bitrouter (archive at
  `archive/ai/bitrouter/`)
- `/srv/repo/litellm-cli` - `f3c3bef` whitelist support in render + stats/status
- `/srv/appdata/litellm/providers.json` - live curated catalog (nvidia
  whitelist, freetheai, openrouter blacklist, fallbacks)
- `/srv/repo/nix-lab/common/ai/litellm/{litellm.nix,litellm-cli.nix}` - nix
  wiring for the render pipeline
- `/mnt/c/users/sigit/.config/opencode/opencode.json` - litellm-only providers,
  updated models (backup in the opencode-backups tray)
- `/home/sigit/.config/opencode/tasks/pending-custom-gateway-option-b.md` -
  on-hold task capturing ergonomics requirement + native-alternative research

---

Generated by Big Pickle (OpenCode)
