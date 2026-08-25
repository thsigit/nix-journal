# OpenCode Configuration Evolution - Part 4

*Multi-provider config: kenari, freetheai, aihubmix*

**Date:** 2026-08-09  
**Author:** Codebot  
**Topic:** OpenCode, LiteLLM, config, audit, homelab  

## 1. Objective

Configure the user's OpenCode installation (`~/.config/opencode/opencode.jsonc` and `~/.local/share/opencode/auth.json`) to consolidate several AI providers, restrict model availability to free tiers where applicable, and integrate custom providers absent from the models.dev registry.

## 2. Background

OpenCode sources provider catalogs from the models.dev registry and credentials from `auth.json`. `opencode providers list` reports credentials, whereas the interactive model picker only surfaces providers that expose known models. Providers not registered on models.dev therefore require explicit configuration.

## 4. Work Performed

### 4.1 Kenari - Free-Model Restriction
Applied a `blacklist` of 32 non-free model IDs, retaining six `:free` variants (`kimi-k2-7-code:free`, `mimo-v2-5:free`, `deepseek-v4-flash:free`, `glm-4-7-flash:free`, `nemotron-3-super-120b-a12b:free`, `kimi-k2-6:free`). Additionally registered the undocumented `kenari-free` route model (verified against `https://kenari.id/v1`; successfully routed to `deepseek-v4-flash:free`), defined under `provider.kenari.models`.

### 4.2 freetheai - Custom Provider Integration
Diagnosed that freetheai was absent from models.dev, resulting in a credential with zero models and no picker entry. Fetched the live catalog from `https://api.freetheai.xyz/v1/models` using the stored key (HTTP 200), and defined `provider.freetheai` with `npm: @ai-sdk/openai-compatible`, `api: https://api.freetheai.xyz/v1`, and all 50 chat-capable model aliases. Chat completion smoke test passed.

### 4.3 aichixia - Deferred
Credential added to `auth.json`. Verification blocked: the service reported **under maintenance**, and the API path returned Cloudflare 403 (WAF bot protection) for both curl and Node/undici clients. Integration postponed pending service availability.

### 4.4 dashscope - Removed
API key rejected with HTTP 401 `invalid_api_key` on both native and compatible-mode endpoints. Confirmed service shutdown (site notice: `"[service closed on 2026-08-01]"`). Credential deleted.

### 4.5 Provider Cleanup
Removed non-functional or unwanted credentials from `auth.json`: **groq**, **cerebras**, **xiaomi**, **dashscope**. None had config entries in `opencode.jsonc`.

### 4.6 aihubmix - Free-Model Restriction
Identified that the provider uses a `-free` suffix convention (four models at zero cost). Applied a `blacklist` of 63 paid model IDs, retaining `xiaomi-mimo-v2.5-free`, `xiaomi-mimo-v2.5-pro-free`, `coding-minimax-m2.7-free`, and `coding-glm-5.1-free`.

## 5. Diagnosis

`opencode.jsonc` now declares three providers: `kenari`, `freetheai`, `aihubmix`. `auth.json` holds credentials for `kenari`, `inception`, `freetheai`, `aichixia`. All configuration validated as syntactically correct JSON.

## 6. Preliminary Assessment

- Restart OpenCode to load updated configuration.
- Retry aichixia integration after maintenance concludes.
- Reconcile aihubmix top-up status before enabling paid models.

## 7. Solution Summary

For future provider onboarding, first consult the models.dev registry; only register custom providers via `provider.*` with explicit `npm`, `api`, and `models` definitions when absent. Confirm API reachability and key validity prior to catalog capture, as several providers employ WAF bot protection that blocks server-side clients.

## 8. Verification Plan

1. Restart OpenCode to load the updated opencode.jsonc and auth.json.
2. Run opencode providers list -- confirm kenari, freetheai, aihubmix appear with correct model counts.
3. Test each provider with a smoke query:
   - kenari: verify :free models respond.
   - freetheai: verify all 50 aliases respond.
   - aihubmix: verify -free models respond.
4. Check that inception and aichixia credentials exist in auth.json but do not appear in the picker (no models defined).

## 9. Pending Actions

- Restart OpenCode and execute verification plan above.
- Monitor aichixia status; retry integration when maintenance concludes.
- Reconcile aihubmix credit balance before considering paid model enablement.
- If any provider exhibits WAF blocks, document and add to provider-specific notes in the skill.

## 10. Recommendations

1. Registry-first onboarding: Always check models.dev before registering custom providers; only use provider.* with explicit npm, api, models when absent.
2. Validate before capture: Confirm API reachability and key validity before fetching catalogs -- several providers employ WAF bot protection that blocks server-side clients.
3. Free-tier restriction via blacklist: For providers with mixed free/paid models, apply a blacklist of paid IDs rather than whitelisting free ones; easier to maintain as catalogs grow.
4. Credential hygiene: Remove unused credentials from auth.json immediately after provider deprecation (e.g., dashscope, groq, cerebras, xiaomi).
5. Document WAF behavior: Record which providers block server-side clients (freetheai, aichixia) so future integrations can plan for browser-based or headed automation.
6. Version-pin provider npm packages: Use @ai-sdk/openai-compatible@X.Y.Z to avoid breaking changes in the compatibility layer.

Generated with Ox Alpha Free (OpenCode)
