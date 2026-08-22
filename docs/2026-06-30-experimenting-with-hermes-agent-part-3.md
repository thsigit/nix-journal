# Experimenting with Hermes Agent - Part 3

*SQLite session cleanup + reusable skill*

**Date:** 2026-06-30  
**Author:** Codebot  
**Topic:** Hermes Agent, sessions, SQLite, maintenance, skills  

## 1. Objective

Delete unused Hermes Agent sessions from SQLite database and create a reusable skill for future session cleanup operations.

## 2. Background

Hermes Agent stores sessions in ~/.hermes/state.db with tables: sessions, messages, FTS5 mirrors, compression_locks, state_meta, schema_version. No built-in delete command existed. User had 26 sessions including several titled "delete this", "delete this 2", etc., and low-message experiments cluttering history.

## 3. Problem

No native session deletion capability in Hermes. Manual SQL required with proper FK ordering (messages before sessions) and FTS5 index synchronization. Need to identify candidates, confirm deletions, execute safely, and encapsulate as reusable skill.

## 4. Work Performed

### 4.1 Database Inspection
- Located ~/.hermes/state.db
- Listed tables and schemas including FTS5 triggers (messages_fts_delete, messages_fts_trigram_delete)
- Queried sessions ordered by started_at DESC, presented 26 rows categorized as titled-for-deletion and empty-title low-message experiments

### 4.2 Session Deletion
- Executed batched DELETE in two passes: messages first, then sessions (FK order requirement)
- Deleted 12 confirmed session IDs
- Verified new total: 14 sessions (down from 26)
- FTS5 search index maintained consistency automatically via existing triggers

### 4.3 Skill Creation
- Authored cleanup-sessions skill at ~/.hermes/skills/productivity/cleanup-sessions/SKILL.md
- Skill encodes workflow: list candidates (empty titles or message_count <= 2), present, ask which to delete, run DELETEs in FK order, report new count
- Captures FK-ordering pitfall explicitly

### 4.4 Inventory Verification
- Counted skills: 70 total (69 built-in, 1 custom: cleanup-sessions)

## 5. Diagnosis

Manual SQL deletion is error-prone due to FK constraints and FTS sync requirements. Encapsulating in a skill ensures consistent, repeatable cleanup. The skill is intentionally small (60 lines) - single purpose with explicit pitfall documentation.

## 6. Preliminary Assessment

Database is 12 rows lighter and easier to navigate. FTS5 index consistent. Next invocation of "cleanup sessions" or similar triggers should activate the skill automatically. No periodic cron sweep configured yet.

## 7. Solution Summary

- Inspected database schema and FTS triggers
- Identified and deleted 12 unused sessions via batched SQL
- Created reusable cleanup-sessions skill
- Verified skill inventory (70 total, 1 custom)

## 8. Verification Plan

- Run "cleanup sessions" command to verify skill triggers
- Confirm FTS counts match messages count
- Verify no orphaned FTS entries

## 9. Pending Actions

- Consider adding periodic cron to sweep empty sessions automatically

## 10. Recommendations

- Keep skills small and single-purpose
- Document sharp edges (FK ordering) explicitly in skill
- Verify FTS trigger behavior before manual deletions