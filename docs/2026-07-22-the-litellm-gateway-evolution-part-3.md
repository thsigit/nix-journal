# The LiteLLM Gateway Evolution - Part 3

*Removing Paxsenix and Rewiring to a Local LiteLLM Proxy*

**Date:** 2026-07-22  
**Author:** Codebot  
**Topic:** OpenCode, LiteLLM, homelab, SSL, Caddy, Podman, routing  

## 1. Objective

Remove PaxSenix provider from OpenCode configuration and rewire all agents to local LiteLLM proxy at litellm.home.arpa.

## 2. Background

PaxSenix was default provider across 7 OpenCode agents (chat, reason, code, review, vision, fast, cheap) with 136 models in opencode.json. User requested removal and migration to self-hosted LiteLLM gateway.

## 3. Problem

PaxSenix removal straightforward but proxy migration introduced SSL certificate validation failure, then 502 Bad Gateway from Caddy due to LiteLLM container crash-looping from config version mismatch.

## 4. Work Performed

### 4.1 PaxSenix Removal

- opencode.json: deleted provider.paxsenix block, rewrote all 7 agent model keys
- auth.json: removed API key
- model.json: purged PaxSenix from recent-model list
- All agents fell back to opencode/deepseek-v4-flash-free (built-in free model)

### 4.2 Proxy Configuration

- Added OpenAI-compatible provider pointing to https://litellm.home.arpa/v1
- Stored API key in auth.json
- Immediate error: "Failed to load auth provider metadata: unable to verify the first certificate"

### 4.3 SSL Certificate Resolution

- Homelab uses self-signed internal CA
- WSL2 mount had old homelab-ca.crt (AKI: 81:7A:0B:... vs server SKI: C8:3B:66:... - mismatch)
- Correct CA on homelab: /etc/ssl/certs/homelab-ca.pem
- Copied to Fedora trust store: /etc/pki/ca-trust/source/anchors/
- Ran update-ca-trust
- Node.js uses own CA bundle: set NODE_EXTRA_CA_CERTS permanently in .bashrc

### 4.4 502 Bad Gateway Debug

- Caddy log: "dial tcp 127.0.0.1:4000: connect: connection refused"
- LiteLLM Podman container crash-looping
- systemd showed "active" (conmon wrapper alive), but podman ps empty
- journalctl root cause: ValueError: Invalid routing_strategy: 'usage-based'. Valid: ['usage-based-routing', ...]
- LiteLLM v1.92.0 renamed usage-based to usage-based-routing
- Fixed: sed on /srv/appdata/litellm/config.yaml
- Container started cleanly, registering 140+ models (kenari, NVIDIA, OpenRouter, zai, Gemini, Ollama, groq, cerebras)

### 4.5 Final Configuration

- Rebuilt OpenCode config around proxy
- Provider section: 20 Kenari model definitions (via LiteLLM gateway)
- All agents use :free variants to avoid burning topped-up balance
- Stack: OpenCode -> litellm.home.arpa (Caddy TLS) -> localhost:4000 (LiteLLM) -> kenari/nvidia/openrouter

## 5. Diagnosis

AKI/SKI mismatch reveals wrong CA cert before deep SSL debugging. NODE_EXTRA_CA_CERTS required even after update-ca-trust (Node.js doesn't read system bundle). LiteLLM version bumps break configs silently (routing_strategy rename in patch release). Container "active" in systemd != healthy (check journalctl). OpenCode requires explicit model definitions in provider config (no auto-discovery from /v1/models).

## 6. Preliminary Assessment

Proxy healthy, 140+ models registered. OpenCode configured with single provider, single API key, single config. No more Paxsenix.

## 7. Solution Summary

- Removed PaxSenix from opencode.json, auth.json, model.json
- Configured LiteLLM proxy provider
- Resolved SSL: correct CA (homelab-ca.pem), Fedora trust store, NODE_EXTRA_CA_CERTS
- Fixed 502: LiteLLM routing_strategy v1.92.0 rename (usage-based -> usage-based-routing)
- Verified 140+ models registered
- Rewired OpenCode agents to proxy with :free variants

## 8. Verification Plan

- Test OpenCode agent responses via proxy
- Monitor LiteLLM container stability
- Verify :free model usage doesn't burn balance

## 9. Pending Actions

- Resolve billing situation for non-free models
- Monitor LiteLLM version updates for config breaks

## 10. Recommendations

- Check AKI/SKI before SSL debugging (openssl x509 -text comparison)
- Always set NODE_EXTRA_CA_CERTS on Linux for Node.js apps
- Monitor upstream version changes for breaking config keys
- Check journalctl on 5xx proxy errors (systemd status misleading)
- Define models explicitly in OpenCode provider config