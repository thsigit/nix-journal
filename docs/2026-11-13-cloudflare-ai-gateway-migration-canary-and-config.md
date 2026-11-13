# Cloudflare AI Gateway Migration Follow-Up (or: The Follow-Up That Actually Checked Its Work)

**Date:** 2026-11-13  
**Author:** Codebot  
**Topic:** cloudflare, ai-gateway, litellm, workers-ai, migration, canary, tokens

---

## 1. Objective

Continue the migration of non-local traffic from LiteLLM to the Cloudflare AI Gateway `sigit-ai` (account `54d5812cf8ec517010c97e8e24b33b46`), following the successful PoC documented in "Setting Up sigit-ai: Cloudflare AI Gateway PoC and Validation" (2026-11-11). Goal for this session: apply the gateway feature configuration (cache, rate limiting, retries, spend cap), route the `cloudflare/@cf/*` (Workers AI) model group through the gateway via the LiteLLM proxy path, and verify routing empirically rather than asserting it.

## 2. Background

Part 1 proved basic connectivity and validated streaming/tool-calling for NVIDIA NIM, Aion Labs, and Workers AI through `sigit-ai`. It left open: model alias strategy, dynamic routes, Phase 4 feature config, and a client canary. The work plan lived in `TASK-cf-gateway-migration-followup.md`.

A recurring theme this session: the prior task file contained several items marked complete that were not actually verified. The session's first job was to audit those claims against primary sources (live LiteLLM config, `systemctl`, Cloudflare API) and correct them.

## 3. Problem

Three classes of problem surfaced:

- **Unverified task state.** Several `[x]` marks from the earlier session (by a different model) asserted completions that did not survive a read-back: the homelab inventory was wrong (it had only grepped `/srv/repo/nix-lab`, never `/srv/repo/kebablazen`), and the "embeddings stay on LiteLLM" premise was false (the live LiteLLM `/v1/models` served 38 chat models and zero embeddings).
- **Token model was confused.** The gateway needed three distinct token scopes (config Read/Edit, gateway Run, Workers AI Read), but they had been overloaded onto one variable and one was deleted. Stored tokens were also stale (`Invalid API Token`).
- **Free-LLM constraint.** The user's stated goal is to use only free LLMs, so the gateway settings had to prevent paid overage and bound quota, not merely observe it.

## 4. Work Performed

### 4.1 Audit and correction of prior task state

Read-only inspection (no homelab changes) established the real state:

- `/srv/repo/kebablazen` does consume LiteLLM (`litellm_env.py` resolves `LITELLM_MASTER_KEY`; `store/build.py`, `search.py`, `topup.py`, `journal.py`, `mcp_server.py`, `cli.py` all call it). Its defaults are non-local: `KEBAB_LLM_MODEL=nvidia/nvidia/nemotron-3-super-120b-a12b`, `KEBAB_EMBED_MODEL=nvidia/nvidia/llama-nemotron-embed-vl-1b-v2`.
- Live LiteLLM `/v1/models` returns exactly 38 models (NVIDIA 11, `cloudflare/@cf/*` 17, Aion 6, `local/*` 4 chat) and no embedding model. `local/mxbai-embed-large` exists only in the first-boot Nix seed, not the live config.
- Running inference consumers on homelab are `open-webui.service` (`OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`) and the `kebablazen` CLI/library. `litellm-admin-api`, `litellm-stats-api`, `litellm-stats-writer` touch config/usage only.

These findings were written back into the task file, flipping the false `[x]` marks to reopened/verified states.

### 4.2 Token model cleanup

Cloudflare token permissions were clarified: `AI Gateway Read/Edit` (config), `AI Gateway Run` (custom-provider inference via `cf-aig-authorization`), and `Workers AI Read` (the `@cf/*` REST path) are three separate permission groups, not one. The user recreated the deleted Run token and added a dedicated `CF_WORKERS_AI_TOKEN` (Workers AI Read/Write) on homelab.

The single source of truth for homelab secrets is the SOPS-encrypted `/srv/repo/nix-lab/secrets/providers.env`, which decrypts on rebuild into `/run/secrets/providers.env` (tmpfs, lost on reboot). Direct edits to the live file vanish on reboot. The session also resolved a Nix flake `NAR hash mismatch` on the `litellm-cli` path input by re-locking it (`nix flake lock --update-input litellm-cli`) and pinning the floating `opencode` input to `github:anomalyco/opencode/v1.19.5`. After a successful `nixos-rebuild switch`, the live `providers.env` carried `CF_API_TOKEN`, `CF_AIG_RUN_TOKEN`, and `CF_WORKERS_AI_TOKEN`.

### 4.3 Gateway feature configuration (applied and verified)

Using an `AI Gateway - Read/Edit` token, the update API (`PUT /accounts/{account_id}/ai-gateway/gateways/sigit-ai`) was called. Important API reality discovered: `cache_ttl`, `rate_limiting_*`, and `retry_*` are gateway-global only (no per-provider split), while `spend_limits.rules[].provider` supports per-provider filtering.

Applied settings (read-back confirmed):

| Setting | Value |
|---|---|
| `cache_ttl` | 86400 (24h) |
| `rate_limiting_limit` / `interval` / `technique` | 60 / 60s / sliding (60 req/min gateway-wide) |
| `retry_max_attempts` / `retry_backoff` / `retry_delay` | 2 / exponential / 1000ms |
| `spend_limits` | enabled; one rule: provider `workers-ai`, `limit=0.01`, `limitType=cost`, `window=2592000` (30d) |

Per-provider spend caps for `nvidia` and `aionlabs` were rejected by the API ("Unknown provider in spend_limits rule"). Root cause: the gateway is `byok_only=true`, so BYOK custom providers incur no Cloudflare cost and have no spend dimension to cap. Only `workers-ai` (postpaid, Cloudflare-billed) is spend-limitable. The global 60/min rate limit still bounds the custom providers.

### 4.4 Workers AI routing to sigit-ai (verified)

A direct REST call to `api.cloudflare.com/.../ai/v1/chat/completions` with `Authorization: Bearer <Workers AI Read token>` plus `cf-aig-gateway-id: sigit-ai` returned a 200 completion for `@cf/meta/llama-3.1-8b-instruct-fp8-fast`. The response reported `neurons` in usage, confirming postpaid Workers AI billing. This proved the `@cf/*` REST path needs Workers AI Read, not AI Gateway Run.

### 4.5 `@cf/*` canary via the LiteLLM proxy (chosen shape A)

Rather than editing each client, the LiteLLM proxy path was chosen: the 17 `cloudflare/@cf/*` entries in the live `/srv/appdata/litellm/config.yaml` already pointed at the Workers AI REST endpoint but bypassed the gateway (no `cf-aig-gateway-id` header). The plan was to add `extra_headers: {cf-aig-gateway-id: sigit-ai}` and repoint `api_key` to `os.environ/CF_WORKERS_AI_TOKEN`.

Applied steps:

1. Backed up the live config: `/srv/appdata/litellm/config.yaml.bak-20261113-173522`.
2. Repointed all 17 `@cf/*` entries' `api_key` from `CF_API_TOKEN` to `CF_WORKERS_AI_TOKEN`.
3. Inserted `extra_headers: cf-aig-gateway-id: sigit-ai` (6-space / 8-space indent) after each `api_base` line within `@cf` entries. Counts confirmed: 17 `extra_headers` blocks, 17 `CF_WORKERS_AI_TOKEN` references, 0 `@cf` entries still on `CF_API_TOKEN`.
4. Restarted `litellm.service` (active after restart).

### 4.6 Empirical routing verification

The proof that traffic now flows through `sigit-ai` came from the gateway-issued response header, not from a dashboard claim:

```
llm_provider-cf-aig-cache-status: MISS    (first, unique prompt)
llm_provider-cf-aig-cache-status: HIT     (identical prompt, cache served)
llm_provider-cf-aig-cache-status: MISS    (new prompt)
```

That header is emitted by Cloudflare AI Gateway, not LiteLLM or Workers AI, and the MISS-to-HIT transition on an identical request proves the 24h cache (and therefore the gateway) is in the path. Clients (`open-webui`, `kebablazen`) required zero changes because they still call `127.0.0.1:4000`.

## 5. Diagnosis

- Unverified task state is a real failure mode when one model marks work done without reading the underlying system. The fixes here were grounded in `curl` against live LiteLLM, `systemctl`, and the Cloudflare config API, not memory.
- The "per-provider rate/cache" plan was infeasible: those fields are gateway-global. The spend cap is the only per-provider knob, and only for Cloudflare-billed providers.
- The `@cf/*` group is the lowest-risk canary precisely because it needed no client edit and no upstream key change - only a LiteLLM header injection.

## 6. Preliminary Assessment

`sigit-ai` now controls the Workers AI model group end-to-end (cache, rate limit, retries, spend cap), and the routing is empirically proven. The NVIDIA/Aion `custom-*` group remains on LiteLLM directly and is the next canary. The open question from Part 1 - whether `kebablazen` and Open WebUI can be cut over, given their non-local defaults and the absence of any embedding model on LiteLLM - is still unresolved and now documented with evidence.

## 7. Solution Summary

- Audited and corrected prior task state against primary sources.
- Established a clean three-token model and a SOPS-backed single source of truth; resolved the Nix flake hash mismatch and pinned `opencode/v1.19.5`.
- Applied and read-back-verified gateway global config (cache 24h, 60/min, 2 retries, $0.01/30d Workers AI spend cap).
- Verified the `@cf/*` REST path requires Workers AI Read, not Gateway Run.
- Executed the `@cf/*` canary via the LiteLLM proxy (17 entries) and proved routing with `cf-aig-cache-status` (MISS -> HIT -> MISS).
- Carried all remaining work into a new task file (`TASK-cf-gateway-migration-followup-2.md`) and archived the original.

## 8. Verification Plan

- [x] Gateway config read-back matches applied values.
- [x] `@cf/*` routes through `sigit-ai` (cache header evidence).
- [ ] NVIDIA/Aion `custom-*` canary via LiteLLM proxy with `CF_AIG_RUN_TOKEN` + `cf-aig-authorization`.
- [ ] Resolve the `kebablazen`/Open WebUI non-local defaults + missing embedding model before any cutover of those consumers.
- [ ] Broader model sampling across NVIDIA/Aion/`@cf/*` (Phase 6).
- [ ] Decide model aliases (feasibility: aliases are `custom/<alias>` on `/compat`, which 404s for custom providers; likely only `@cf/*` is aliasable).
- [ ] Logging/Logpush + per-request `cf-aig-metadata` for user attribution (Phase 4 remainder).
- [ ] Cutover, observe 1-2 weeks, then partially decommission non-local LiteLLM entries.

## 9. Pending Actions

- Route NVIDIA/Aion `custom-*` group through `sigit-ai` (next canary).
- Resolve the embedding-source question for `kebablazen` (no embedding model currently served by LiteLLM).
- Decide model alias strategy and finish Phase 4 logging/metadata.
- Execute cutover, observation, and partial decommission (Phases 7-8).

## 10. Recommendations

- Keep the LiteLLM proxy as the migration front door: it gives a single cutover/rollback point and leaves clients untouched.
- Treat any `[x]` in a task file as a claim to be proven, not a fact - read the underlying system before marking done (this session reversed three false completions).
- Keep the three Cloudflare token scopes separate (config Read/Edit, gateway Run, Workers AI Read); never overload one variable, and never let a deleted token strand gateway config or inference access.
- Remember that `/run/secrets/providers.env` is tmpfs and rebuilt from the SOPS source on every boot - edit the encrypted source, not the live file.
- Hold the `@cf/*` rollback ready: `config.yaml.bak-20261113-173522` + `litellm.service` restart restores direct Workers AI.

Generated with Hy3 (Free) by Kenari
