# The TinyLlama Experiment - Part 2

*Taming The Context Window*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** OpenRouter, providers, Ollama, local-llm, Hermes Agent  

## 1. Objective

Enable Hermes Agent to accept small-context local models (specifically `tinyllama` at 2K) for chat-only workflows on CPU-only WSL2, by patching the 64K minimum context guard and investigating Ollama Modelfile-based context extension.

## 2. Background

WSL2, 16GB RAM, no GPU, free tiers only. Hermes Agent refuses models below 64K context. Local models: `tinyllama` (637 MB, 2K), `deepseek-r1:1.5b`, `starcoder2:3b`, `qwen2.5:3b`, `qwen3:4b`. OpenRouter free tier rate-limited (HTTP 429). Direct `ollama run` works but bypasses Hermes Agent tool infrastructure.

## 3. Problem

Two-layer block: (1) static guard in `agent_init.py` rejects init for context < 64K, (2) runtime guard queries Ollama for loaded context, refuses tool-use if < 64K. Need surgical fix preserving guard for other models.

## 4. Work Performed

### 4.1 Direct Ollama Test (Bypass)

```bash
ollama run tinyllama:latest "Reply with exactly: connected"
# Output: Exactly
```
Model loads, responds, minimal RAM. But no Hermes Agent tools, memory, skills.

### 4.2 Static Guard Patch

File: `~/.hermes/hermes-agent/agent/agent_init.py` (~line 1545).

Original:
```python
_ctx = getattr(agent.context_compressor, "context_length", 0)
if _ctx and _ctx < MINIMUM_CONTEXT_LENGTH:
    raise ValueError(...)
```

Patch: per-model override with whitelist.

```python
_model_id = str(getattr(agent, "model", "") or "").strip().lower()
try:
    from agent.model_metadata import _strip_provider_prefix
    _norm_model = _strip_provider_prefix(_model_id)
except Exception:
    _norm_model = _model_id

_allowed_small_models = {"tinyllama", "tinyllama:latest"}

if any(am in _norm_model for am in _allowed_small_models):
    _ra().logger.info(
        "Model %s has a context window of %d tokens (< %d) but is allowed by per-model override.",
        agent.model, _ctx, MINIMUM_CONTEXT_LENGTH,
    )
else:
    raise ValueError(...)
```

~25 lines. Uses `_strip_provider_prefix` for prefixed names (e.g., `ollama-launch:tinyllama:latest`). Logs clear message on override fire. Whitelist explicit - every new small model must be deliberately added.

### 4.3 Runtime Guard: Ollama Modelfile

After patch, second error:
```
Ollama loaded tinyllama:latest with only 2,048 tokens of runtime context, but Hermes needs at least 64,000.
```

Hermes Agent queries Ollama for actual loaded context. Ollama defaults `tinyllama` to 2K unless told otherwise.

Modelfile approach:
```
FROM tinyllama:latest
PARAMETER num_ctx 65536
```

```bash
ollama create tinyllama-65k -f ~/Modelfile.tinyllama
```

Changes runtime parameter. Model weights same. Not yet tested (writing post first). If 65K OOM on 8GB, will drop to 32K/16K.

### 4.4 Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| Hermes Agent refuses tinyllama | Hard block at init | Whitelist allows it |
| Ollama runtime context | 2,048 tokens | Needs Modelfile to increase |
| Tool-calling small models | Impossible | Possible (after Modelfile) |
| Safety guard other models | 64K minimum | Still 64K minimum |
| OpenRouter dependency | Required for cloud fallback | Local fallback available |

## 5. Diagnosis

Hermes Agent 64K minimum is reasonable for production agent workloads. Global disable not recommended. Per-model override is surgical fix preserving safety while enabling local-first for CPU users. Modelfile `num_ctx` is standard Ollama method but effectiveness depends on model architecture. Must verify runtime context empirically with `ollama ps`.

## 6. Preliminary Assessment

Patch applied and tested for static guard. Modelfile approach pending test. Whitelist currently {`tinyllama`, `tinyllama:latest`}. Final config will be honest about capabilities.

## 7. Solution Summary

- Patched `agent_init.py` with per-model whitelist override for `tinyllama` variants
- Static guard bypassed for whitelisted models with info log
- Modelfile instructions prepared for runtime context extension
- Global 64K guard preserved for all other models
- Direct `ollama run` remains escape hatch

## 8. Verification Plan

- Create and test Modelfile `tinyllama-65k`
- Verify runtime context with `ollama show` and `ollama ps`
- Test Hermes Agent chat with `tinyllama` (simple chat only)
- Confirm tool-calling sessions refused appropriately
- Monitor guard behavior for regressions

## 9. Pending Actions

- Execute Modelfile build and verify runtime context
- If 65K fails, test 32K/16K
- Evaluate alternative small models with native large context
- Document override pattern for future additions

## 10. Recommendations

- Use per-model whitelist overrides, not global minimum reduction
- Test Ollama runtime context empirically (`ollama ps`), not via metadata alone
- Accept hardware/model limitations honestly; configure tool restrictions accordingly
- Keep direct `ollama run` as escape hatch for refused operations
- Rotate API keys immediately when exposed in chat
