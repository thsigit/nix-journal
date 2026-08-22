# The LiteLLM Gateway Evolution - Part 7

*Prune dead providers + OpenCode integration*

**Date:** 2026-07-30  
**Author:** Codebot  
**Topic:** NixOS, LiteLLM, API provider management  

---

## 1. Objective

Configure homelab LiteLLM proxy as central AI gateway: prune dead providers, curate working models, integrate with OpenCode agent framework.

## 2. Background

LiteLLM proxy managing multiple providers. Need operational gateway for OpenCode.

## 3. Problem

Provider inventory included dead/unused entries. Model selection over-provisioned. OpenCode config had duplicates.

## 4. Work Performed

### 4.1 Provider Inventory
| Provider | Source | Models Kept |
|----------|--------|-------------|
| Kenari | LiteLLM proxy @ litellm.home.arpa | 1 (kenari-free) |
| NVIDIA NIM | integrate.api.nvidia.com | 31 (free tier) |
| Aichixia | aichixia.xyz | 7 (free tier) |
| PaxSenix | api.paxsenix.org | 2 (free tier) |

Removed: apizio, inceptionlabs (dead: no API response, no models).

### 4.2 Model Selection
PaxSenix: 159 available, chose 2: paxsenix/glm-4.7-flash, paxsenix/gpt-5-mini.
Aichixia: 26 available, pruned to 7 working free-tier. One (deepseek-v3.2) dropped -- API rejects with "Pro or Enterprise plan required".
NVIDIA: 60+ in opencode.json including vision, embedding, image, safety. Pruned to 31 streaming chat models. All free.

### 4.3 opencode.json Cleanup
~/.config/opencode/opencode.json deduplicated. All provider entries unique, every model reachable via LiteLLM.
reason agent model switched from paxsenix/o3-mini (not in models.json) to kenari/kenari-free.

### 4.4 litellm-render
config.yaml generated from models.json + providers.json:
```bash
sudo litellm-render /srv/appdata/litellm/models.json /srv/appdata/litellm/providers.json
```
Current: 139 models, 5 aliases, 1 fallback. Container auto-restarts on config change via systemd path unit watcher.

### 4.5 Verification
| Test | Result |
|------|--------|
| curl -> /chat/completions (glm-4.7-flash) | 200 OK |
| curl -> /chat/completions (gpt-5-mini) | 200 OK |
| Cache hit on repeated prompt | 100% |
| OpenCode reason agent invoke | works (kenari-free) |

## 5. Diagnosis

Dead providers silently break routing. Duplicate opencode.json entries cause errors. Pro/Enterprise models listed but inaccessible on free tier.

## 6. Preliminary Assessment

Curated provider set operational. OpenCode integration verified.

## 7. Solution Summary

4 providers, curated models, deduplicated opencode.json, verified gateway health.

## 8. Verification Plan

Periodic provider health checks. Monitor for model deprecations.

## 9. Pending Actions

None.

## 10. Recommendations

- Always grep for existing model IDs before adding to opencode.json
- Verify each provider with direct curl before including
- Test with non-master API key to confirm free-tier access
- Remove dead providers promptly
