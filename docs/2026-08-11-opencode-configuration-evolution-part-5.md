# OpenCode Configuration Evolution - Part 5

*NVIDIA whitelist + dead-reference sweep*

**Date:** 2026-08-11  
**Author:** Codebot  
**Topic:** OpenCode, model, config, curation, session, cli  

## 1. Objective

Reduce the number of NVIDIA models surfaced in OpenCode's CLI (`opencode models nvidia`) from 90+ down to a small curated set of text-generative flagship models, so the model picker only shows live, usable options. Second session validated model prefixes, then swept the agent configuration for dead model references and repointed them to live whitelist entries.

## 2. Background

OpenCode fetches provider model catalogs from the models.dev registry. Not every cataloged model is a live, general-purpose text generator. The NVIDIA catalog alone includes embeddings, rerankers, safety classifiers, image/video generators, ASR/TTS models, vision-language models, protein-folding tools, and driving/3D specialists. The user wanted only the models actually useful in OpenCode's CLI to appear.

The authoritative JSON Schema at https://opencode.ai/config.json defines a provider-level `blacklist` array (model IDs to exclude) and a `whitelist` array (model IDs to include; the inverse approach). Config changes require an OpenCode restart to take effect.

## 3. Work Performed

### 3.1 Initial Blacklist

The user first requested blacklisting six specific NVIDIA models that were cataloged but not live:
- `qwen/qwen3.5-397b-a17b` (Qwen3.5-397B-A17B)
- `deepseek-ai/deepseek-v4-pro` (DeepSeek V4 Pro)
- `deepseek-ai/deepseek-v4-flash` (DeepSeek V4 Flash)
- `black-forest-labs/flux.1-dev` (FLUX.1-dev)
- `mistralai/mixtral-8x7b-instruct` (Mistral: Mixtral 8x7B Instruct)
- `mistralai/mixtral-8x22b-instruct` (Mistral: Mixtral 8x22B Instruct)

An earlier draft added `hidden: true` model entries, which the schema rejects (models use `additionalProperties: false`), so those were reverted. The correct mechanism is the provider-level `blacklist` array on the `nvidia` provider config. Verified: after adding the six IDs, `opencode models nvidia` no longer listed them.

### 3.2 Broad Blacklist of Non-Text-Generative Models

The user then asked to filter to text-generative models only and blacklist the rest. Classified every model from `opencode models nvidia` by modality data in the models.dev API:

- **Kept (text LLMs):** Llama 3.1/3.2/3.3/4, Gemma 2/3/4, Nemotron (Super/Ultra/Nano/Omni), Mistral family, Qwen coder/next, GPT-OSS, phi-4-mini, GLM-5.2, step-3.x-flash, minimax, poolside laguna, upstage solar, inkling, etc.
- **Blacklisted (49 entries):** all embeddings (nv-embed*, bge-m3, nemoretriever), rerankers, safety guards (llama-guard, nemotron-content-safety), image generators (flux*, qwen-image*), video generators (cosmos*), ASR/TTS (whisper, magpie, studiovoice, nemotron-voicechat), vision-only VL models, protein tools (esm*), driving models (bevformer, streampetr, sparsedrive), 3D/USD tools, translation (riva), and PII extraction (gliner).

This left ~49 text-generative models, which the user still considered too many.

### 3.3 Whitelist (Inverse) Approach

Replaced the blacklist with a curated `whitelist` of flagship text models:

| Model | Rationale |
|---|---|
| `meta/llama-3.1-70b-instruct` | Model under test |
| `meta/llama-3.3-70b-instruct` | Best general llama |
| `nvidia/llama-3.3-nemotron-super-49b-v1.5` | Best nemotron, reasoning |
| `nvidia/nemotron-mini-4b-instruct` | Used by reason/review/fast/plan agents |
| `qwen/qwen3-next-80b-a3b-instruct` | Qwen flagship |
| `mistralai/mistral-small-4-119b-2603` | Mistral flagship |
| `google/gemma-4-31b-it` | Gemma flagship |
| `openai/gpt-oss-120b` | GPT-OSS flagship |
| `openai/gpt-oss-20b` | Used by build agent |

### 3.4 Final Slim-Down and Agent Repointing

Removed `nvidia/nemotron-mini-4b-instruct` and `openai/gpt-oss-20b` from the whitelist, then repointed every reference:

- default model -> `nvidia/llama-3.3-nemotron-super-49b-v1.5`
- `reason` -> `nvidia/llama-3.3-nemotron-super-49b-v1.5`
- `review`, `fast` -> `nvidia/google/gemma-4-31b-it`
- `build` -> `nvidia/openai/gpt-oss-120b`
- `plan` -> `nvidia/qwen/qwen3-next-80b-a3b-instruct`

Final whitelist (7 models): llama-3.1-70b, llama-3.3-70b, nemotron-super-49b-v1.5, qwen3-next-80b, mistral-small-4, gemma-4-31b, gpt-oss-120b.

### 3.5 Prefix Validation and Agent Dead-Model Cleanup (Session 2)

The follow-up session validated that every whitelist entry uses the correct `nvidia/` provider prefix, then audited all agents for references to models that are no longer live.

**Prefix validation:** The user asked whether the models in the config carry the right provider prefix. Only `nvidia/llama-3.3-nemotron-super-49b-v1.5` had the correct `nvidia/` prefix; the others were `meta/`, `qwen/`, `mistralai/`, `google/`, `openai/`. The user removed the Nemotron Nano models from the whitelist, leaving 15 models (3 with the `nvidia/` prefix, 12 with other prefixes).

**Dead agent model sweep:** After a restart, the config was read directly from `/home/sigit/.config/opencode/opencode.json`. Six model references were broken - three pointed at `nvidia/meta/llama-3.3-70b-instruct` (no longer in the whitelist) and three carried an incorrect `nvidia/` prefix:

| Agent | Dead/Incorrect reference | Replacement |
|---|---|---|
| default (top-level) | `nvidia/meta/llama-3.3-70b-instruct` | `nvidia/nemotron-3-super-120b-a12b` |
| `reason` | `nvidia/meta/llama-3.3-70b-instruct` | `nvidia/nemotron-3-super-120b-a12b` |
| `plan` | `nvidia/meta/llama-3.3-70b-instruct` | `nvidia/nemotron-3-super-120b-a12b` |
| `review` | `nvidia/google/gemma-4-31b-it` | `google/gemma-4-31b-it` |
| `fast` | `nvidia/google/gemma-4-31b-it` | `google/gemma-4-31b-it` |
| `build` | `nvidia/openai/gpt-oss-120b` | `openai/gpt-oss-120b` |

Each replacement was chosen from the live NVIDIA whitelist, and the `nvidia/` prefix was stripped where the whitelist entry is listed under its bare provider (`google/`, `openai/`).

**Verification:** Re-read the config and cross-checked every NVIDIA-backed agent against the whitelist. All agents now reference live, whitelisted models:

- `reason`: `nvidia/nemotron-3-super-120b-a12b` - in whitelist
- `review`: `google/gemma-4-31b-it` - in whitelist
- `fast`: `google/gemma-4-31b-it` - in whitelist
- `build`: `openai/gpt-oss-120b` - in whitelist
- `plan`: `nvidia/nemotron-3-super-120b-a12b` - in whitelist

Non-NVIDIA agents (`code`, `cheap`) were left unchanged and functional.

## 4. Diagnosis

The bloated picker stemmed from models.dev catalogs being loaded wholesale, with no filtering between catalog entries and live, text-capable models. OpenCode's `blacklist`/`whitelist` provider arrays are the supported way to curate this. A second failure mode surfaced in the follow-up: agent and default model references drifted from the whitelist after models were removed, and some carried an incorrect provider prefix (`nvidia/google/...`, `nvidia/openai/...`), making them unresolvable.

## 5. Key Findings

- `hidden: true` is not a valid model property; `ProviderConfig.blacklist` and `ProviderConfig.whitelist` are the correct fields.
- Whitelist is strictly easier to maintain than a 49-row blacklist for a small target set.
- Agent and default model references must be repointed when a referenced model is removed from the whitelist, or OpenCode breaks.
- `opencode models nvidia` output is the ground truth for verifying that the filter took effect.
- Model IDs are provider-prefixed; the prefix must match how the whitelist entry is defined (bare `google/...` in the whitelist means agents must use `google/...`, not `nvidia/google/...`).

## 6. Pending Actions

- Remove `nvidia/nvidia/nemotron-mini-4b-instruct` and `nvidia/openai/gpt-oss-20b` from the `litellm` provider's `models` map (still present, separate from the NVIDIA whitelist).
- Restart OpenCode and confirm `opencode models nvidia` lists exactly the curated set and all agents resolve their models.

## 7. Recommendations

1. Prefer `whitelist` over `blacklist` when the target set is small and stable.
2. Always validate config changes against https://opencode.ai/config.json before writing.
3. After any provider filter change, verify with `opencode models <provider>` and repoint agent model references.
4. Restart OpenCode after config edits; the running session keeps the stale config.
5. When an agent uses a model from a whitelist, copy the model ID verbatim from the whitelist entry - never re-add a provider prefix that the whitelist entry does not carry.
6. After removing models from a whitelist, grep the config for remaining references before restarting.
