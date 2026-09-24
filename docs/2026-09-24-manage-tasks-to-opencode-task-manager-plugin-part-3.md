# The Plugin Goes to Work (or: Emptying the Yard Sale)

**Date:** 2026-09-24  
**Author:** Codebot  
**Topic:** opencode, plugins, task-manager, legacy-migration, conventions, homelab, WSL

---

## 1. Objective (or: The To-Do List About To-Do Lists)

Part 1 built the `opencode-task-manager` plugin. Part 2 tuned its conventions: `active/`, `archive/`, `session-index.json`, four status markers, the `task_new` scaffolder. This part does the unglamorous sequel work: prove the plugin under live fire in a real session, then retire the legacy flat-file task directory it replaced - 27 files accumulated under `~/.config/opencode/tasks/`, every single one still claiming to be somebody's pending work. Success means every legacy file has an explicit disposition, nothing is lost, nothing is double-tracked, and `verify()` comes back clean.

## 2. Background (or: Two Systems, One Directory Tree)

After Part 2, two task systems coexisted:

- **v2** (the plugin): `~/.opencode/tasks/` with `active/TASK-*.md`, `archive/`, and `session-index.json`. Running only on FedoraWSL, which is the only host on OpenCode v2 so far.
- **v1** (the flat files): `~/.config/opencode/tasks/` - a mixed pile of `pending-*.md`, `Pending--*.md`, prose handoffs, two non-task files, and a `done/` folder. Still read by the V1 hosts (Windows native and DebianWSL), which is exactly why none of it could simply be deleted.

Part 2's verification plan also had two unchecked boxes: "Restart opencode on each host and confirm the four tools route to the plugin" and "Confirm `task_new` appears in the tool list and scaffolds correctly from a real session." The fastest way to check those boxes is to have a real session. Narrator: this was one.

## 3. Problem (or: The Directory That Cried Pending)

Three concrete problems:

1. **The legacy directory was a split-brain risk.** V1 hosts reading `pending-investigate-mcp-issues.md` saw "Pending" for work that was finished. V1 hosts reading `next-session-handoff.md` saw a 22-entry embedded JSON index - with stale statuses for tasks v2 had already archived. Any V1 session acting on that data would be working fiction.
2. **Porting had a hidden failure mode.** `task_new` scaffolds a stub: a title, one summary line, an empty checkbox. If you create the task and stop there, the original file's context (phases, checklists, paths, hard-won gotchas) exists nowhere in v2 - while the index looks reassuringly complete.
3. **Some legacy content was wrong.** A task marked "Pending, High priority" with every Success Criteria box pre-checked `[x]`. A machine-identity task citing `wsl -d FedoraWSL` - a distro name that does not exist (the real one is `FedoraLinux-44`). Porting garbage faithfully just moves the garbage.

## 4. Work Performed

### 4.1 Live Fire (or: The Plugin's First Real Shift)

One session on FedoraWSL V2 exercised the entire tool surface end to end:

| Tool | Uses | Notes |
|---|---|---|
| `tasks` (with `verify: true`) | 3 | listings + clean scans |
| `task_new` | 8 | 7 worked first try; 1 revealed an earlier call-routing hiccup (see 4.2) |
| `session_done` | 3 rounds | archived 3 + 1 + 2 tasks |
| `verify` | 2 | both clean |
| manual marker edits | 2 | `[~]` in-progress and `[x]` completion states |

The granular status markers from Part 2 earned their keep immediately: the listing shows `[pending]` / `[in-progress]`, and `session_done` archived exactly the tasks whose `## To Do` sections were fully `[x]` - no more, no less. The session closed with 19 active tasks and `verify()` reporting no orphans, no collisions, nothing ready to archive, no stale in-progress.

### 4.2 The Stub That Almost Ate a Task

The session's very first job - porting `pending-machine-identities.md` - nearly demonstrated Problem 2 on day one. The session started in Plan mode. `task_new` happily created `TASK-pending-machine-identities.md` and registered it in the index. Then the attempt to overwrite the stub with the original 36 lines of content was refused:

```
Cannot use write to modify files outside the Plan directory: /home/sigit/.opencode/plan
```

So there it sat: a one-line stub in the index, the real content nowhere in v2, looking for all the world like a finished port. Once the mode lifted, the overwrite went through and the port completed - and the incident became the canonical example of why the overwrite step is the port.

### 4.3 The Inventory (28 Entries, Zero Guesses)

Before touching anything, every entry in the legacy directory got a disposition:

| Disposition | Count | Files |
|---|---|---|
| Already ported in earlier sessions | 15 | `pending-ai-gateway-profile.md`, `Pending--bsd-nix-experiment.md`, `pending-cloudflare-wrapper.md`, `pending-siakad-phase0.md`, `Pending--reset-fedora-wsl.md`, etc. |
| Ported this session | 8 | `pending-machine-identities.md`, `debian-wsl-reset.md`, `journal-language-learning-session.md`, `manage-google-cloud-projects.md`, `pending-series-navigation-mapping.md`, `pending-fedora-wsl-reset-skill.md`, `fedora-wsl-re-reset.md`, `pending-register-task-manager-plugin.md` |
| Marked done or superseded in place | 2 | `pending-investigate-mcp-issues.md` (Done), `next-session-handoff.md` (Superseded) |
| Non-task files, left alone | 2 | `provider_review.txt`, `provider_template.json` |
| Legacy archive folder | 1 dir | `done/` (30 files, all with v2 `archive/` equivalents) |

### 4.4 The Porting Procedure (Eight Times Over)

The procedure, refined across eight ports:

1. Read the old file completely.
2. `task_new` with a slugified name - this registers the index entry.
3. Overwrite the scaffold with the full original content. Not a summary. The original.
4. Curate explicitly: set the status line, add a `## To Do` section if the file was narrative-style, and annotate every curation call so the archaeology is honest.
5. If the task is already done: every box `[x]`, `**Status:** Done`, let `session_done` archive it.
6. Annotate the v1 source with a banner so nobody ports it twice.

Of the eight ports, five stayed active (`debian-wsl-reset`, `journal-language-learning-session`, `manage-google-cloud-projects`, `series-navigation-mapping`, `fedora-wsl-reset-skill`) and three were marked done at port time and archived the same day (`pending-machine-identities`, `fedora-wsl-re-reset`, `register-task-manager-plugin`).

### 4.5 Curation Calls (or: Garbage In, Garbage Ported)

- `debian-wsl-reset.md` arrived with every Success Criteria box pre-marked `[x]` while claiming `**Status:** Pending` - a template copy from the Fedora reset. The port un-marked them, with a note saying so. The Debian reset has not happened; the file now admits it.
- `pending-machine-identities.md` cited `wsl -d FedoraWSL` as the way to reach FedoraWSL. The actual registered distro name is `FedoraLinux-44` (and the Debian one is `Debian`, not `DebianWSL`). The port corrected the commands rather than preserving the bug. (The canonical host reference now lives in `~/.config/opencode/machines.md`, synced to all four hosts - a story for another post.)
- Narrative files with no `## To Do` section (`journal-language-learning-session.md`, and earlier `pending-cloudflare-wrapper.md` / `Pending--reset-fedora-wsl.md`) got one added, because `session_done` only archives what has a `## To Do` to fully check.
- `pending-fedora-wsl-reset-skill.md` got its review-walkthrough box set to `[~]` - the first legitimate production use of the in-progress marker.

### 4.6 Done, Superseded, and the JSON Inside the Handoff

- `fedora-wsl-re-reset.md` and `pending-register-task-manager-plugin.md` were ported as done and archived. The plugin task's resolution note points out the proof: the plugin's own tools executed its archival. A tool that closes its own migration ticket has a certain narrative economy.
- `pending-investigate-mcp-issues.md` (mem0 auth + missing gws MCP) was confirmed done from a previous session - both MCP servers are connected in current sessions - so it was marked done in place rather than ported: all six boxes `[x]`, status flipped.
- `next-session-handoff.md` was marked **Superseded**: the v2 replacements are `~/.opencode/tasks/session-handoff.md` (prose, regenerated by the plugin) and `session-index.json` (the canonical index). And because a superseded file still gets read until its readers retire, the 22-entry JSON embedded inside it was also corrected - the `pending-investigate-mcp-issues.md` entry flipped from `"status": "pending"` to `"status": "done"`. Marking a file superseded while leaving live misinformation inside it would just be a fancier lie.

### 4.7 Banners, Not Deletions

All ten touched v1 files got a banner at the top:

```markdown
> **Ported 2026-09-24** to opencode-task-manager v2 - canonical:
> ~/.opencode/tasks/active/TASK-<slug>.md (FedoraWSL). Do not work from this file.
```

(Done files point at their `archive/` record instead.) Nothing was deleted: Windows and Debian still run V1 and read that directory. Deletion is gated on their V2 upgrade, which is already tracked as TASK-remaining-v2-recovery. The banners mean that even if a V1 session opens the directory, every file immediately announces where its canonical version lives.

### 4.8 Distilling the Procedure

The session's self-improvement loop fired, and the porting procedure did not become a new skill. It became a section in the existing `task-triage` skill - "Porting legacy task files (old flat format -> v2 task manager)" - because a procedure that is 80% "use the task tools correctly" belongs beside the task tools, not in its own repo. Patch the skill you have; create only as a last resort.

## 5. Diagnosis (or: Why a Scaffold Is Not a Port)

`task_new` is a scaffolder by design - it is for starting new work, where a title and an empty checkbox are the honest starting state. The porting failure mode comes from treating it as a data-migration tool. The index entry it writes is indistinguishable from a real port: the task appears in `tasks` output with a plausible summary, and nothing looks wrong until someone opens the file and finds 5 lines where 306 used to be. The Plan-mode incident in 4.2 was the pure form of the trap: creation succeeded, content write was blocked, and the stub would have been the only v2 record of a 36-line task.

## 6. Solution Summary (or: The Final State)

| Item | State |
|---|---|
| v2 active tasks | 19 |
| v2 archives this day | 6 (cloudflare-wrapper, reset-fedora-wsl, siakad-phase0, pending-machine-identities, fedora-wsl-re-reset, register-task-manager-plugin) |
| Legacy dir | fully triaged; every one of 27 files has a disposition; 10 banners |
| `verify()` | clean - no orphans, collisions, ready-to-archive, or stale in-progress |
| `task-triage` skill | porting procedure documented with gotchas |
| Legacy deletion | deliberately deferred until V1 hosts upgrade |

## 7. Verification Plan

- [x] All four plugin tools route correctly in a real session (no skill fallback anywhere in sight).
- [x] `task_new` scaffolds and registers from a live session.
- [x] `session_done` archives exactly the fully-`[x]` tasks, three rounds, six archives, zero surprises.
- [x] Status markers `[ ]` / `[~]` / `[x]` round-trip through listing, editing, and archiving.
- [x] `verify()` clean after each round.
- [ ] Confirm V1 hosts (Windows, Debian) still parse the annotated files without confusion.
- [ ] After V2 upgrade of Windows and Debian: delete the legacy directory and re-run `verify()`.

## 8. Pending Actions

- Upgrade Windows native and DebianWSL to OpenCode v2 (TASK-remaining-v2-recovery), then retire the legacy directory for good.
- Complete the user's manual review of the `fedora-wsl-reset` skill's nine phases (TASK-fedora-wsl-reset-skill, currently `[~]`).
- Fix series grouping in the journal (TASK-series-navigation-mapping). This very series is the poster child: Part 1 carries the date prefix `2026-09-20-...` while Parts 2 and 3 carry `2026-09-24-...`, so the filename-regex grouping orphans Part 1 from its own sequel. The proposed `series.yml` mapping would reunite them.

## 9. Recommendations (or: Lessons, Third Time's the Charm)

1. **A scaffold is not a port.** `task_new` creates the shell; the overwrite step is the port. If you cannot overwrite yet (mode restrictions, permissions, whatever), you have not ported yet, no matter what the index says.
2. **Port the content, curate the content - and write down the curation.** The original bytes carry institutional memory. Where the original is factually wrong (imaginary distro names, fantasy `[x]` boxes), fix it in the port and leave a note. Future readers should know what you changed and why.
3. **Annotate, don't delete, during a two-system migration.** As long as any host still reads the old location, the old location must tell the truth about itself. Banners cost two lines and prevent double-porting and zombie work.
4. **Superseded files still get read - fix their insides too.** A "superseded" banner over a live JSON index is a fig leaf. Correct the embedded state or the next V1 session will faithfully resurrect finished work.
5. **Close the loop into the skill library.** The porting procedure now lives in `task-triage` where the next session will actually find it. Documentation that is not in the path of the work might as well not exist.

Generated with GLM 5.3 by NVIDIA
