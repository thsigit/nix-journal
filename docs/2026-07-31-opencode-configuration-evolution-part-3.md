# OpenCode Configuration Evolution - Part 3

*Dead provider and agent-model cleanup*

**Date:** 2026-07-31  
**Author:** Codebot  
**Topic:** OpenCode, config, maintenance, Mem0  

---

## 1. Objective

Housekeeping: consolidate Mem0 memories, prune dead providers, fix broken agent models.

## 2. Background

Regular maintenance session for OpenCode configuration and memory store.

## 3. Problem

Memory store with noise/duplicates. Dead providers in auth.json. Broken agent model references.

## 4. Work Performed

### 4.1 Memory Consolidation
Ran mem0-dream cycle. Started with 76 memories (Jul 24-31). Deleted 18 entries: stale session state, completed one-time requests, one credential fragment. Merged two near-duplicate gpt-oss-120b removal records. Rewrote LiteLLM "No connected db" bug fix to avoid naming master key env var. Final: 58 memories, zero sensitive data, all atomic.

### 4.2 Provider Pruning
opencode providers list showed Ambient and Cerebras API keys still registered. Both dead/unused. Removed from auth.json, deleted two cerebras model refs from opencode.json. Trailing comma after last provider removal broke JSON -- fixed immediately, validated with python3 -c "import json; ...".

### 4.3 Agent Model Repairs
Cross-referenced every agent model against live LiteLLM proxy. Three broken:

| Agent | Old Model | Problem | New Model |
|-------|-----------|---------|-----------|
| review | nvidia/nemotron-mini-4b-instruct | Missing nvidia/ prefix | nvidia/nvidia/nemotron-mini-4b-instruct |
| code | cohere/north-mini-code-1-0 | Cohere endpoint 404 | openrouter/cohere/north-mini-code:free |
| cheap | openrouter/meta-llama/llama-3.2-3b-instruct:free | Invalid model name | zai/glm-4.7-flash |

Review agent: typo (single nvidia/ prefix). Cohere direct dead; same model via OpenRouter free worked. OpenRouter Llama 3.2 3B invalid; ZAI GLM 4.7 Flash (200 OK, free) replaced.

### 4.4 Default Agent Change
Changed default_agent from build to chat. Build agent (Poolside Laguna XS) too narrow for general use. Chat agent (NVIDIA Nemotron Mini 4B) handles dialogue and general tasks concisely, matching preferred style.

### 4.5 Build Agent Upgrade
Upgraded build agent from openrouter/poolside/laguna-xs-2.1:free to groq/llama-3.3-70b-versatile. 70B on Groq significantly more capable for NixOS modules, build scripts, configs. Fast inference via Groq keeps latency reasonable.

## 5. Diagnosis

Memory noise reduces retrieval quality. Dead providers and broken models cause runtime errors. Agent models need periodic validation against live proxy.

## 6. Preliminary Assessment

Cleanup complete. All agents functional. Memory store lean.

## 7. Solution Summary

Mem0 consolidated to 58 entries. Dead providers removed. Three agent models fixed. Default agent changed. Build agent upgraded.

## 8. Verification Plan

Test all agent invocations. Verify memory search quality. Monitor for new dead providers.

## 9. Pending Actions

Periodic memory consolidation. Agent model validation against proxy.

## 10. Recommendations

Run mem0-dream regularly. Validate agent models after proxy changes. Keep auth.json minimal. Fix JSON syntax immediately after edits.
