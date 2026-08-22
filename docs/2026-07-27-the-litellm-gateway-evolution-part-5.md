# The LiteLLM Gateway Evolution - Part 5

*Model catalog expansion + OpenCode*

**Date:** 2026-07-27  
**Author:** Codebot  
**Topic:** LiteLLM, OpenCode, provider configuration  

---

## 1. Objective

Expand LiteLLM homelab gateway from curated models to full ~200 model catalog, wire all models into OpenCode /models picker, discover OpenCode provider limitation.

## 2. Background

LiteLLM proxy exposing models from multiple providers. Need to integrate with OpenCode agent framework.

## 3. Problem

OpenCode built-in openai provider ignores baseURL option for model discovery and API calls. Setting baseURL: https://litellm.home.arpa/v1 doesn't work -- requests go to platform.openai.com.

## 4. Work Performed

### 4.1 OpenCode Provider Limitation
Custom OpenAI-compatible endpoints (like LiteLLM) MUST use @ai-sdk/openai-compatible npm package. Models won't auto-discover -- each must be listed explicitly in opencode.json. openai provider ID reserved for OpenAI itself.

### 4.2 Model Catalog Expansion
Added all ~200 models from LiteLLM proxy to opencode.json:

| Provider | Count | Notes |
|----------|-------|-------|
| NVIDIA | ~85 | Llama, Qwen, Mistral, Gemma, Nemotron, Flux |
| OpenRouter | 21 | Free-tier only |
| Apizio | 13 | DeepSeek, Gemini, GPT-4o, Qwen |
| Aichixia | 11 | Free-tier |
| Dashscope | 18 | Alibaba Cloud Qwen |
| Freetheai | 16 | Free-tier |
| InceptionLabs | 12 | Mercury-2, DeepSeek, Gemini |
| PaxSenix | 37 | Claude, GPT-5, GLM-5, Kimi |
| Xiaomimimo | 16 | Free-tier |
| Groq | 3 | Llama |
| Cerebras | 3 | GLM, GPT-OSS, Gemma |
| ZAI | 2 | GLM-4.5-flash, GLM-4.7-flash |
| Cohere | 1 | North Mini Code |
| Ollama | 1 | Local Llama 3.2 |
| Kenari | 1 | Free tier |

### 4.3 New Agents Created
| Agent | Model | Purpose |
|-------|-------|---------|
| build | zai/glm-4.7-flash | Build and development |
| plan | zai/glm-4.5-flash | Planning, architecture, design |

Accessible via @build and @plan.

### 4.4 Auth Cleanup
Removed duplicate provider entries from auth.json:
- openai: removed (using LiteLLM proxy)
- kenari: removed (using LiteLLM proxy)
Remaining: github-copilot, Google, litellm.

### 4.5 Legacy Directory Cleanup
~/.opencode was legacy with duplicate node_modules:
- ~/.opencode/node_modules: stale install from old setup
- ~/.config/opencode/node_modules: active install
Renamed ~/.opencode/node_modules -> ~/.opencode/node_modules.old

## 5. Diagnosis

OpenCode's provider architecture requires explicit model listing for custom endpoints. No auto-discovery. Legacy directories accumulate silently.

## 6. Preliminary Assessment

Full catalog integrated. Provider limitation understood and worked around.

## 7. Solution Summary

200+ models added to opencode.json. Two new agents. Auth cleaned. Legacy dir handled.

## 8. Verification Plan

Test model selection via /models. Verify @build and @plan agents functional.

## 9. Pending Actions

Periodic catalog updates as providers change. Monitor for OpenCode provider API changes.

## 10. Recommendations

Use @ai-sdk/openai-compatible for custom endpoints. Explicitly list all models. Audit ~/.opencode vs ~/.config/opencode periodically. Keep auth.json minimal.
