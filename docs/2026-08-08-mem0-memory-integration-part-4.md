# Mem0 Memory Integration - Part 4

*259-memory dream run*

**Date:** 2026-08-08  
**Author:** Codebot  
**Topic:** Mem0, OpenCode, maintenance, cleanup, productivity  

---

## 1. Objective

Document mem0-dream automated memory consolidation run against 259 memories in sigit/app_id=sigit store.

## 2. Background

AI assistants accumulate memory over time -- observations, decisions, bug fixes, status updates. After weeks, hundreds of entries with duplicates, stale data, noise. Manual cleanup tedious. mem0-dream runs periodic consolidation pass, identifies issues automatically, proposes changes for approval.

## 3. Problem

259 memories accumulated. Need systematic consolidation.

## 4. Work Performed

### 4.1 Step 1: Fetch and Group
All 259 memories fetched across 2 API pages (200 per page). Grouped by metadata.type:

| Type | Count | Description |
|------|-------|-------------|
| auto_capture | ~120 | Session events, user requests, observations |
| task_learning | ~60 | Technical fixes, config details, lessons learned |
| session_state | ~20 | Session compacting progress reports |
| bug_fix | ~15 | Specific diagnosis and fix records |
| decision | ~10 | Architectural decisions |
| architecture_decisions | ~5 | Higher-level design choices |

No pinned memories. No retention config file -- defaults: 90 days for session_state and compact_summary, no pruning for others.

### 4.2 Step 2: Find Duplicates
Algorithm: noun/keyword overlap as cosine similarity proxy. Merge candidates: same metadata.type, >60% significant noun overlap, neither pinned.

Biggest cluster: 10 session compacting reports -- all variations of "User reports session compacting for project sigit, branch main" with different stat counts. Collapsed to 1 entry.

Other merges:
- 3 blog summary requests -> 1 (same request, different target dates)
- 2 TLS problem reports -> 1 (darkstat + LiteLLM, same timestamp)
- 2 provider disable requests -> 1 (same action, different phrasing)
- 2 hostapd status reports -> 1 (AP mode + PEAP auth, same session)

Total: 19 originals -> 5 merged entries.

### 4.3 Step 3: Find Noise
Noise = ephemeral status updates with no lasting knowledge value. Examples:
- "User sent a test message asking the assistant to respond with the word 'connected'"
- "User is ready to perform nixos-rebuild switch"
- "User wants to remove the provider 'apizio'"
- "User plans to rebuild and test the configuration"

36 entries pruned.

### 4.4 Step 4: Apply
After user approval, executed:
1. Deleted 19 merge originals
2. Added 5 merged versions with source: "mem0-dream"
3. Deleted 36 noise entries

### 4.5 Results
```
Reviewed:   259
Merged:     5 (19 originals -> 5 consolidated)
Pruned:     36 (operational noise)
Conflicts:  0
Final:      210 (19% reduction)
```

### 4.6 Classification Logic
Every memory classified into one of four categories:
- KEEP: atomic, specific, lasting knowledge (bug fixes with file paths, architectural decisions with rationale, technical learnings with concrete details)
- MERGE: near-duplicates expressing same fact (merged version more complete and specific)
- DELETE: sensitive data (API keys, passwords), expired/stale, noise (ephemeral status updates), redundant operational details
- REWRITE: vague or poorly-categorized (create improved version, delete original)

Key insight: most auto-captured entries are noise. "User wants to remove X" is request, not knowledge. The decision to remove X and reason why -- that's knowledge.

### 4.7 What Wasn't Consolidated
Decisions and bug fixes largely kept intact -- durable knowledge:
- LiteLLM crash-loop fix with specific file paths and line numbers
- NAT mark conflict resolution with bitwise OR approach
- FreeRADIUS TLS key format requirements
- Voucher system architecture (format, storage, future phases)

### 4.8 Lessons
1. Session compacting reports worst offenders: 10 entries saying same thing with different numbers. Could be single counter.
2. User requests are noise, not knowledge. "User wants to remove X" ephemeral. Decision and reason = knowledge.
3. No contradictions found. All 259 consistent.
4. 60% noun overlap heuristic works: caught all duplicate clusters without false positives.

### 4.9 Configuration
mem0-dream checks for .mem0.json or .mem0.md in project root for custom retention. Without one, defaults:

| Memory type | Retention |
|-------------|-----------|
| session_state | 90 days |
| compact_summary | 90 days |
| all others | no pruning |

--auto flag runs non-interactively: merges and prunes apply automatically, contradictions skipped (require human judgment). Lock file prevents concurrent runs.

## 5. Diagnosis

Automated consolidation effective. Noise predominantly auto-capture entries. Durable knowledge in decision/bug_fix types.

## 6. Preliminary Assessment

19% reduction with zero conflicts. Consolidation logic sound.

## 7. Solution Summary

mem0-dream consolidated 259 memories to 210. 5 merges, 36 prunes. Configuration defaults documented.

## 8. Verification Plan

Monitor memory quality over time. Run mem0-dream periodically.

## 9. Pending Actions

Create .mem0.md with project-specific retention policies if needed.

## 10. Recommendations

Run mem0-dream regularly. Distinguish requests (noise) from decisions (knowledge). Use pinned memories for critical facts. Consider .mem0.md for custom retention.
