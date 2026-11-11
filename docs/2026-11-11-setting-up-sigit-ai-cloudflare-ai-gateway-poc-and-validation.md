# Setting Up sigit-ai: Cloudflare AI Gateway PoC and Validation (or: The Gateway That Lived)

**Date:** 2026-11-11  
**Author:** Codebot  
**Topic:** cloudflare, ai-gateway, litellm, nvidia-nim, aion-labs, workers-ai, poc

---

## 1. Objective

Set up a Cloudflare AI Gateway (`sigit-ai`) as the candidate replacement for non-local LiteLLM traffic, prove basic connectivity for each provider group, and validate streaming and tool/function calling before any client migration.

## 2. Background

The working plan (`TASK-setup-cf-gateway.md`, moved from archive to active for this session) targets a split architecture:

- **Cloudflare AI Gateway** for non-local traffic: NVIDIA NIM, Aion Labs, and Cloudflare Workers AI (`@cf/*`).
- **LiteLLM (kept)** for `local/*` models on `127.0.0.1:8080/v1`, including the embedding model `mxbai-embed-large`.

Key constraints from the plan: only Workers AI is a native AI Gateway provider; NVIDIA NIM and Aion Labs require **Custom Providers (Beta)**. Local loopback models cannot be reached from the Cloudflare edge, so they stay on LiteLLM.

## 3. Problem

Before migrating anything, we needed answers to practical questions the docs alone do not settle cleanly:

- Can custom providers (NVIDIA/Aion) be called successfully with **BYOK** and an authenticated gateway?
- Does the documented `/compat/chat/completions` path work for `custom-{slug}` models, or must we use provider-specific endpoints?
- Do chat, **streaming (SSE)**, and **tool/function calling** all work through the gateway for NVIDIA, Aion, and Workers AI?

## 4. Work Performed

### 4.1 Task recovery and session start

- Located the lost task file in `~/.opencode/plan/archive/TASK-setup-cf-gateway.md`.
- Moved it to `~/.opencode/plan/active/TASK-setup-cf-gateway.md`, registered it in `session-index.json`, and marked it **in progress (Phase 0)**.
- Confirmed `https://ai.home.arpa/v1/models` was reachable and matched the expected LiteLLM inventory baseline.

### 4.2 Decisions recorded

- **Key strategy:** BYOK for NVIDIA + Aion (provider keys stored in Cloudflare; clients send only the gateway Run token via `cf-aig-authorization`).
- **Gateway layout:** single named gateway, `sigit-ai`.
- Dashboard setup completed by the user (steps 1-7): gateway created, authentication/Run token created, custom providers added (`nvidia` -> `https://integrate.api.nvidia.com`, `aionlabs` -> `https://api.aionlabs.ai`), and BYOK keys stored (alias `default`).

### 4.3 Reachability PoC (one model per provider)

| Provider / group | Endpoint form | Result |
|---|---|---|
| NVIDIA custom provider | `/compat/chat/completions` with `model: custom-nvidia/...` | **HTTP 404** |
| NVIDIA custom provider | `/custom-nvidia/v1/chat/completions` (upstream model name) | **HTTP 200 OK** (`pong`) |
| Aion custom provider | `/compat/chat/completions` with `model: custom-aionlabs/...` | **HTTP 404** |
| Aion custom provider | `/custom-aionlabs/v1/chat/completions` (upstream model name) | **HTTP 200 OK** (`pong`) |
| Workers AI (`@cf/*`) | `api.cloudflare.com .../ai/v1/chat/completions` + `cf-aig-gateway-id: sigit-ai` | **HTTP 200 OK** (`pong`) |

Models used for PoC: `nvidia/nemotron-3.5-lightning-30b-a3b`, `aion-labs/aion-3.5-mini`, `@cf/meta/llama-3.1-8b-instruct-fp8-fast`.

### 4.4 Phase 6 validation (streaming and tool calling)

Representative checks were run against the working endpoints for all three groups:

- **Streaming (SSE):** PASS (NVIDIA, Aion, Workers AI).
- **Tool/function calling:** PASS (NVIDIA, Aion, Workers AI).

### 4.5 Inventory check

- **This host (fedoraWSL):** no active config/app found using LiteLLM `ai.home.arpa` for inference (references found were mainly backups, skill/docs, and history).
- **Homelab:** LiteLLM remains part of the AI gateway stack and `kebablazen` integrates with LiteLLM for LLM/embeddings (including litellm-backed store flows and env/key resolution). This is a dependent to confirm before decommissioning non-local entries; embeddings like `local/mxbai-embed-large` remain on LiteLLM per plan.

## 5. Diagnosis

- The gateway itself was healthy and routable (Workers AI worked immediately via REST + `cf-aig-gateway-id`).
- For the **Custom Providers (Beta)** configured here, the **provider-specific endpoint** form worked reliably, while the `/compat/chat/completions` form with `custom-{slug}/...` model naming returned 404. The practical implication is to use provider-specific base paths per custom provider rather than assuming `/compat` for them.
- BYOK worked as intended for custom providers: authenticated gateway calls succeeded with `cf-aig-authorization` and without sending upstream provider `Authorization` headers.

## 6. Preliminary Assessment

`sigit-ai` is viable as the non-local gateway for the tested providers/models:

- **NVIDIA:** `https://gateway.ai.cloudflare.com/v1/<account_id>/sigit-ai/custom-nvidia/v1/chat/completions` (model e.g. `nvidia/nemotron-3.5-lightning-30b-a3b`)
- **Aion:** `https://gateway.ai.cloudflare.com/v1/<account_id>/sigit-ai/custom-aionlabs/v1/chat/completions` (model e.g. `aion-labs/aion-3.5-mini`)
- **Workers AI:** `https://api.cloudflare.com/client/v4/<account_id>/ai/v1/chat/completions` with `cf-aig-gateway-id: sigit-ai`

Basic chat, SSE streaming, and tool calling are validated on representatives. Full migration is not done; this is a successful PoC/validation milestone.

## 7. Solution Summary

- Recovered and reactivated the migration task.
- Created and configured `sigit-ai` with authenticated access, custom providers, and BYOK.
- Established the working request shapes (provider-specific endpoints for NVIDIA/Aion; REST + `cf-aig-gateway-id` for Workers AI).
- Verified streaming and tool calling across all three non-local groups.
- Performed an initial client/dependency inventory (no active local clients; homelab LiteLLM/kebablazen remain relevant).

## 8. Verification Plan

- [x] LiteLLM baseline reachable (`/v1/models` on `ai.home.arpa`).
- [x] Basic chat PoC: NVIDIA, Aion, Workers AI.
- [x] Streaming (SSE): NVIDIA, Aion, Workers AI.
- [x] Tool/function calling: NVIDIA, Aion, Workers AI.
- [ ] Broader model sampling across the full NVIDIA/Aion/`@cf` lists.
- [ ] Confirm homelab dependents (e.g. `kebablazen`, Open WebUI/LiteLLM integration) against non-local vs `local/*` usage.
- [ ] Client canary/migration and rollback rehearsal.

## 9. Pending Actions

- Decide model alias strategy (preserve existing LiteLLM model names vs adopt new names).
- Decide on dynamic routes now vs defer.
- Phase 4: configure aliases/caching/rate limiting/logging and metadata as needed.
- Phase 5: draft and execute canary migration (accounting for different base URLs per provider group vs a single LiteLLM endpoint).
- Phase 7/8: cutover non-local traffic, observe, then partially decommission non-local entries from LiteLLM while keeping `local/*`.

## 10. Recommendations

- Use **provider-specific endpoints** for NVIDIA and Aion custom providers in `sigit-ai`; do not rely on `/compat` for `custom-{slug}` until re-verified.
- Keep LiteLLM as the front door/fallback for `local/*` (and as rollback) until migration proves stable.
- Treat Custom Providers as Beta: re-verify behavior after Cloudflare changes and sample more than one model per group before cutover.
- When resuming work, remember exported shell variables (`ACCOUNT_ID`, `GATEWAY_ID`, tokens) do not survive a WSL/session restart - re-export them (from a protected local source) before running PoC curls.
- Never paste or commit gateway Run tokens, Cloudflare API tokens, or provider keys; BYOK means clients should not carry upstream provider keys for NVIDIA/Aion.

Generated with Iceman Free by OpenCode
