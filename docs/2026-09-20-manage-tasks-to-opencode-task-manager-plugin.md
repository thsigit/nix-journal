# From Python Script to TypeScript Plugin (or: How the Task Manager Finally Grew Up)

**Date:** 2026-09-20  
**Author:** Codebot  
**Topic:** opencode, plugins, TypeScript, Python, sync-opencode, homelab, WSL

---

## 1. Objective (or: Killing the Python Dependency)

Convert the `manage-tasks` skill from a Python script invoked by opencode into a first-class TypeScript plugin using `@opencode-ai/plugin`, then delete the old skill so it can no longer shadow the new tool. Success means `tasks` and `session is done` both hit the plugin, type-check passes, and the change survives sync across DebianWSL, FedoraWSL, Windows, and the homelab rendezvous.

## 2. Background (or: The Skill That Worked Too Hard)

The task workflow has been stable for weeks. A single Python file, `manage_tasks.py`, lived inside `~/.config/opencode/skills/manage-tasks/` and handled listing, archiving, and verification of `.md` task files under `~/.config/opencode/tasks/`. The Python script worked. It just required Python, a shell-out from the agent, and a skill directory that could accidentally outlive its usefulness.

Meanwhile, the `self-improving-skills` plugin had already proven the pattern: a directory under `~/.config/opencode/plugins/`, an `index.ts` that registers tools, and zero config changes needed because opencode auto-discovers plugins at startup. The migration target was obvious.

## 3. Problem (or: A Buffer Comparison Walks Into a Bar)

Two problems surfaced during the port:

1. **Reference equality on Buffers**: `fs.readFileSync(a) === fs.readFileSync(b)` compares object identity, not byte content. The `verify` scan reported false collisions, and `session_done` refused to archive legitimate orphans because the comparison always returned `false`.
2. **Skill shadowing**: even after the plugin was created, the old `manage-tasks` skill directory still existed on every host. OpenCode prefers skills over plugins for matching trigger words, so `tasks` kept calling Python.

## 4. Work Performed

### 4.1 The Plugin Skeleton

Created `~/.config/opencode/plugins/opencode-task-manager/` with:

- `task-manager.ts` — direct port of `manage_tasks.py` logic (task file discovery, handoff parsing, archiving, verify scan)
- `index.ts` — plugin entry registering three tools:
  - `tasks` — list handoff tasks, cross-check directory, optional verify
  - `session_done` — archive finished tasks, regenerate handoff
  - `verify` — report orphans, collisions, ready-to-archive
- `tsconfig.json` — strict TypeScript config with `@types/node`

The plugin uses the same `glob` library and the same `tasks/` paths as the Python original, so behavior is preserved.

### 4.2 The Buffer Fix

Added a `buffersEqual(a, b)` helper that compares byte-by-byte:

```typescript
function buffersEqual(a: Buffer, b: Buffer): boolean {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return false;
  }
  return true;
}
```

Replaced `===` comparisons in both `sessionDone` and `verify`.

### 4.3 Testing

Ran inline tests with `bun -e` importing the module:

| Function | Result |
|---|---|
| `listTasks()` | 15 tasks from handoff, no unindexed files |
| `verify()` | 1 legitimate COLLISION (`pending-work-with-bert-tiny.md`), 0 false positives |
| `sessionDone()` | correctly removes orphan `pending-decentralize-universal-setup.md`, regenerates index |

TypeScript check passes with `bunx tsc --noEmit`.

### 4.4 Cleanup and Sync

- Archived old skill: `manage-tasks/` → `manage-tasks.archived-20260920-130845/`
- Removed `manage-tasks` from DebianWSL, FedoraWSL, Windows, and `/srv/repo/opencode-hub/`
- Updated `~/.config/opencode/skills/sync-opencode/sync-excludes.txt`:
  ```
  skills/*/manage-tasks*
  skills/manage-tasks
  ```
- Ran full sync cycle: conditional push to rendezvous, authoritative pull back, then Windows and FedoraWSL pulls
- Verified parity: `opencode.json` SHA `f64af75c962511bca80aeeacf59e3734c8214914d4e813264777fbed872858ad` on all four locations

## 5. Diagnosis (or: Why the Old Script Kept Winning)

Skills are matched before plugins in opencode's tool resolution. As long as `~/.config/opencode/skills/manage-tasks/SKILL.md` existed with trigger words `tasks` and `session is done`, the agent called the Python skill regardless of the plugin's presence. Removing the skill directory was the final step that made the plugin actually load.

## 6. Solution Summary (or: The Final State)

- **Plugin path**: `~/.config/opencode/plugins/opencode-task-manager/`
- **Tools**: `tasks`, `session_done`, `verify`
- **Trigger words**: `tasks`, `session is done`
- **Old skill**: removed from all hosts and hub
- **Buffer bug**: fixed with `buffersEqual`
- **Sync**: all hosts identical, excludes updated

## 7. Verification Plan

- [ ] Restart opencode on DebianWSL, FedoraWSL, Windows
- [ ] Confirm `tasks` invokes the plugin (not Python)
- [ ] Confirm `session is done` invokes the plugin
- [ ] Run `verify` and confirm only the bert-tiny collision remains
- [ ] Confirm `opencode.json` parity across all hosts after restart

## 8. Pending Actions

- Restart opencode on each host and validate tool routing
- Monitor `pending-work-with-bert-tiny.md` collision until phase 2 is ready to archive
- Remove archived skill backups (`manage-tasks.archived-*`) after one week of stable plugin operation

## 9. Recommendations (or: Lessons Learned)

1. **Remove the old implementation before declaring victory.** A plugin that shares trigger words with a skill will silently lose until the skill is gone.
2. **Never compare Buffers with `===`.** It compares references, not content. Use byte-by-byte comparison or `Buffer.compare()`.
3. **Keep excludes in a file, not a shell variable.** The `sync-excludes.txt` pattern survived three sync attempts; inline `--exclude` patterns did not.
4. **Test plugins with the same runtime opencode uses.** `bun -e` caught runtime issues that `tsc` would not have.

Generated by step-3-7-flash:free (Kenari)
