# The Handoff File That Runs the Show (or: Task Management Finally Grows a Memory)

**Date:** 2026-09-18  
**Author:** Codebot  
**Topic:** manage-tasks, skill, task-management, session-handoff, rsync, decentralized-config, opencode

---

## 1. Objective (or: Stop Rescanning, Start Resuming)

For far too long, "start of session" meant the same dance: `tasks`, a pile of `.md` files,
summaries, and a shrug about what happened last time. This session fixed that. The goal was
to turn the session handoff into a **canonical, machine-readable snapshot** that the
`manage-tasks` skill reads at startup and rewrites at session end, so a fresh session starts
exactly where the old one stopped.

## 2. Background (or: What We Were Working With)

- Task files live in `~/.config/opencode/tasks/`, symlinked to the Windows hub at `/mnt/c/users/sigit/.config/opencode/tasks/` so all three hosts see the same folder.
- The `manage-tasks` skill (then v0.4) flat-scanned `*.md` and summarized them. No persistent state; the "handoff" was a manually maintained doc.
- A `done/` directory held finished tasks as `Done--*.md`; a `.archive/` held a few older stragglers. Two conventions, neither enforced by the skill.

## 3. Problem (or: Every Session Was a Cold Boot)

Three smells:

1. **The handoff was prose, not data.** Nothing parsed it; a session start re-read everything.
2. **Completion was all-or-nothing.** If a task had stray unchecked boxes in "In Progress" or "Completed", it looked unfinished even when its work was done.
3. **No archive rule.** "Finished" meant different things on different days.

## 4. Work Performed (or: The Three-Shift Refactor)

### 4.1 The Handoff Grows a JSON Brain

`next-session-handoff.md` is still markdown, but it now carries a `## Task Index
(managed by manage-tasks)` section whose content is a fenced JSON block:

```json
{
  "tasks": [
    { "file": "pending-decentralize-universal-setup.md", "status": "pending",
      "summary": "Drop shared hub; per-distro sync copies via new rsync --delete skill" }
  ]
}
```

Verified parseable with `python3 -m json.tool`. The JSON is the canonical list; everything
else in the file is still prose a human can read.

### 4.2 `tasks` Reads First, Scans Second

The startup command now:

1. Reads the handoff, extracts the JSON block, shows file + status + summary.
2. Cross-checks `ls ~/.config/opencode/tasks/*.md` and flags any `pending-*` /
   `Pending--*` file **not** in the JSON (a new task nobody indexed yet).
3. Falls back to a plain directory scan only if the JSON is missing.

Cross-check after the cutover: 15 indexed tasks, 12 pending-named files in the dir,
**zero** unindexed stragglers.

### 4.3 `session is done` Archives by the To Do Section Only

Completion is judged solely on the `## To Do` section: if **every** `- [ ]` there is
`- [x]`, the task is done. Checkboxes in "Completed", "In Progress", or arbitrary note
sections do not keep a task open. Verified with a synthetic fixture (`In Progress`
unchecked, `To Do` all checked -> done).

On session end the skill:

- Renames `Pending--X.md` -> `Done--X.md` and moves it to `.archive/` (the new convention;
  the legacy `done/` dir is left alone).
- Regenerates the JSON block from the remaining tasks.
- Rewrites the state sections (Current State / Completed Work / Pending Actions).
- **Preserves manual notes** outside the JSON block - only the fenced content is touched.

Nothing in the current 15-task set was archived this pass: every task still has open To Do
items, exactly as it should.

### 4.4 Two Task Files for the Road

- `pending-work-with-vibevoice.md` created from `/mnt/c/ai/models/vibevoice/CROSS_PLATFORM_NOTES.md`: build done 2026-09-18 (CPU-only ELF), wiring to `chat.home.arpa` TTS pending.
- `pending-decentralize-universal-setup.md` added as the live test task: dismantle the shared hub, give each distro its own copy, and build a new `rsync --delete` sync skill for `tasks/`, `skills/`, `application_architecture/`, `commands/`, `mem0/`, `archive-session/` (to merge into `sessions/`), and `vocab/` (location TBD).

## 5. Diagnosis (or: The Memory Problem Was a Format Problem)

Every symptom traced back to the same root: **state lived in prose no machine read.** The
moment the task index became structured JSON inside the handoff, the skill could treat the
file as a database instead of a wall of words.

## 6. Solution Summary (or: One File, Two Roles)

`next-session-handoff.md` is now simultaneously a human-readable handoff **and** a
machine-readable index. `manage-tasks` v0.5 is the keeper: read on `tasks`, write on
`session is done`, archive on completion, hands off clean state between sessions.

## 7. Verification (or: The Test You Can Replay)

The owner set up a live walkthrough:

1. Add a task (`pending-decentralize-universal-setup.md`).
2. Say `session is done`, exit.
3. In a fresh session, run `tasks`.

Expected: the new session opens with the handoff list including the new task. The JSON was
validated, the dir cross-check came back clean, and the regenerated snapshot (2026-09-18)
lists all 15 tasks. The fresh-session replay is the remaining checkbox.

## 8. Pending Actions (or: What the Machine Will Resume)

- Replay the test: fresh session -> `tasks` -> confirm the handoff list, including the new task.
- `pending-decentralize-universal-setup.md` is waiting: inventory hub folders, decide `vocab/`'s home, merge `archive-session/` into `sessions/`, design and write the `rsync --delete` sync skill, then migrate hosts off the hub symlinks.
- Once decentralized, update or retire the `universal-setup` skill that currently treats the hub as source of truth.

## 9. Recommendations (or: If It Recurs, Read This)

1. **Keep the JSON canonical.** Prefer regenerating it over hand-editing; stray hand edits get overwritten at the next `session is done`.
2. **Don't resurrect `done/`.** New completions go to `.archive/` as `Done--*`; leave old history where it sits.
3. **The sync skill is the risky part.** `rsync --delete` is only safe because the sync set is a closed list of managed folders - never point it at `~/.config/opencode/` wholesale.
4. **Verify the replay before trusting it.** The real test is a cold session, not this report.

---

*Generated by Big Pickle (OpenCode)*