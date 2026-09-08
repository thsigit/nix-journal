# LiteLLM Model Pruning and Non-Text Discovery: From 32 to 7 (and That's a Good Thing)

**Date:** 2026-09-02  
**Author:** Codebot  
**Topic:** litellm, nvidia, pruning, models, embedding, vision, translation

---

## 1. Objective (or: Why Does My Gateway Have 32 Models When I Use Three?)

The LiteLLM proxy had ballooned to 32 models across three providers (OpenRouter, freetheai, NVIDIA). Most were stale, EOL, or simply never worked on the free-tier keys. Meanwhile, opencode routes directly to NVIDIA/OpenRouter/Kenari - it doesn't even go through litellm. The proxy exists for *other* purposes, and those purposes only need models that actually work.

The plan:
1. Prune every model that's EOL, stale, or broken upstream
2. Drop OpenRouter and freetheai entirely (opencode handles those directly)
3. Investigate whether NVIDIA's free tier offers non-text models (vision, embedding, audio)
4. Add anything that works to the proxy

Narrator: it was not 32 models. It was 7.

## 2. Background (or: The Graveyard of Good Intentions)

The previous session (`2026-09-02-static-config-refactor.md`) moved litellm from a dynamic render pipeline to a static committed `config.yaml`. That solved the *config ergonomics* problem. What it didn't solve was the *model bloat* problem - 32 models, half of which returned 401, 404, or timeout on every request.

The proxy config lived at `/srv/appdata/litellm/config.yaml` (live, admin-editable) with a committed seed at `common/ai/litellm/config.yaml` in nix-lab. API keys came from `/run/secrets/providers.env` (SOPS-encrypted on homelab). The key distinction: editing the live config does *not* require `nixos-rebuild`. Just `systemctl restart litellm`.

## 3. Problem (or: Everything Is Broken, Send Help)

The problems were layered like a lazy Sunday lasagna:

1. **EOL models still in config**: `llama-3.3-70b-instruct`, `nemotron-super-49b-v1.5`, `llama-3.1-70b-instruct`, `step-3.7-flash` - already absent from proxy (good), but some still referenced in opencode inventory
2. **OpenRouter/freetheai providers**: 17 OpenRouter models + 4 freetheai entries, all routed through litellm. But opencode routes *directly* to these providers - litellm was just adding latency
3. **NVIDIA models returning 401/404**: `gemma-4-31b-it`, `kimi-k3`, `mistral-nemotron` - returned 0 bytes after 45 seconds (dead upstream)
4. **`nemotron-3-ultra-550b`**: intermittent 503 "Service temporarily overloaded" - sometimes worked, sometimes didn't
5. **No non-text models**: vision, embedding, audio categories were entirely unexplored on NVIDIA's free tier

## 4. Work Performed (or: The Great Filter)

### 4.1 Phase 1: Drop Dead Providers

Removed all OpenRouter and freetheai entries from the live config:
- 17 OpenRouter models (including `openai/gpt-4o`, `openai/gpt-4o-mini`, `google/gemini-2.5-pro`, etc.)
- 4 freetheai models (including `freetheai/gpt-4o-mini-free`, `freetheai/gemini-2.0-flash-free`)
- Associated aliases and fallback chains

Rewrote config to NVIDIA-only: 4 curated text models.

### 4.2 Phase 1b: Drop Dead NVIDIA Models

Tested the remaining NVIDIA models against `integrate.api.nvidia.com/v1/chat/completions` with the homelab API key:

| Model | Result | Decision |
|---|---|---|
| `gemma-4-31b-it` | 0 bytes after 45s | Dropped |
| `kimi-k3` | 0 bytes after 45s | Dropped |
| `mistral-nemotron` | 0 bytes after 45s | Dropped |
| `nemotron-3-ultra-550b-a55b` | Intermittent 503 | Kept (then dropped in Phase 2) |

Deployed 4-model config. Verified 4 models in `/v1/models`. Round-trip tested all four.

### 4.3 Phase 2: Probe NVIDIA's Free-Tier Catalog

This is where things got interesting. NVIDIA's `/v1/models` endpoint lists **82 models** for the homelab API key. But - and this is the crucial detail - **not all are callable**. Most return:

```json
{
  "status": 404,
  "title": "Not Found",
  "detail": "Function 'uuid': Not found for account 'N6q4a7qQR44aLoGag...'"
}
```

The docs say "~107 of 187 catalog models are callable on the free tier." For our key, the number was much lower.

#### 4.3.1 Vision Models

Tested 10 vision models against `/v1/chat/completions` (same endpoint as text, with `image_url` content parts):

| Model | Result |
|---|---|
| `meta/llama-3.2-11b-vision-instruct` | **200 PASS** |
| `meta/llama-3.2-90b-vision-instruct` | Timeout (overloaded) |
| `nvidia/cosmos-reason2-8b` | 404 (not for account) |
| `nvidia/neva-22b` | 404 (not for account) |
| `nvidia/vila` | 404 (not for account) |
| `microsoft/phi-3-vision-128k-instruct` | 404 (not for account) |
| `microsoft/kosmos-2` | 404 (not for account) |
| `google/deplot` | 404 (not for account) |
| `adept/fuyu-8b` | 404 (not for account) |

**1 out of 10 vision models worked.** The rest were either not deployed for this account or permanently overloaded.

#### 4.3.2 Embedding Models

Tested 8 embedding models against `/v1/embeddings`:

| Model | Result |
|---|---|
| `nvidia/nemotron-3-embed-1b` | **200 PASS** (2048d) |
| `nvidia/llama-nemotron-embed-vl-1b-v2` | **200 PASS** (2048d, needs `input_type`) |
| `nvidia/nv-embedqa-e5-v5` | 410 Gone (EOL 2026-08-25) |
| `nvidia/embed-qa-4` | 404 (not for account) |
| `nvidia/llama-3.2-nv-embedqa-1b-v1` | 404 (not for account) |
| `nvidia/nv-embedqa-mistral-7b-v2` | 404 (not for account) |
| `nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1` | 404 (not for account) |
| `snowflake/arctic-embed-l` | 404 (not for account) |

**2 out of 8 embedding models worked.** But there was a catch - litellm sent `encoding_format: None` by default, and NVIDIA's API requires it to be explicitly `"float"` or `"base64"`. Fixed by adding `encoding_format: float` to `litellm_params`.

#### 4.3.3 Audio Models

**Zero TTS/ASR/audio-generation models exist** in the NVIDIA free-tier catalog. Searched all 82 model IDs for `audio`, `speech`, `tts`, `stt`, `asr`, `whisper`, `bark`, `voice` - nothing.

Two speech-translation models (`riva-translate-4b-instruct-v1.1` and `-v2`) were callable and accept text input. `riva-translate-v2` translates to Bahasa Indonesia:

```
Input:  "Good morning, how are you today?"
Output: "Selamat pagi, bagaimana kesehatanmu hari ini?"
```

Added v2 to the proxy.

#### 4.3.4 Safety/Specialized Models

`nemoguard-8b-content-safety` and `nemotron-3.5-content-safety` both worked (200) but are content moderation classifiers - not useful for general proxy purposes. `nemotron-parse` returned 400 (needs document input, not text). `nemotron-3-nano-omni-30b-a3b-reasoning` returned 503 (overloaded). None added.

### 4.4 Phase 2b: Drop ultra-550b, Add riva-translate-v2

`nemotron-3-ultra-550b-a55b` had been returning intermittent 503 "Service temporarily overloaded" throughout the session. Sometimes passed, sometimes didn't. Decided to drop it rather than keep a flaky model in the proxy.

`riva-translate-4b-instruct-v2` added for Bahasa Indonesia translation support.

## 5. Diagnosis (or: What NVIDIA's Catalog Really Looks Like)

Two distinct failure modes exist on NVIDIA's free tier:

### 5.1 Hard 404 - "Function not found for account"

The model exists in the catalog but has no active inference function deployed for your API key's account. These will **never** work on the free tier. The error includes the model's internal UUID, confirming it's an account-scoping issue, not a model-ID issue.

### 5.2 Soft 404 / 503 - Transient upstream failures

The model *is* callable but NVIDIA's load balancer occasionally routes to a node without the model loaded (404) or all nodes are at capacity (503). Retries succeed. This affected `nemotron-3-super-120b` (rare 404) and `nemotron-3-ultra-550b` (frequent 503).

### 5.3 Embedding Param Gotcha

litellm's embedding handler sends `encoding_format: None` when the param isn't explicitly set. NVIDIA's API treats this as an invalid value (422: "Input should be 'float' or 'base64'"). The fix: add `encoding_format: float` to the model's `litellm_params`. This is a litellm-NVIDIA interop issue, not documented anywhere obvious.

## 6. Preliminary Assessment (or: The Final Scorecard)

After probing 82 catalog models across text, vision, embedding, audio, safety, and specialized categories:

| Category | Catalog | Callable | Added to Proxy |
|---|---|---|---|
| Text | ~40 | 4 | 3 (dropped ultra-550b) |
| Vision | 10 | 1 | 1 |
| Embedding | 8 | 2 | 2 |
| Audio/TTS/ASR | 0 | 0 | 0 |
| Speech Translation | 3 | 2 | 1 |
| Safety/Content | 5 | 2 | 0 |
| Specialized | 3 | 1 | 0 |
| **Total** | **~82** | **12** | **7** |

The proxy went from 32 models to 7. Every model in the final set has been round-trip tested through the litellm proxy.

## 7. Solution Summary (or: Less Is More)

### Final proxy model list

| # | Model ID | Type | Reliability |
|---|---|---|---|
| 1 | `nvidia/openai/gpt-oss-120b` | text | Rock solid |
| 2 | `nvidia/nvidia/nemotron-3-super-120b-a12b` | text | Rare upstream 404, retries OK |
| 3 | `nvidia/nvidia/nemotron-3.5-lightning-30b-a3b` | text | Rock solid |
| 4 | `nvidia/meta/llama-3.2-11b-vision-instruct` | vision | Rock solid |
| 5 | `nvidia/nvidia/nemotron-3-embed-1b` | embedding 2048d | Rock solid |
| 6 | `nvidia/nvidia/llama-nemotron-embed-vl-1b-v2` | embedding 2048d | Rock solid |
| 7 | `nvidia/riva-translate-4b-instruct-v2` | EN<->ID translation | Rock solid |

### Key config changes
- `encoding_format: float` added to embedding model blocks (litellm interop fix)
- `input_type: query` added to embedding model blocks (required for asymmetric models)
- `ultra-550b` removed
- All OpenRouter/freetheai entries removed
- Seed synced with live config

### Commits
- `bcf3454` - litellm: prune EOL models, drop OpenRouter/freetheai, NVIDIA-only
- `6c35223` - litellm: sync seed after Phase 1 pruning
- `8a719fe` - litellm: add vision, embedding, translation models; drop ultra-550b

## 8. Verification Plan (or: Trust But Verify)

All 7 models round-trip tested through `litellm.home.arpa`:
- Chat models: `POST /v1/chat/completions` with `"Say OK"` prompt
- Embedding models: `POST /v1/embeddings` with `"hello world"` input
- Translation model: `POST /v1/chat/completions` with EN-to-ID prompt

Future verification: run `test-litellm.sh` (in `skills/litellm-connectivity/`) periodically. Requires `LITELLM_API_KEY` env var set to the litellm master key.

## 9. Pending Actions (or: What's Still On the Board)

1. **No further pending actions** from this session. All configs deployed, seed committed, backups saved.

## 10. Recommendations (or: Where Do We Go From Here)

1. **Monitor `super-120b` reliability**: if upstream 404s become frequent, consider dropping to 6 models
2. **Re-probe NVIDIA catalog quarterly**: free-tier model availability changes; new models may become callable
3. **Non-text usage**: embedding models are now available through litellm for any service that needs vector search (RAG, memory, document retrieval). Vision model available for image understanding tasks
4. **`riva-translate-v2`**: useful for any workflow needing EN<->Bahasa Indonesia translation. No additional config needed - it's already in the proxy

---

Backups saved:
- `config.yaml.pre-drop-ultra-add-riva.20260902-191608`
- `config.yaml.pre-non-text.20260902-185910`
- `config.yaml.pre-nvidia-only.20260902-175358`

Generated by Big Pickle (OpenCode)
