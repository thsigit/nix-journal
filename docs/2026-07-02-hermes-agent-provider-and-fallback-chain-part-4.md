# Hermes Agent Provider and Fallback Chain - Part 4

*Switching Providers and Picking a Fallback Chain*

**Date:** 2026-07-02  
**Author:** Codebot  
**Topic:** Hermes Agent, OpenRouter, Google, fallback-chain, free-models  

## 1. Objective

Configure Hermes Agent with Google AI Studio as primary provider, establish multi-layer fallback chain using OpenRouter free models and local Ollama, and remove stale Fireworks AI provider.

## 2. Background

Hermes Agent was pinned to Fireworks AI (accounts/fireworks/models/glm-5p2) with leftover base_url pointing to local Ollama. Auth pool had OpenRouter and Gemini credentials. Need live OpenRouter free model list, sensible default, and robust fallback chain.

## 3. Problem

Existing fallback chain had single redundant entry: openrouter/free pointing to same provider (no real fallback). Leftover model.base_url would misroute OpenRouter requests. Need to identify live free models with sufficient context (>=64K) and build 8-layer chain.

## 4. Work Performed

### 4.1 Configuration Audit

- Read config.yaml: found stale model.base_url pointing to local Ollama
- Auth pool: OpenRouter and Gemini credentials present
- No new key wiring required

### 4.2 OpenRouter Free Model Discovery

- Queried live OpenRouter models endpoint
- 22 free models returned
- Filtered for context >= 64K (Hermes Agent minimum)
- Sorted by context length, presented recommendation tiers:

| Tier         | Models                                                                                     | Context        | Notes               |
| ------------ | ------------------------------------------------------------------------------------------ | -------------- | ------------------- |
| Best Overall | qwen/qwen3-coder:free, nousresearch/hermes-3-llama-3.1-405b:free, openai/gpt-oss-120b:free | 1M, 131K, 131K | Strong all-rounders |
| Workhorses   | meta-llama/llama-3.3-70b-instruct, poolside/laguna-m.1                                     | 131K           | Reliable            |
| Code-Focused | qwen/qwen3-coder, cohere/north-mini-code                                                   | 1M, 256K       | Coding optimized    |

- Selected: qwen/qwen3-coder:free (1M context, 480B params, coding + general)

### 4.3 Fallback Chain Construction

Hermes Agent proposed 8-layer chain (written as {model, provider} dicts matching config.yaml schema):

1. OpenRouter / qwen/qwen3-coder:free (primary)
2. OpenRouter / nousresearch/hermes-3-llama-3.1-405b:free (131K, 405B)
3. OpenRouter / meta-llama/llama-3.3-70b-instruct:free (131K, 70B)
4. OpenRouter / openai/gpt-oss-120b:free (131K, 120B)
5. Google / gemini-2.0-flash (free tier)
6. Google / gemini-2.5-flash (free tier)
7. fireworks-ai / accounts/fireworks/models/glm-5p2 ($6 trial)
8. ollama-launch / qwen2.5:3b (local)

### 4.4 Verification

- Verified YAML list format against existing config.yaml
- Commands ready for user to paste (Hermes Agent config set)
- Old single-entry fallback still active until commands executed

## 5. Diagnosis

Stale base_url would break OpenRouter routing. Single redundant fallback provided no resilience. Live model discovery essential for free tier volatility. Context filtering (>=64K) eliminates incompatible models.

## 6. Preliminary Assessment

Fallback chain designed but not yet applied. Fireworks trial credits still available but slated for removal. Local Ollama provides ultimate fallback.

## 7. Solution Summary

- Audited config.yaml and auth pool
- Discovered 22 live OpenRouter free models
- Filtered for >=64K context, selected qwen/qwen3-coder:free primary
- Constructed 8-layer fallback chain across OpenRouter, Google, Fireworks, Ollama
- Prepared Hermes Agent config set commands for user execution

## 8. Verification Plan

- Paste config commands and verify with Hermes Agent chat probe
- Test auto-advance on HTTP 429
- Confirm chain falls through to Google, then Fireworks, then Ollama

## 9. Pending Actions

- Execute Hermes Agent config set commands
- Verify fallback chain with live probe
- Remove Fireworks after trial exhaustion

## 10. Recommendations

- Regularly refresh OpenRouter free model list (high volatility)
- Maintain context >=64K filter for Hermes Agent compatibility
- Keep local Ollama as final fallback tier
- Remove stale base_url before provider switches