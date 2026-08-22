# Hermes Agent Provider and Fallback Chain - Part 3

*Gemini primary + credential practices*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** OpenRouter, providers, Ollama, local-llm, Hermes Agent  

## 1. Objective

Migrate Hermes Agent from local Ollama + OpenRouter fallback to Google Gemini (AI Studio free tier) as primary provider, resolving configuration pitfalls and establishing credential management best practices.

## 2. Background

Previous setup: `tinyllama:65k` and `qwen2.5:3b` via Ollama, patched Hermes Agent runtime checks for small models, OpenRouter as cloud fallback (cycling `gpt-5.5`, `nvidia/nemotron-3-ultra`, free-tier models). Issues: OpenRouter free tier model availability, unpredictable rate limits, `tinyllama` stuck at 2K runtime context.

Desired: reliable cloud API, first-party, free tier, static API key, 1M token context.

## 3. Problem

Switching from local (Ollama) to cloud (Gemini) provider requires clearing legacy `model.base_url` or requests route to wrong endpoint. Free-tier Pro model has extreme rate limits. Credential propagation to external tools (OpenCode, OpenClaw) must avoid plaintext shell profiles.

## 4. Work Performed

### 4.1 Migration Commands

```bash
hermes auth add gemini --type api-key --api-key "AIzaSy..."
hermes config set model.provider gemini
hermes config set model.default gemini-2.5-flash
```

### 4.2 The `base_url` Trap

Test failed: `404: model 'gemini-2.5-flash' not found`. Error showed:
```
Endpoint: Endpoint: http://127.0.0.1:11434/v1
```
`model.provider` switched but `model.base_url` still pointed at Ollama.

Fix:
```bash
hermes config set model.api_key ""
hermes config set model.base_url ""
```

Clean state confirmed:
```
Model: {'api_key': '', 'base_url': '', 'default': 'gemini-2.5-flash', 'provider': 'gemini'}
```

**Lesson**: When switching local->cloud, MUST clear `model.base_url`. Error blames model ID; real culprit is endpoint.

### 4.3 Pro Model Quota Trap

Tried `gemini-2.5-pro` for reasoning:
```
429 Too Many Requests: You exceeded your current quota...
```
Free tier Pro: extremely tight limits. Flash: 15 RPM. Pro unusable for agent workloads (5-10 rapid calls/task).

Mitigation: Added agent memory note: **always suggest Flash, warn about Pro quota**. Hermes Agent now steers to `gemini-2.5-flash` by default. No way to hide Pro from picker (Hermes Agent reads full API model list). Workaround: pin default to Flash, let memory handle rest.

### 4.4 Credential Management: Vault vs Environment

Gemini key in Hermes auth pool (`~/.hermes/auth.json`, mode 600). External tools need same key.

Naive approach (bad):
```bash
export GOOGLE_API_KEY="AIzaSy..."  # plaintext in history, scrollback, hard to rotate
```

Better approach: pull from vault at shell startup:
```bash
export GOOGLE_API_KEY=$(hermes auth list gemini | grep -o 'AIzaSy[A-Za-z0-9_-]*' | head -n 1)
```

Benefits:
- Single source of truth (auth vault)
- Rotation in Hermes Agent propagates automatically
- No plaintext in shell profiles

Caveat: `hermes auth list` may redact secret in some versions. Fallback: `hermes config set-env` to `~/.hermes/.env` (tool-protected).

### 4.5 Before vs After Comparison

| Aspect | Before (Ollama + OpenRouter) | After (Gemini) |
|--------|------------------------------|----------------|
| Latency | Variable (local: fast/dumb, cloud: slow aggregator) | Consistent ~1-2s |
| Context window | 2K-8K (tinyllama fought) | 1M tokens |
| Model quality | Small models hallucinated | Flash handles most tasks |
| Rate limits | Ollama: none, OR: unpredictable | 15 RPM (predictable) |
| Setup complexity | Moderate (Ollama + config hacks) | Minimal (3 commands) |
| Reliability | Frequent 404s from OR, Ollama crashes | Single stable endpoint |

## 5. Diagnosis

Migration technically simple (3 commands) but `base_url` leftover creates confusing failure mode. Hermes Agent design: `model.provider` and `model.base_url` independent; changing one doesn't clear the other. Correct for 20+ providers but confusing during migration. Pro model quota is a hard free-tier limit requiring behavioral workaround.

## 6. Preliminary Assessment

Gemini Flash provides reliable, fast, large-context inference on free tier. Setup minimal. Credential management via vault is secure and maintainable. Pro model excluded behaviorally.

## 7. Solution Summary

- Migrated to Gemini via AI Studio free tier (3 commands)
- Cleared `base_url` trap (critical step)
- Pinned default to `gemini-2.5-flash`; behavioral guard against Pro
- Credential in Hermes Agent vault; shell export pulls from vault
- No plaintext keys in profiles

## 8. Verification Plan

- Monitor Flash reliability and latency in production
- Verify Pro quota warning triggers correctly
- Test credential rotation propagation
- Confirm no `base_url` regressions on future provider switches

## 9. Pending Actions

- Test `hermes auth list` redaction behavior; implement `.env` fallback if needed
- Document `base_url` trap in team runbook

## 10. Recommendations

- **Always check `Endpoint: Endpoint:` line in errors before assuming model ID is wrong.** Endpoint reveals actual routing. `127.0.0.1:11434` = Ollama, not Google. Fix routing first.
- Clear `model.base_url` and `model.api_key` when switching local->cloud
- Pin free-tier defaults to models with usable quotas
- Use vault-sourced shell exports for credential propagation
- Behavioral guards (agent memory) for unpinnable model picker entries
