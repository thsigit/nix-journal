# Tuning the Task Manager Plugin (or: The Conventions Grew Up Too)

**Date:** 2026-09-24  
**Author:** Codebot  
**Topic:** opencode, plugins, TypeScript, task-manager, conventions, homelab, WSL

---

## 1. Objective (or: Finishing What Part 1 Started)

Part 1 got the `opencode-task-manager` plugin loaded and killed the Python dependency. This part tunes the conventions the plugin enforces: rename the handoff, consolidate the messy prefix zoo, split the task index out of the prose, add four status markers, and bolt on seven quality-of-life improvements. Success means the plugin reads the new layout, the old `done/` folder is gone, and `session-index.json` is the single source of truth.

## 2. Background (or: The Prefix Zoo We Inherited)

After Part 1, the task directory looked like a yard sale:

- Active tasks carried one of two prefixes: `pending-` or `Pending--` (yes, two different strings for the same concept, because consistency is for the weak).
- Completed tasks lived in `done/` as `Done--<name>.md` (a third prefix, naturally).
- The canonical task list was a fenced JSON block buried inside `next-session-handoff.md`, welded to the prose so tightly that regenerating it meant rewriting prose.
- The handoff filename started with `next-`, a word that means nothing once the session it hands off to is already the current one. Narrator: it was confusing.

The plugin logic in `task-manager.ts` mirrored all of this: `PREFIXES = ["pending-", "Pending--"]`, `DONE_PREFIX = "Done--"`, and a `HANDOFF` path pointing at `next-session-handoff.md`.

## 3. Problem (or: A Place For Everything, But Also Five Other Places)

Four concrete problems with the as-shipped conventions:

1. **Dual active prefixes** (`pending-` vs `Pending--`) meant two code paths to strip and two places to forget one.
2. **Index welded to prose**: `session-handoff.md` held both human notes and the machine-readable task list, so any prose edit risked corrupting JSON, and vice versa.
3. **Binary status only**: a task was either `[ ]` or `[x]`. "I started this" and "this is blocked" had no first-class marker, so `verify` could not tell a stuck task from a fresh one.
4. **No scaffolding or safety**: creating a task meant hand-writing a file plus manually editing JSON; archiving twice in a day would collide on the filename; and two hosts writing `session-index.json` concurrently could clobber each other.

## 4. Work Performed

### 4.1 Renaming the Handoff

The file `next-session-handoff.md` became `session-handoff.md` (the `next-` prefix was meaningless). Updated the `HANDOFF` constant and `HANDOFF_NAME` in `task-manager.ts`, plus the tool descriptions in `index.ts`. The on-disk file was `mv`-ed and the embedded JSON was lifted out into a separate `session-index.json`.

### 4.2 Consolidating the Prefix Zoo

Killed all three prefixes. Active tasks now live in an `active/` subdirectory, every file named `TASK-<slug>.md` (one prefix, lowercase slug). Completed tasks move to `archive/` as `TASK-<name>_YYYY-MM-DD.md`. The plugin constants collapsed to a single `TASK_PREFIX = "TASK-"`.

A migration script (`python3` + `shutil`) did the heavy lifting:

| Source | Destination | Count |
|---|---|---|
| `pending-*` / `Pending--*` in tasks root | `active/TASK-*.md` | 17 |
| `done/Done--*` | `archive/TASK-<name>_2026-09-21.md` | 31 |
| embedded JSON in handoff | `session-index.json` | 1 |
| old `done/` directory | removed | - |

### 4.3 Four Status Markers

Added a `deriveStatus()` function that reads the `## To Do` checkbox markers and returns a granular state:

| Marker | Status | Meaning |
|---|---|---|
| `[ ]` | pending | not started |
| `[~]` | in-progress | started, not done |
| `[x]` | completed | all boxes checked -> archived by `session is done` |
| `[!]` | blocked | waiting on something external |

`isDone()` still requires every box to be `[x]`, so completion semantics are unchanged.

### 4.4 Seven Plugin Improvements

All seven accepted recommendations were implemented in `task-manager.ts` and `index.ts`:

1. **Status field reflects granular markers** - `listTasks()` prints `[status]` per task.
2. **Timestamps in the index** - each entry carries `created` and `updated` (from file stat).
3. **`session is done` appends handoff prose** - writes a `## Session archived (DATE)` block to `session-handoff.md`.
4. **Startup directory guard** - `ensureDirs()` creates `BASE`/`active`/`archive` on load.
5. **`task_new` tool** - scaffolds `active/TASK-<slug>.md` with a `## To Do` template and registers it in the index.
6. **Collision-safe archive dates** - `archiveDest()` adds a `_N` suffix when a same-day archive already exists.
7. **Cross-host sync awareness** - `writeIndex()` writes `session-index.json.tmp` then `rename`s, so concurrent hosts cannot clobber the index mid-write.

### 4.5 The Bug We Almost Shipped

While testing the archive collision logic, `sessionDone()` archived nothing. Root cause: `todoSection()` sliced the file content starting one character too early, so the first line of the section was ` [x] done` (leading space) instead of `- [x] done`. The marker regex `-\s+\[.\]` then failed to match, `isDone()` returned `false` for every task, and `session is done` would have silently kept all tasks. Fixed by slicing after the header newline. This was a latent bug in the Part 1 port - the Python original sliced correctly; the TypeScript rewrite did not.

## 5. Diagnosis (or: Why the Old Slice Ate the Dash)

The Python `manage_tasks.py` used `content.split("## To Do", 1)[1]` then skipped to the next line. The TypeScript port tried to be clever with an index offset (`header + (content[header+10] === "\n" ? 11 : 10)`) that assumed the header was exactly `# To Do` (10 chars). But headers are `## To Do` (11 chars) or longer with surrounding whitespace, so the offset landed on the space before the first `-`. Clever, meet fragile.

## 6. Solution Summary (or: The Final State)

- **Handoff**: `session-handoff.md` (prose only) + `session-index.json` (canonical list, atomic write).
- **Layout**: `active/TASK-*.md` for work, `archive/TASK-<name>_DATE.md` for history.
- **Status**: `[ ]` / `[~]` / `[x]` / `[!]` -> pending / in-progress / completed / blocked.
- **Tools**: `tasks`, `task_new`, `session_done`, `verify` (four now, was three).
- **Index entries**: `file`, `status`, `summary`, `created`, `updated`.
- **Latent slice bug**: fixed.

## 7. Verification Plan

- [x] `rebuildIndex()` returns 17 tasks with `created`/`updated` timestamps.
- [x] `listTasks()` shows `[status]` and `(updated YYYY-MM-DD)` per task.
- [x] `verify()` reports clean (no orphans, collisions, ready-to-archive, or stale).
- [x] `newTask()` round-trips: creates `active/TASK-<slug>.md` and registers it, then cleanup removes it and rebuilds.
- [x] `sessionDone()` archive collision test: same-day second archive lands as `TASK-<name>_DATE-2.md`.
- [x] `todoSection` fix confirmed: `- [x]` now matches, so `isDone()` detects completion.
- [ ] Restart opencode on each host and confirm the four tools route to the plugin.
- [ ] Confirm `task_new` appears in the tool list and scaffolds correctly from a real session.

## 8. Pending Actions

- Restart opencode on DebianWSL, FedoraWSL, Windows to load the new `task_new` tool and `active/`/`archive/` layout.
- Run `verify` on each host to confirm no orphans from the migration.
- Decide whether `session-handoff.md` historical "Completed Work" section (lines referencing old `Done--` names) should be pruned or kept as archaeology. Current call: keep, it is accurate for its date.
- Monitor the new `STALE_DAYS = 7` flag: confirm `verify` surfaces genuinely stuck in-progress tasks, not just quiet ones.

## 9. Recommendations (or: Lessons, Again)

1. **Off-by-one slices are silent killers.** The bug archived nothing and would have looked like "no tasks done" forever. Test the completion path, not just the listing path.
2. **One prefix, one place.** Collapsing `pending-` / `Pending--` / `Done--` into a single `TASK-` prefix deleted an entire class of string-matching bugs. Boring is better.
3. **Separate machine state from human prose.** The JSON-in-markdown handoff was a trap. A standalone `session-index.json` is easier to regenerate, diff, and debug.
4. **Atomic writes for shared files.** `tmp` + `rename` is the cheapest insurance against two hosts fighting over `session-index.json`.
5. **Test with the same runtime opencode uses.** `bun -e` caught the slice bug and the collision path; `tsc` would have shrugged.

Generated with Hy3 (Free) by Kenari
