# Configuring Ollama Github Models

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** OpenRouter, providers, Ollama, local-llm, Hermes Agent  

## 1. Objective

Configure Ollama CLI as a unified proxy front-end for multiple LLM providers (GitHub Copilot, OpenRouter, Ollama cloud) without local model weights, using stateless adapter containers pulled via OCI references.

## 2. Background

Hermes Agent runs on WSL2 (FedoraWSL) with local Ollama and cloud providers. OpenRouter and GitHub Copilot already connected. Goal: `ollama launch <model>` routes to any provider via adapter containers. User explicitly does not want local model weights.

## 3. Problem

Ollama CLI natively runs local models. Need to extend it to proxy requests to external provider APIs through adapter containers, making those adapters appear as first-class Ollama models.

## 4. Work Performed

### 4.1 Goal Clarification

User requirement: Ollama as proxy/front-end for GitHub Copilot API (and others), not as model runner. Three approaches offered:
- A: Hermes Agent built-in multi-provider routing (already working)
- B: Adapter OCI images pulled via `ollama pull docker://...`
- C: Ollama Modelfile as first-class model definition wrapping adapter

User chose to keep all three as options.

### 4.2 Ollama Capability Investigation

`ollama --help`, `ollama pull --help`, `ollama create --help`, `ollama run --help`:
- `ollama pull` accepts OCI refs (e.g., `docker://ghcr.io/...`)
- `ollama create` accepts `-f Modelfile`
- `ollama run` supports `--keepalive`, `--format`, `--insecure`, experimental flags
- `:cloud` models already present (e.g., `gemma4:31b-cloud`)

### 4.3 Adapter Design

Core concept: tiny Docker images (~20MB) with Python script:
1. Read prompt from argv/stdin
2. Call target provider HTTP API (OpenRouter or Copilot proxy)
3. Print response to stdout

Ollama pulls/runs as models. Stateless - no weights, fast startup, trivial updates.

Templates provided for:
- OpenRouter adapter: `openrouter_adapter.py` + `Dockerfile` + `requirements.txt`
- Copilot adapter: two variants (shell-out to `copilot` CLI, or HTTP proxy)
- Build/push commands for GHCR with `docker login` + `docker push`

### 4.4 Modelfile Template

Created `/home/sigit/Modelfile`:
```yaml
name: copilot-adapter
run: |
  #! /bin/sh
  /app/copilot_adapter ""

description: "Adapter that proxies prompts to GitHub Copilot"

build:
  context: .
  dockerfile: Dockerfile
```

### 4.5 Hermes Agent Integration

Bridge Ollama models into Hermes Agent `/model` picker:
```bash
hermes config set providers.ollama-launch.models '["openrouter:adapter","copilot:adapter","gemma4:31b-cloud"]'
```

### 4.6 Architecture Summary

```
User
  ollama launch <adapter>
    Ollama pulls/runs adapter container
      adapter calls provider API
        response to stdout
          Ollama returns to user

Hermes /model
  reads providers.ollama-launch.models
    shows all three provider models as choices
```

### 4.7 Key Decisions

| Decision | Rationale |
|----------|-----------|
| Adapter images, not local models | User explicitly said no local models |
| Stateless containers | No weight storage, fast startup, trivial updates |
| GHCR registry | Free for public, integrates with GitHub |
| Modelfile approach | Makes adapters first-class Ollama models |
| Keep A/B/C available | User wants flexibility, not lock-in |

### 4.8 Security Note

API keys via environment variables or Docker secrets only. Never bake into images.

## 5. Diagnosis

Ollama's OCI support and Modelfile system enable running arbitrary containers as "models." This is an unconventional but clean pattern for provider proxying. The Modelfile bridges script-to-model recognition. Hermes Agent config is the glue for UI visibility.

## 6. Preliminary Assessment

Architecture is sound. Adapters are lightweight. GHCR integration is seamless. Hermes Agent bridge is minimal. No code written yet - all design and templates.

## 7. Solution Summary

Designed adapter-based Ollama proxy architecture with Modelfile templates, Dockerfile templates, GHCR push workflow, and Hermes Agent integration. Three approaches (A/B/C) preserved as options.

## 8. Verification Plan

- Flesh out complete Modelfile + Dockerfile for both adapters
- Build locally with `ollama create` or `docker build`
- Push to GHCR (requires GitHub PAT)
- Register model names in Hermes Agent config
- End-to-end test: `ollama run openrouter:adapter "hello"`

## 9. Pending Actions

- Complete adapter implementations (OpenRouter + Copilot)
- Build and test locally
- Push to GHCR
- Register in Hermes Agent config
- Full integration test

## 10. Recommendations

- Keep adapters minimal (~20MB target)
- Use environment variables for all secrets
- Version adapter images independently of provider APIs
- Document Modelfile as the contract between Ollama and adapter
- Test with actual provider credentials before committing
