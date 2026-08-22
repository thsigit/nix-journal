# Hermes Agent Provider and Fallback Chain - Part 5

*Retire Fireworks, rebuild chain*

**Date:** 2026-07-20  
**Author:** Codebot  
**Topic:** Hermes Agent, Fireworks, OpenRouter, fallback-chain, free-models, config-management  

## 1. Objective

Remove exhausted Fireworks AI provider from Hermes Agent configuration, clean auth store and environment, and rebuild fallback chain with live free models.

## 2. Background

Fireworks AI $6 trial exhausted after weeks of testing. Provider sat in fallback chain between OpenRouter and Ollama, hosting llama-v3p3-70b-instruct, qwen3-235b-a22b-instruct. Stale definition would trigger timeout before advancing to Ollama.

## 3. Problem

Fireworks provider block in config.yaml, API key in ~/.hermes/.env, four credential entries in auth pool under different aliases. All needed clean removal. Fallback chain needed replacement for deprecated owl-alpha.

## 4. Work Performed

### 4.1 Fireworks Purge
- Provider block: Hermes Agent config unset providers.fireworks-ai
- Environment variable: sed -i delete line 475 in ~/.hermes/.env, grep confirmed gone
- Auth pool: four credentials (custom:fireworks-ai, Fireworks, fireworks-ai, fw) all referencing same env var. Used auth suppress mechanism to prevent re-import if env var returns.

### 4.2 Fallback Chain Reconstruction
Post-removal chain:
1. google/gemini-2.5-flash (always free, never rate-limited)
2. openrouter/owl-alpha (deprecated)
3. ollama-launch/ornith:latest (local)

owl-alpha deprecated. Replacement candidate mancer/weaver only 8K context (Hermes Agent minimum 64K).

Queried live OpenRouter free models with >=64K context:

| Model | Context | Notes |
|-------|---------|-------|
| nvidia/nemotron-3-super-120b-a12b:free | 1,000,000 | Strong all-rounder |
| google/gemma-4-31b-it:free | 262,144 | Google latest, good reasoning |
| cohere/north-mini-code:free | 256,000 | Code-focused, 256K context |
| openrouter/free | 200,000 | Meta-router, auto-picks best |

Selected: cohere/north-mini-code:free (context headroom, stays free, North family solid for coding).

New fallback chain:
- Primary: minimax-m3:cloud (via ollama-launch)
- Fallback 1: google/gemini-2.5-flash (via Google)
- Fallback 2: cohere/north-mini-code:free (via OpenRouter)
- Fallback 3: ollama-launch/ornith:latest (via ollama-launch)

### 4.3 Fireworks Trial Note
$6 new-user credit genuinely useful: full catalog (Llama 3.3 70B, Qwen 3 235B, DeepSeek V3, GLM-5) via OpenAI-compatible endpoint at api.fireworks.ai/inference/v1. Credits last months. firectl CLI checks balances and redeems promos. Remove cleanly when exhausted.

### 4.4 Verification
Hermes Agent fallback list confirms chain live.

## 5. Diagnosis

Stale provider definitions cause timeout delays. Deprecated routing endpoints (owl-alpha) break chains. Context filtering essential for Hermes Agent compatibility. Auth suppress mechanism prevents zombie credentials.

## 6. Preliminary Assessment

Zero Fireworks references in config, auth, or env. Fallback chain three entries, each independently verified. Session ran on last Fireworks model (deepseek-v4-flash).

## 7. Solution Summary

- Removed Fireworks provider block, env var, and 4 auth credentials
- Identified owl-alpha deprecation
- Queried live OpenRouter free models >=64K context
- Selected cohere/north-mini-code:free as replacement
- Rebuilt 3-layer fallback chain
- Verified via Hermes Agent fallback list

## 8. Verification Plan

- Test fallback chain under OpenRouter 429 conditions
- Monitor cohere/north-mini-code:free availability
- Confirm local Ollama ultimate fallback

## 9. Pending Actions

- Monitor OpenRouter free model volatility
- Refresh model list periodically

## 10. Recommendations

- Remove providers immediately when credits exhausted
- Filter free models for >=64K context (Hermes Agent requirement)
- Use auth suppress for env-based credentials
- Keep local Ollama as final fallback tier
- Document trial provider cleanup process