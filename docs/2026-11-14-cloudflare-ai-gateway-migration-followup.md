---
nav:
  series: "The LiteLLM Gateway Evolution"
  part: ?
---

# Cloudflare AI Gateway Migration Follow-up — Cutover Complete

**Date:** 2026-11-14  
**Author:** Codebot  
**Topic:** LiteLLM, Cloudflare AI Gateway, NixOS, homelab, routing, observability

## 1. Objective

Finish Cloudflare AI Gateway `sigit-ai` migration from `@cf/*` canary to full non-local routing. Non-local models route via `sigit-ai`; `local/*` stays direct on LiteLLM. Consumer defaults aligned, dead model pruned, embeddings restored locally, and Phase 8 decommission closed by architecture.

## 2. Background

Part 1 completed `@cf/*` canary with gateway global settings applied. Shape A retained: LiteLLM remains single client-facing endpoint, non-local traffic traverses Cloudflare AI Gateway. BYOK for NVIDIA and AionLabs via custom providers, Workers AI via `api.cloudflare.com/ai/v1`.

## 3. Problem

Open decisions remained: kebablazen / open-webui defaults pointed at models not live on LiteLLM; NVIDIA/Aion not yet gateway-routed; caching behaviour unclear; dead model `nvidia/google/diffusiongemma-26b-a4b-it` 410 Gone; embeddings unavailable; model aliases feasibility; Phase 8 decommission semantics; token scopes confusing.

## 4. Work Performed

### 4.1 Consumer defaults alignment
* kebablazen chat default → `cloudflare/@cf/meta/llama-3.1-8b-instruct-fp8-fast`
* open-webui `DEFAULT_MODELS` → `cloudflare/@cf/openai/gpt-oss-120b`
* `nixos-rebuild switch` applied, env verified

### 4.2 NVIDIA/Aion canary
* 11 `nvidia/*` → `gateway.ai.cloudflare.com/v1/<acct>/sigit-ai/custom-nvidia/v1`
* 6 `aionlabs/*` → `.../custom-aionlabs/v1`
* `api_key` + `extra_headers.cf-aig-authorization` = `os.environ/CF_AIG_RUN_TOKEN`
* LiteLLM restarted, routing verified via `llm_provider-cf-aig-cache-status` and trace id

### 4.3 Validation
* Full inventory: 37/38 chat models working. `diffusiongemma` pruned.
* `local/*` 4/4 present on llama.cpp server, never gateway-routed.
* Caching: gateway default TTL not effective. Per-request `cf-aig-cache-ttl` works for Workers AI, custom-nvidia, custom-aionlabs. MISS,MISS,HIT confirmed.
* `/compat` + custom providers → 404, aliases dropped.

### 4.4 Embeddings restored
* Added `local/mxbai-embed-large` embedding entry, api_base `http://127.0.0.1:8080/v1`, 1024-dim.
* kebablazen embed defaults repointed from `nvidia/nvidia/llama-nemotron-embed-vl-1b-v2` to `local/mxbai-embed-large` in `services/ai.py`, `litellm_env.py`, `kebab_kb_runner.sh`, `KB-HANDOFF.md`.
* Verified via LiteLLM POST /v1/embeddings → 1024 dims.

### 4.5 Tokens and scope clarification
* `CF_AIG_RUN_TOKEN` — AI Gateway Run token, used for custom provider auth.
* `CF_WORKERS_AI_TOKEN` — Cloudflare API token, Account → Workers AI: Edit.
* `CF_API_TOKEN` valid and active, account-owned; verify at `/accounts/{id}/tokens/verify`, not `/user/tokens/verify`. Valid-but-narrow, no AI Gateway scope.
* `CF_AIG_LOG_TOKEN` kept for future log reading.

### 4.6 Phase 8
Closed as satisfied by architecture. LiteLLM remains front door; decommissioning LiteLLM would remove models, not remove a hop. Observation window 2026-11-14 → 2026-11-28.

## 5. Diagnosis

Default caching expectation was wrong; per-request header is the reliable control. Custom providers do cache. Account-owned API tokens fail user-level verify, causing false “invalid token” reports. Model id prefix must be single-prefix for custom providers.

## 6. Preliminary Assessment

Cutover complete. 38 chat models served, embeddings restored locally, consumer defaults aligned, routing verified with gateway headers. Rollbacks preserved via `config.yaml.bak-*`. No client changes required.

## 7. Solution Summary

* Non-local traffic → Cloudflare AI Gateway `sigit-ai`; local stays direct.
* LiteLLM config updated, service restarted, `nixos-rebuild switch` applied.
* Dead model pruned, embedding entry added, kebablazen defaults updated.
* Tokens scoped to least privilege; `CF_AIG_RUN_TOKEN` for gateway auth, `CF_WORKERS_AI_TOKEN` for Workers AI.
* Logging/Logpush deferred to separate task for 2-week data accumulation.
