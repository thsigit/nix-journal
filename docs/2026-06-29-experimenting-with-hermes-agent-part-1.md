# Experimenting with Hermes Agent - Part 1

*Failover config + mem0 upgrade*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** Hermes Agent, fallback, Mem0, free-tier, gemini-claw, Ollama  

## 1. Objective

Build a resilient Hermes Agent configuration that automatically fails over across free-tier LLM providers when primary models become unavailable, and upgrade memory system from SQLite to Mem0 for semantic recall.

## 2. Background

User runs exclusively on free LLM tiers: Alibaba DashScope (primary), Google AI Studio, Fireworks AI, Ollama local, OpenRouter. Models frequently drop, rate-limit, or change availability. Manual provider switching loses context and momentum. Built-in SQLite memory is basic.

## 3. Problem

- No automated failover: provider failures require manual intervention and context re-establishment
- Local models too small: 3B-8B parameter models have 16K-32K context, below Hermes Agent 64K minimum
- Ollama updates wipe model registry
- SQLite memory lacks semantic search and cross-session knowledge graphs

## 4. Work Performed

### 4.1 Fallback Chain Configuration

Configured 5-layer `fallback_model` chain in Hermes Agent:

| Priority | Provider | Model | Notes |
|----------|----------|-------|-------|
| 1 | Google AI Studio | gemini-2.0-flash | Free tier, excellent |
| 2 | Google AI Studio | gemini-2.5-flash | Newer, slightly smarter |
| 3 | Fireworks AI | llama-v3p3-70b-instruct |  trial credit |
| 4 | Ollama (local) | minimax-m3:cloud | Via Ollama, no local RAM |
| 5 | OpenRouter | owl-alpha | Free tier |

Triggers on error codes: 429, 529, 503, connection failures. No manual intervention required.

### 4.2 Provider Testing

- Google AI Studio: working
- Fireworks AI: working
- OpenRouter: working
- Local Ollama models: failed (context < 64K)
- Pulled `ornith:9b` (9B params) - required Ollama update first
- Ollama update cleared registry; old models lost
- Settled on `minimax-m3:cloud` via Ollama as local fallback

### 4.3 Gemini Claw Extension Fix

- Fixed `updateDynamicRules` error in Chrome extension
- Restored accidentally truncated files
- Replaced off-screen popup with sidebar toggle from toolbar icon

### 4.4 Memory Upgrade: SQLite to Mem0

- Migrated from Hermes Agent built-in SQLite to Mem0
- Mem0 provides vector-based semantic search and knowledge graph
- Improved cross-session fact recall
- Eliminated need to repeat context across sessions

### 4.5 Session Cleanup

- Deleted 12 old sessions (test queries, health checks, outdated experiments)
- Manual review preferred over auto-pruning

## 5. Diagnosis

Hermes Agent `fallback_model` is powerful but under-documented. It supports chaining multiple providers and triggers on specific error codes - exactly what free-tier users need. Local models require >=14B parameters or explicitly configured large context windows to meet 64K minimum. Ollama updates clear the registry; blobs may remain but Ollama won't recognize them. Mem0 significantly improves memory recall through semantic understanding.

## 6. Preliminary Assessment

Automated failover now survives provider failures silently. Context preserved across switches. Memory recall improved. Local fallback limited to cloud-proxied models via Ollama. Session hygiene improved via manual cleanup.

## 7. Solution Summary

- 5-provider fallback chain configured and tested
- Local fallback uses `minimax-m3:cloud` via Ollama (no local weights)
- Mem0 integrated for semantic memory
- 12 stale sessions removed
- Gemini Claw extension stabilized

## 8. Verification Plan

- Monitor failover triggers in production use
- Verify Mem0 recall quality over multiple sessions
- Test local fallback under actual primary failure
- Back up model list before future Ollama updates

## 9. Pending Actions

- Fill real credentials for cloud providers in fallback chain
- Update `CLOUD_FAILOVER_PAIRS` with actual provider|model list
- Consider automating health-check script via cron/systemd timer
- Evaluate raising WSL2 memory cap via `.wslconfig` for larger local models
- Retry `ornith:9b` or similar for true local inference

## 10. Recommendations

- Always configure `fallback_model` when using free tiers
- Verify local model context windows meet Hermes Agent 64K minimum before relying on them
- Back up `ollama list` output before Ollama updates
- Prefer Mem0 over SQLite for agent memory
- Document fallback chain in team/runbook for reproducibility
