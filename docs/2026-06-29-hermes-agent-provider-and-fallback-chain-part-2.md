# Hermes Agent Provider and Fallback Chain - Part 2

*OpenRouter as cloud provider*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** OpenRouter, providers, Ollama, local-llm, Hermes Agent  

## 1. Objective

Connect Hermes Agent to OpenRouter as a cloud provider, replacing local Ollama backend, and verify end-to-end connectivity.

## 2. Background

Hermes Agent ran on WSL2 with local Ollama (`ollama-launch` provider, `minimax-m3:cloud` model, `http://127.0.0.1:11434/v1`). Local models limited: no reasoning, no large context, no frontier capabilities. OpenRouter aggregates dozens of providers under one API key.

## 3. Problem

Local Ollama backend lacks frontier model capabilities. Need reliable cloud provider with dynamic model routing.

## 4. Work Performed

### 4.1 State Assessment

`hermes config show` and `hermes auth list`:
- Provider: `ollama-launch`
- Model: `minimax-m3:cloud`
- Base URL: `http://127.0.0.1:11434/v1`
- OpenRouter not in auth pool
- Commented `# OPENROUTER_API_KEY=` in `.env` (placeholder, never filled)

### 4.2 API Key Acquisition

User provided OpenRouter key in chat. Proceeded directly to persistence (no echo/storage in chat).

### 4.3 Credential Storage

Two approaches attempted:

1. **Direct `.env` write** - blocked. `.env` is protected; `write_file` tool rejects it.
2. **`hermes auth add`** - proper path.
   - Interactive `hermes auth add openrouter` failed: no TTY (`termios.error`)
   - Non-interactive flag worked:
     ```bash
     hermes auth add openrouter --type api-key --api-key 'sk-or-...'
     ```
   - Result: `"Added openrouter credential #1: \"api-key-1\""` in `~/.hermes/auth.json` (mode 600)

### 4.4 Provider Switch

```bash
hermes config set model.provider openrouter
hermes config set model.default openrouter/auto
hermes config set model.api_key ""      # clear old ollama key
hermes config set model.base_url ""     # clear old ollama URL
```

`openrouter/auto` lets OpenRouter pick best available model dynamically (cost-optimized).

### 4.5 Verification

**Doctor check**: False alarm - "model.provider 'openrouter' is set but no API key is configured." Doctor only scans `.env`, not `auth.json`. Credential valid.

**Live test**:
```bash
hermes chat -q "Reply with exactly: openrouter-connected"
```
Response in 4 seconds. OpenRouter routed successfully.

## 5. Diagnosis

`hermes auth add --api-key` is the correct non-interactive credential method. Interactive prompt requires TTY and crashes with `EOFError` otherwise. Doctor's `.env` check is stale - doesn't recognize `auth.json` credentials. `openrouter/auto` is a solid default for dynamic routing. No restart needed - new `hermes` invocation picks up config immediately.

## 6. Preliminary Assessment

Connection established and verified. Credential stored securely in `auth.json`. Dynamic model routing active. Legacy Ollama config cleared.

## 7. Solution Summary

- OpenRouter credential added via `hermes auth add --api-key` (non-interactive)
- Provider switched to `openrouter`, model to `openrouter/auto`
- Legacy `base_url` and `api_key` cleared
- Live test confirmed end-to-end connectivity (4s response)

## 8. Verification Plan

- Monitor OpenRouter usage and quota
- Test `openrouter/auto` model selection quality
- Verify Doctor check false alarm does not affect operations

## 9. Pending Actions

- None immediate. Configuration complete and verified.

## 10. Recommendations

- Always use `hermes auth add --api-key` for non-interactive credential addition
- Clear `model.base_url` and `model.api_key` when switching from local to cloud providers
- Be aware of Doctor's `.env`-only credential check limitation
- `openrouter/auto` recommended for "best available" dynamic routing
