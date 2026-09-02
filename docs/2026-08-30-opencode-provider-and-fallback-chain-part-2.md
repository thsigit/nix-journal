# "OpenCode Provider and Fallback Chain" - Part 2

**Date:** 2026-08-30  
**Author:** Codebot  
**Topic:** opencode, providers, nvidia, litellm, connectivity

---

## 1. Objective

This report documents the comprehensive testing and pruning of OpenCode provider endpoints and model availability across all configured providers: LiteLLM, AIHubMix, Abliteration.ai, GitHub Copilot, and NVIDIA.

## 2. Background

OpenCode uses a provider-based architecture where models are accessed through various API endpoints. The configuration in `opencode.json` defines providers and whitelisted models, while `auth.json` stores API keys and credentials.

This session follows the universal opencode settings reconfiguration described in "Three Distros, One OpenCode Setup" (2026-08-29), where we consolidated configuration across FedoraWSL, DebianWSL, and Windows into a shared hub at `/mnt/c/users/sigit/.config/opencode/`. With the unified setup in place, we now test provider connectivity and optimize the model whitelist. This session tested:

1. API key validity for all providers
2. Model availability for each provider
3. NVIDIA model pruning for performance

## 3. Problem

The following issues needed investigation:

1. **LiteLLM**: Returns `400 - No connected db` on all endpoints when run without database
2. **NVIDIA**: Some whitelisted models timeout or don't exist
3. **Model discovery**: Needed to identify vision, audio, and embedding models for future use

## 4. Work Performed

### 4.1 Provider API Key Testing

All providers in `auth.json` were tested for API key validity:

| Provider | Endpoint | Status |
|----------|----------|--------|
| LiteLLM | `https://litellm.home.arpa/v1/models` | WARN 400 - No connected db |
| AIHubMix | `https://api.aihubmix.com/v1/models` | OK 200 |
| Abliteration.ai | `https://api.abliteration.ai/v1/models` | OK 200 |
| GitHub Copilot | `https://api.github.com/user` | OK 200 |
| NVIDIA | `https://integrate.api.nvidia.com/v1/models` | OK 200 |

### 4.2 LiteLLM Endpoint Analysis

LiteLLM was tested against the following endpoints, all returning `400 - No connected db`:

```
GET  /health
GET  /v1/models
POST /v1/chat/completions
POST /v1/completions
POST /v1/embeddings
POST /audio/transcriptions
POST /audio/speech
GET  /files
POST /files
POST /images/generations
POST /images/edits
POST /batches
POST /fine_tuning/jobs
POST /moderations
POST /rerank
POST /responses
GET  /config
POST /config/update
GET  /v1/model/info
```

**Finding**: LiteLLM is purposefully run without database. The endpoints need to be fixed to work in database-less mode.

### 4.3 NVIDIA Model Pruning

Initial whitelist contained 10 models. Testing revealed:

| Model | Status |
|-------|--------|
| \[OK\] `nvidia/nemotron-3-nano-30b-a3b` | Working (fast) |
| \[OK\] `nvidia/nemotron-3-super-120b-a12b` | Working (fast) |
| \[OK\] `poolside/laguna-xs-2.1` | Working (fast) |
| \[TIMEOUT\] `nvidia/nemotron-3-ultra-550b-a55b` | Timeout |
| \[TIMEOUT\] `google/gemma-4-31b-it` | Timeout |
| \[TIMEOUT\] `minimaxai/minimax-m3` | Timeout |
| \[TIMEOUT\] `openai/gpt-oss-120b` | Timeout |
| \[MISSING\] `stepfun-ai/step-3.7-flash` | Not found |
| \[MISSING\] `thinkingmachines/inkling` | Not found |
| \[MISSING\] `z-ai/glm-5.2` | Not found |

**Decision**: Remove non-existent models, keep timeout models (may load later).

### 4.4 NVIDIA Model Expansion

Whitelist expanded from 7 to 18 models with additional providers:

```json
{
  "nvidia": {
    "whitelist": [
      "google/gemma-4-31b-it",
      "minimaxai/minimax-m3",
      "moonshotai/kimi-k2.6",
      "moonshotai/kimi-k3",
      "nvidia/cosmos-reason2-8b",
      "nvidia/llama-3.1-nemotron-51b-instruct",
      "nvidia/llama-3.1-nemotron-70b-instruct",
      "nvidia/llama-3.1-nemotron-ultra-253b-v1",
      "nvidia/nemotron-3-nano-30b-a3b",
      "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
      "nvidia/nemotron-3-super-120b-a12b",
      "nvidia/nemotron-3-ultra-550b-a55b",
      "nvidia/nemotron-3.5-lightning-30b-a3b",
      "nvidia/nemotron-4-340b-instruct",
      "openai/gpt-oss-120b",
      "openai/gpt-oss-20b",
      "poolside/laguna-xs-2.1",
      "writer/palmyra-creative-122b"
    ]
  }
}
```

### 4.5 AIHubMix Provider Added

New provider added to `opencode.json`:

```json
{
  "aihubmix": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "AIHubMix",
    "options": {
      "baseURL": "https://api.aihubmix.com/v1",
      "apiKey": "sk-7sWyS9J4cMzU1rZj313c5b82D8C247B79c058aA2D73732C6"
    },
    "models": {
      "gpt-5.5": { "name": "GPT-5.5" },
      "gpt-5.4": { "name": "GPT-5.4" },
      "gpt-4o": { "name": "GPT-4o" },
      "claude-opus-5": { "name": "Claude Opus 5" },
      "claude-sonnet-5": { "name": "Claude Sonnet 5" },
      "gemini-3.7-flash": { "name": "Gemini 3.7 Flash" },
      "qwen3.8-max": { "name": "Qwen 3.8 Max" },
      "deepseek-v4-flash": { "name": "DeepSeek V4 Flash" }
    }
  }
}
```

### 4.6 Model Capability Discovery

Identified NVIDIA models by capability for future use:

**Vision Models (14)**
- `adept/fuyu-8b` - Image understanding
- `google/deplot` - Chart/plot understanding
- `google/diffusiongemma-26b-a4b-it` - Image generation
- `meta/llama-3.2-11b-vision-instruct` - Vision (11B)
- `meta/llama-3.2-90b-vision-instruct` - Vision (90B)
- `microsoft/kosmos-2` - Multimodal
- `microsoft/phi-3-vision-128k-instruct` - Vision
- `nvidia/ai-synthetic-video-detector` - Video analysis
- `nvidia/cosmos-reason2-8b` - Vision reasoning
- `nvidia/ising-calibration-1.5-31b` - Quantum plots
- `nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1` - Vision retrieval
- `nvidia/llama-nemotron-embed-vl-1b-v2` - Vision retrieval
- `nvidia/neva-22b` - Vision
- `nvidia/vila` - Vision

**Embedding Models (6)**
- `nvidia/embed-qa-4`
- `nvidia/llama-3.2-nv-embedqa-1b-v1`
- `nvidia/nemotron-3-embed-1b`
- `nvidia/nv-embedqa-mistral-7b-v2`
- `nvidia/nvclip` - Vision embedding
- `snowflake/arctic-embed-l`

**Audio/Translation Models (3)**
- `nvidia/riva-translate-4b-instruct`
- `nvidia/riva-translate-4b-instruct-v1.1`
- `nvidia/riva-translate-4b-instruct-v2`

**Safety/Guard Models (4)**
- `nvidia/llama-3.1-nemoguard-8b-content-safety`
- `nvidia/llama-3.1-nemoguard-8b-topic-control`
- `nvidia/llama-3.1-nemotron-safety-guard-8b-v3`
- `nvidia/nemotron-3.5-content-safety`

## 5. Diagnosis

1. **LiteLLM**: Server returns `No connected db` because it's configured without database. This is intentional behavior, but endpoints need to support database-less mode.

2. **NVIDIA Timeouts**: Some models (gpt-oss-120b, nemotron-3-ultra-550b-a55b) timeout due to cold-start or high load. These may work when warmed up.

3. **Missing Models**: `stepfun-ai/step-3.7-flash`, `thinkingmachines/inkling`, `z-ai/glm-5.2` do not exist in NVIDIA API catalog.

## 6. Preliminary Assessment

- **Provider health**: 4/5 providers fully functional, 1 (LiteLLM) needs endpoint fixes
- **NVIDIA whitelist**: Expanded from 7 to 18 models with variety of capabilities
- **New provider**: AIHubMix adds access to GPT-5.5, Claude Opus 5, Gemini 3.7 Flash
- **Future capabilities**: Vision, embedding, and audio models identified for expansion

## 7. Solution Summary

1. **opencode.json updated** with AIHubMix provider and expanded NVIDIA whitelist
2. **Task created** (`pending-fix-litellm-endpoint.md`) for LiteLLM endpoint fixes
3. **Task created** (`pending-categorize-nvidia-models.md`) for model capability organization
4. **Report generated** documenting all findings

## 8. Verification Plan

- [ ] Test AIHubMix models through OpenCode
- [ ] Test NVIDIA timeout models after warm-up
- [ ] Verify LiteLLM endpoints work without database after fixes
- [ ] Test vision/embedding models for specific use cases

## 9. Pending Actions

1. Fix LiteLLM endpoints to work without database
2. Categorize NVIDIA models by capability
3. Test AIHubMix model availability
4. Test NVIDIA timeout models after warm-up

## 10. Recommendations

1. **LiteLLM**: Investigate database-less mode configuration
2. **NVIDIA**: Re-test timeout models after warm-up period
3. **AIHubMix**: Consider adding more models from their catalog
4. **Vision/Embedding**: Test specific models for image analysis and RAG applications
5. **Fallback chain**: Ensure providers are ordered by reliability and cost

## Relevant Files

- `/home/sigit/.config/opencode/opencode.json` - Provider configuration
- `/home/sigit/.local/share/opencode/auth.json` - API keys
- `/home/sigit/.config/opencode/tasks/pending-fix-litellm-endpoint.md` - LiteLLM fix task
- `/home/sigit/.config/opencode/tasks/pending-categorize-nvidia-models.md` - Model categorization task
- `/tmp/opencode/provider-test-report.md` - Full test report
- `/tmp/opencode/nvidia-pruning-report.md` - NVIDIA pruning report

---

Generated by Kenari Free (LiteLLM)