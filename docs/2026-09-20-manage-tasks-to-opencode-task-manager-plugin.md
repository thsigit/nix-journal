# 2026-09-20—manage-tasks-skill-to-opencode-task-manager-plugin

## Summary
Converted `manage-tasks` skill (Python) to native OpenCode plugin `opencode-task-manager` in TypeScript, removed Python dependency, fixed buffer comparison bug, cleaned legacy artifacts, synced to all hosts.

## Context
The task management workflow relied on a Python skill `manage-tasks` with triggers `tasks` and `session is done`. The skill worked correctly but required Python and manual script invocation. The goal was to migrate to a TypeScript plugin using `@opencode-ai/plugin` Tool API, matching the pattern used by existing plugins (e.g., self-improving-skills).

## Changes
- **Created plugin** `~/.config/opencode/plugins/opencode-task-manager/`
  - `task-manager.ts` — core logic ported from `manage_tasks.py` (~9.5KB)
  - `index.ts` — plugin entry exposing `tasks`, `session_done`, `verify` tools
  - `tsconfig.json` — strict TS config, type-check passes
- **Bug fix**: Buffer comparison was `===`, now byte-by-byte `buffersEqual`
- **Cleanup**: Removed `manage-tasks` skill from DebianWSL, FedoraWSL, Windows, hub
- **Sync**: Updated `sync-excludes.txt` to exclude legacy skill backups, synced via `sync-opencode`

## Test results
- `listTasks()` — 15 tasks displayed, no unindexed files
- `verify()` — reports legitimate COLLISION for bert-tiny only
- `sessionDone()` — correctly archives orphan `pending-decentralize-universal-setup.md`
- TypeScript `bunx tsc --noEmit` passes
- Parity verified: `opencode.json` SHA identical across all hosts

## Files
- Plugin: `~/.config/opencode/plugins/opencode-task-manager/`
- Sync config: `~/.config/opencode/skills/sync-opencode/sync-excludes.txt`
- Handoff: `~/.config/opencode/tasks/next-session-handoff.md`

## Next
Restart opencode on each host, verify tools respond via natural language.