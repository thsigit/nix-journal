# Taming the Model Zoo: Filtering NVIDIA, Kenari, and OpenRouter to Working Text Models (Plus a Copilot Pulse Check)

**Date:** 2026-09-04  
**Author:** Codebot  
**Topic:** opencode, model pruning, nvidia, kenari, openrouter, github copilot, skills, whitelist

---

## 1. Objective (or: Why Does `opencode models` Show 359 Things I Will Never Use?)

The owner wanted `opencode models <provider>` to return only the models that
actually work, instead of the full firehose of every model a provider exposes.
Specifically:

- Filter each provider down to **text-only** models.
- Test which of those can actually **generate text** (not just exist in a catalog).
- Prune the opencode configuration so the listing reflects reality.
- Do this for **NVIDIA NIM**, **Kenari**, and **OpenRouter**.
- Bonus round: figure out what, if anything, can be done with the **GitHub Copilot**
  credential that opencode already holds.

The end state we were after: run `opencode models nvidia` and see five sensible
models, not ninety-nine.

## 2. Background

opencode stores providers in a single universal hub config at
`/mnt/c/users/sigit/.config/opencode/opencode.json` (symlinked into each distro's
`~/.config/opencode`). The three distros (FedoraWSL, Debian, Windows-native) all
deep-merge this hub plus a small per-OS overlay (`opencode.fedora.json`, etc.).

Three providers were in scope:

- `nvidia` -> `https://integrate.api.nvidia.com/v1` (NVIDIA NIM, direct).
- `kenari` -> `https://kenari.id/v1` (free tier).
- `openrouter` -> `https://openrouter.ai/api/v1`.

GitHub Copilot is different: it is an **OAuth credential** in
`auth.json` (`github-copilot.access`), not a config provider with a model catalog.

Provider API keys live in `~/.secrets/` (nvidia, openrouter) and are resolved at
opencode runtime for kenari.

## 3. Problem (or: The Catalog Lied, and So Did the Config)

Two nasty surprises surfaced early, and they are the kind that make you question
your Tools license.

### 3.1 The `models` object is decorative

Editing `provider.<p>.models` does **nothing** to what `opencode models <p>`
prints. That command fetches the live provider catalog every time. We proved this
by pruning `provider.nvidia.models` to six entries and still getting 101 models
back. The `models` object is just per-model metadata (names, limits, cost). It is
not a gate.

### 3.2 `blacklist` is a trap here

The schema's `ProviderConfig` does have a `blacklist` array. We tried it. It was
silently ignored for the listing. Worse, `opencode models nvidia` returns a
**variable** number of models per run (we saw 101, then 55, then 7). A blacklist
must enumerate the entire catalog, so a moving target means a blacklist can never
cover what the listing did not return this time. Deterministic failure, dressed up
as a config option.

The key that actually gates the listing is the provider-level `whitelist` array,
and it demands **provider-relative IDs** (`meta/muse-glimmer-30b`, NOT
`nvidia/meta/muse-glimmer-30b`). The wrong form is also silently ignored. So the
fix is a `whitelist` of only the confirmed-good models, written into the hub
config. No per-OS overlay edits needed; they deep-merge the hub.

## 4. Work Performed

### 4.1 Built `prune-nvidia-models`

A script that lists NVIDIA models, drops non-text entries by name pattern
(flux, whisper, esm, image, video, embed, rerank, guard, multimodal, omni, ...),
then chat-round-trips every surviving text model against NVIDIA NIM. PASS models
are written to `provider.nvidia.whitelist` in the hub. It backs up `opencode.json`
first (timestamped `.pre-prune-*` files) and repoints only this provider's
default/agents when the kept set changes.

First result: 5 working text models.

### 4.2 Cloned for Kenari and OpenRouter

`prune-kenari-models` and `prune-openrouter-models` are parameterizations of the
same logic with provider-specific identity (key file, fallback baseURL, slug
prefix). The error parser was hardened to understand multiple provider error
shapes (NVIDIA `{"status":410,"detail":...}`, OpenRouter `{"error":{"message":...,"code":401}}`,
generic) instead of printing `ERR unknown`.

### 4.3 Free-tier rule (or: 334 Models Is A Lot Of Round-Trips)

OpenRouter's text catalog is 334 models deep. Live-testing all of them is
wasteful and slow. We added a provider-specific rule: only the **free-tier** text
models (slugs ending `:free`, `-free`, or `/free`) are live-tested; everything
else is auto-blacklisted without a round-trip. The same rule was applied to Kenari
after the owner said they only care about the free Kenari models. Net effect:
`opencode models openrouter` shows 10 free models, `opencode models kenari` shows
7 free models.

### 4.4 Built `test-copilot-connectivity`

Since Copilot has no catalog and `opencode run` is flaky against it, we test the
Copilot API directly: read the OAuth `access` token from `auth.json`, POST a chat
completion to `https://api.githubcopilot.com/chat/completions` with the
`Copilot-Integration-Id: vscode-chat` header, and report PASS/ERR.

## 5. Diagnosis

- `opencode models` ignores `provider.<p>.models` and is gated only by
  `provider.<p>.whitelist` (provider-relative IDs).
- `blacklist` is unreliable for listing because the catalog fetch is non-deterministic.
- The hub config is universal; overlays are unnecessary for this change.
- Copilot connectivity is fine at the API level; the opencode built-in provider
  just does not expose models the same way.

## 6. Preliminary Assessment

The `whitelist` approach is the only mechanism that produces a stable, correct
listing. Free-tier filtering keeps the test matrix tiny and the result useful.
Copilot is a credential, not a catalog, so it gets a connectivity test rather than
a prune.

## 7. Solution Summary

| Provider | Mechanism | Live listing after |
|---|---|---|
| nvidia | `provider.nvidia.whitelist` (5 PASS text models) | 5 |
| kenari | `provider.kenari.whitelist` (free-only, 7 PASS) | 7 |
| openrouter | `provider.openrouter.whitelist` (free-only, 10 PASS) | 10 |
| github-copilot | `test-copilot-connectivity` skill (API round-trip) | n/a (no catalog) |

All whitelists live in the universal hub `opencode.json`. Backups:
`opencode.json.pre-prune-20260904T122741`, `...T123419`, `...T123702`,
`...T124217`, `...T125519`.

## 8. Verification Plan

- `opencode models nvidia | wc -l` -> 5 (confirmed on Debian and FedoraWSL).
- `opencode models kenari | wc -l` -> 7 (confirmed on Debian and FedoraWSL).
- `opencode models openrouter | wc -l` -> 10 (confirmed).
- `test-copilot-connectivity.sh` -> `gpt-4o` PASS, `gpt-4o-mini` PASS.

One owner-side gotcha that cost a round trip: opencode loads config at session
start. After `--apply`, restart opencode (or open a fresh terminal) before
trusting the new listing. Stale sessions show the old numbers.

## 9. Pending Actions

- **GitHub Copilot as a real provider** (filed as task
  `pending-learn-github-copilot-opencode.md`): determine the model-id format
  opencode's built-in `github-copilot` provider expects, whether a
  `provider.github-copilot` block is needed in `opencode.json`, enumerate the
  working OpenAI model set, and optionally expose a Copilot-backed agent. Right
  now only `gpt-4o` and `gpt-4o-mini` are confirmed against the API; non-OpenAI
  ids return `400 model_not_supported`.

## 10. Recommendations (or: Do Not, Under Any Circumstance, Use blacklist)

1. Keep the three prune skills as the source of truth for provider model hygiene.
   Re-run them periodically; providers rotate models aggressively (NVIDIA retired
   `gpt-oss-120b` the day before this session, 2026-09-03).
2. If you ever feel tempted to edit `provider.<p>.models` to "clean up" the
   listing: don't. It does nothing. Edit the `whitelist`.
3. If you ever feel tempted to use `blacklist`: double-check the catalog fetch is
   deterministic first. In our environment it is not, so `whitelist` wins.
4. Consolidate the three near-identical prune scripts into a shared `_lib.sh`
   once all three are stable. Deferred on purpose so per-provider tuning did not
   cross-contaminate. (Famous last words.)
5. Copilot: treat `test-copilot-connectivity` as the health check; wiring it into
   agents is a separate, future task.

---

Generated by Hy3 Free (Kenari)
