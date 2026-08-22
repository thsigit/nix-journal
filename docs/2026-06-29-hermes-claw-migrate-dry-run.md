# Hermes Agent Claw Migrate Dry Run

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** Hermes Agent, openclaw, migration, cli  

## 1. Objective

Execute and document a dry-run of `hermes claw migrate` to import settings, memories, skills, and API keys from an OpenClaw installation into Hermes.

## 2. Background

`hermes claw migrate` is a first-class subcommand for migrating from OpenClaw to Hermes. Siblings: `migrate` (import) and `cleanup` (archive old install). Flags: `--dry-run`, `--preset {user-data,full}`, `--migrate-secrets`, `--overwrite`, `--no-backup`, `--skill-conflict`, `--source`. Defensive by default: preview, backup, ask before overwrite.

## 3. Problem

Uncertainty about what `hermes claw migrate` does and whether a viable OpenClaw installation exists at the default source path (`~/.openclaw`).

## 4. Work Performed

### 4.1 Command Discovery

Queried Hermes Agent for command details. Confirmed `claw` is a first-class subsystem with three subcommands (`migrate`, `cleanup`, `clean`) and dedicated `--migrate-secrets` gate.

### 4.2 Mode Selection

User chose dry-run only (sensible for orientation).

### 4.3 Dry-Run Execution

`hermes claw migrate --dry-run` output: single clean table. All 34 migration categories reported "source not found."

### 4.4 Manual Verification

`ls -laR ~/.openclaw`: directory exists but nearly bare. Only `state/` subdirectory with `state/openclaw.sqlite` (1 MB). No config, skills, memories, settings, provider keys. Migrator didn't recognize SQLite file as source for any of 34 categories.

## 5. Diagnosis

No viable OpenClaw installation at default path. The 1 MB SQLite file may contain state but is not on migrator's import list. Migration tool worked correctly: scanned, found nothing acceptable, stopped without modifications or backup.

## 6. Preliminary Assessment

Dry-run completed safely. No harm, no side effects, complete answer. Tool behaves as designed.

## 7. Solution Summary

- `hermes claw migrate --dry-run` executed
- All 34 categories: "source not found"
- Manual verification confirms empty OpenClaw directory
- No changes made, no backup written

## 8. Verification Plan

- If real OpenClaw install exists elsewhere, use `--source /path/to/.openclaw`
- SQLite file may be inspectable with SQLite tools
- After real migration: `hermes claw cleanup` archives leftover OpenClaw directory
- Note: `hermes migrate` is separate (config.yaml rewrite for deprecated models, e.g., xAI retirement May 15, 2026)

## 9. Pending Actions

- None unless real OpenClaw source located

## 10. Recommendations

- Always start migration with `--dry-run`
- Use `--source` to point at non-default OpenClaw locations
- `--migrate-secrets` is a deliberate opt-in for API keys
- `hermes claw cleanup` handles post-migration archival
- `hermes migrate` is unrelated (deprecated model config rewrite)
