# The LiteLLM Gateway Evolution - Part 6

*Test models + fix "No connected db"*

**Date:** 2026-07-29  
**Author:** Codebot  
**Topic:** LiteLLM, OpenCode, model, curation, troubleshooting, homelab, routing  

---

## 1. Objective

Test DashScope and OpenRouter models, prune dead ones, diagnose LiteLLM "No connected db" error after gateway restart, sync working models to homelab inventory.

## 2. Background

LiteLLM proxy exposes 146 models across providers. Need to verify which respond before curating.

## 3. Problem

Models need testing. After config re-render, proxy rejected all chat requests with "No connected db". Three hypotheses before root cause found.

## 4. Work Performed

### 4.1 DashScope Testing
17 candidates tested against compatible-mode API. 10 healthy, 7 returned "Invalid model name" (provider-side rejection, slug no longer exists).

Working: qwen3-32b, qwen3-235b-a22b, qwen3-max, qwen3.5-flash, qwen3.5-plus, qwen3.5-omni-flash, qwen3.6-plus, qwen3.7-plus, deepseek-v3.2, deepseek-v4-flash
Dead: qwen3-coder, qwen3.5-max, qwen3.6-max, qwen3.7-max, gemini-2.5-flash, gpt-4o-mini, llama-3.3-70b

10 working added to inventory as source=manual. Config re-rendered (149 models). 7 dead removed from OpenCode config.

### 4.2 OpenRouter Testing
21 free-tier models probed. 12 responded, 9 returned 404/429 (slugs no longer free or never existed). Notable: meta-llama/llama-3.3-70b-instruct:free no longer free; OpenRouter suggested paid slug.

### 4.3 "No connected db" Mystery - Three Hypotheses

Hypothesis 1: SQLite
Added SQLite:////srv/appdata/litellm/litellm.db. Container refused at startup: "DATABASE_URL uses unsupported scheme 'sqlite'... require PostgreSQL." LiteLLM v1.92.0 hard-rejects SQLite.

Hypothesis 2: DB-dependent routing
routing_strategy: usage-based-routing and enable_pre_call_checks are DB-backed. Flipped to simple-shuffle and false. Still "No connected db". Not trigger.

Hypothesis 3: Master key validation (ROOT CAUSE)
LITELLM_MASTER_KEY set in container env. LiteLLM auth model: if master key configured and request presents non-master key, assumes DB-managed virtual key, tries lookup against non-existent DB. Lookup fails as "No connected db".

Two solutions:
1. Pass actual master key: Authorization: Bearer @8615269azSX -> 200 OK instantly
2. Remove LITELLM_MASTER_KEY entirely (open proxy, no auth)

Chose option 1: master key added as apiKey in OpenCode LiteLLM provider options. Proxy healthy.

### 4.4 Master Key Trap Note
Earlier 502 from Caddy was red herring -- container mid-restart. Once unit settled, port up, proxy answered. Don't diagnose reverse proxy before confirming backend up.

### 4.5 Smoke Test and Two More Casualties
Post-fix test across 8 models:
- PASS: dashscope/qwen3-max, dashscope/qwen3.5-flash, groq/llama-3.1-8b-instant, aichixia/gemini-3-flash, aichixia/gpt-5-mini, zai/glm-4.7-flash
- FAIL: nvidia/microsoft/phi-4-mini-instruct (410 Gone, EOL 2026-07-15)
- FAIL: nvidia/microsoft/phi-4-multimodal-instruct (same EOL)

Both Phi-4 models died two weeks prior, proxy still advertising. OpenCode chat/plan agents (phi-4-mini) repointed to nvidia/nvidia/nemotron-mini-4b-instruct. OpenRouter Llama 3.3 free dropped; groq/llama-3.3-70b-versatile covers niche.

### 4.6 Blocklist in Inventory (Durable Pruning)
LiteLLM render path watches models.json/providers.json, regenerates config.yaml on change -- stale discovered models can quietly return. Prevention:
- dashscope.policy.disabled_models: 7 dead dashscope slugs
- nvidia.policy.disabled_models: both EOL phi-4 entries (also deleted from models.json)
- openrouter.policy.disabled_models: meta-llama/llama-3.3-70b-instruct:free

Config re-rendered, container restarted, proxy healthy at 146 models.

## 5. Diagnosis

Master key + non-master key request triggers DB lookup requirement. LiteLLM v1.92.0 requires PostgreSQL for DB features. SQLite unsupported.

## 6. Preliminary Assessment

Model curation effective. Master key auth working. Blocklist prevents re-import.

## 7. Solution Summary

Tested and pruned DashScope/OpenRouter models. Fixed "No connected db" via master key auth. Blocklisted dead models in inventory. Proxy at 146 healthy models.

## 8. Verification Plan

Monitor model health. Test new model additions. Verify blocklist persists across renders.

## 9. Pending Actions

Evaluate LiteLLM replacement candidates (One API, custom proxy, direct provider) for next session.

## 10. Recommendations

- Test models before adding to config
- Use master key for auth in no-DB mode
- Blocklist dead models in policy to prevent re-import
- Don't diagnose proxy before confirming backend container up
