# OpenCode Provider and Fallback Chain - Part 1

*LiteLLM provider connectivity audit*

**Date:** 2026-08-09  
**Author:** Codebot  
**Topic:** LiteLLM, troubleshooting, cleanup, homelab, OpenCode  

---

## 1. Objective

Audit LiteLLM provider connectivity after all provider tests failing.

## 2. Background

Provider connectivity script at ~/.config/opencode/skills/provider-connectivity/run-model-tests.sh reporting PARTIAL or FAIL for every model. Errors pointed to fundamental issues: test script had wrong model names (migrated to OpenRouter paths months ago), NVIDIA base URL incorrect (http://nvidia.api.nvidia.com instead of http://integrate.api.nvidia.com).

## 3. Problem

Master key wrong. 15 providers dead/unused. Need cleanup.

## 4. Work Performed

### 4.1 Master Key Fix
LiteLLM logging 401 Client Error for every request. Test script reading master key from same sops-encrypted litellm.env that LiteLLM loads at startup. Key worked in curl but LiteLLM wasn't using it.

Investigation led to NixOS activation error from June 29: sops-install-secrets failed to copy secrets to /run/secrets/ due to group permission mismatch. LiteLLM container starting with stale secrets (empty litellm.env) while test script reading current correct key.

Fix: master key didn't start with sk- (hard requirement in newer LiteLLM versions). Edited sops file, config rebuild worked.

### 4.2 Provider Cleanup
With working master key, real audit began. Removed 15 providers:
- kenari (replaced by NVIDIA)
- cohere
- PaxSenix
- inceptionlabs
- freetheai
- apizio
- aichixia
- groq
- cerebras
- dashscope
- xiaomimimo
- aihubmix
- fireworks-ai
- Gemini
- streamlake

Each tested, found wanting (paid-only, deprecated, or empty), deleted with models and API keys.

Some providers with valid API keys moved manually to opencode.json for direct access, bypassing LiteLLM proxy (avoid middleman when provider supports native).

Result: 4 providers remaining (NVIDIA, OpenRouter, zai, Ollama), 59 model sources, config actually works.

### 4.3 StreamLake Detour
StreamLake brief false start. Free models deprecated. Paid models (llama-3.1-8b, mimo-v2-free, step-3-flash, mimo-v2-omni) pass through LiteLLM. Whether to keep depends on user topping up balance -- removed for now.

## 5. Diagnosis

Stale sops copy silently broke downstream. sk- prefix required. Test scripts drift. NVIDIA free tier real and reliable.

## 6. Preliminary Assessment

Provider audit complete. Working config with 4 providers.

## 7. Solution Summary

Fixed master key (sk- prefix). Removed 15 dead providers. Moved valid direct-access providers to opencode.json. 4 providers, 59 models operational.

## 8. Verification Plan

Test all remaining provider models. Monitor for deprecations.

## 9. Pending Actions

Monitor StreamLake if balance topped up. Periodic provider audits.

## 10. Recommendations

- Always check startup path: stale sops copy breaks everything downstream
- sk- prefix matters: even if key works in curl, LiteLLM requires it
- Test scripts drift: model names change, base URLs shift, providers disappear. Periodic audits save time
- NVIDIA free tier is real: nemotron-mini-4b-instruct passes reliably, capable default for personal AI gateway
