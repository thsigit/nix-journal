# The Hub Is Dead, Long Live the Rendezvous (or: How I Learned to Stop Worrying and Love Conditional Push)

**Date:** 2026-09-19  
**Author:** Codebot  
**Topic:** opencode, decentralization, rsync, sync-opencode, homelab, WSL, configuration management

---

## 1. Objective (or: What We Were Even Doing Here)

Take the "universal setup" - a single shared config hub at `/mnt/c/users/sigit/.config/opencode/` that FedoraWSL and DebianWSL reached through symlinks - and kill it. The goal was simple to state and surprisingly painful to achieve:

- Each environment (Windows native, FedoraWSL, DebianWSL) keeps its **own real copy** of the opencode config.
- There is **no single source of truth** on any host. A homelab repo plays a passive **rendezvous** where hosts meet to exchange changes.
- A new skill (`sync-opencode`) owns the rsync dance, with `--delete` semantics that cannot eat data.
- Everything verified by parity checks: same `opencode.json`, same skills/tasks, zero symlinks remaining.

Spoiler: the "simple" sync algorithm took three attempts in live testing before it stopped destroying files. That is the good part of this story.

## 2. Background (or: Meet the Shared Hub It Was Built On)

Until this session, the opencode config lived in one Windows directory, and the two WSL distros got there via symlinks. It "worked" in the sense that everyone read the same files - and everyone was exposed to the same single point of failure, plus the usual symlink weirdness (a deleted distro having dangling links, a broken symlink silently pointing at a file that just left orbit).

The setup inventory found:

| Item | Where it lived | Fate |
|---|---|---|
| `opencode.json` + per-OS overlays | hub root | overlays become local-only |
| `skills/` (31 dirs + README) | hub | sync set |
| `tasks/` (16 tasks) | hub | sync set |
| `application_architecture/`, `commands/` | hub | sync set |
| `sessions/` + `export-session.py` | hub | sync set |
| `archived-session/` (kebab export) | hub | merged into `sessions/`, folder deleted |
| `mem0/` | hub | sync set |
| `vocab/` | hub | moved to central `/srv/repo/vocab/` |
| `node_modules/`, `package*.json`, `scripts/` | hub | local-only, excluded from sync |

A quick drift scan during inventory found Debian had silently lost its `commands` + `vocab` symlinks. The hub was already rotting around the edges.

## 3. Problem (or: Three Ways to Delete Someone's Homework)

The design tension: `rsync --delete` is exactly the tool you want for mirroring, and exactly the tool that deletes your data if the source is stale or the excludes are wrong. We needed a bidirectional single-user sync between three hosts with one passive rendezvous. Naive approaches failed in three distinct, live, reproducible ways:

1. **Pull-then-push with `--delete` on both legs**: the *pull* deleted a brand-new local file (not yet on the hub) before the *push* could send it.
2. **Push-then-pull with `--delete` on both legs**: a *stale host* that had not yet received a newer hub file deleted it from the hub during its push.
3. **Inline `--exclude` patterns from a shell variable**: quoting/glob-expansion nightmares made `--delete` dangerous. The fix is a static exclude file.

## 4. Work Performed

### 4.1 The Decisions (Democracy by Question Tool)

Four calls needed user input, all resolved quickly:

| Decision | Outcome |
|---|---|
| `vocab/` location | new central `/srv/repo/vocab/` on homelab |
| `mem0/` placement | under the rendezvous `/srv/repo/opencode-hub/mem0/` (cloud mem0 remains the memory sync mechanism) |
| Sync model | hub-relay pull-then-push ... later corrected to conditional-push + authoritative-pull (see 4.6) |
| `archived-session/` | merged into `sessions/` |

### 4.2 The Rendezvous

On `homelab` (NixOS) we created `/srv/repo/opencode-hub/` with `skills/`, `tasks/`, `application_architecture/`, `commands/`, `sessions/`, `mem0/`, plus rendezvous-only infrastructure: `sync-backups/<STAMP>/` for conflict snapshots and `sync-log.md` (append-only). Vocab went to `/srv/repo/vocab/`. It was seeded once from the old hub; a stray `opencode-pre-litellm-removal-*.json` left over from an older era was removed from the rendezvous.

### 4.3 Cutover, Distro by Distro

Fedora first, then Debian (whose `rsync` install the user handled personally - version 3.4.1):

1. Delete the `/mnt/c/...` symlinks.
2. Pull real copies of the sync set from the rendezvous (Fedora via rsync, preserving local `sessions/` exports and `scripts/`; Debian preserved two local session exports before pulling).
3. Copy the per-OS overlay (`opencode.fedora.json` / `opencode.debian.json`) in as a **local-only** file.
4. Point `~/.bashrc` at `$HOME/.config/opencode/opencode.<os>.json` via `OPENCODE_CONFIG`.

`skills.paths` was slimmed in the base `opencode.json` to the portable form `[".opencode/skills", "~/.config/opencode/skills"]`; the pre-change file was backed up per the backup-opencode convention (`opencode.json-pre-decentralize-20260919-150100.json`).

### 4.4 The Sync Skill (First Draft)

`sync-opencode/SKILL.md` documented the rendezvous layout, the sync set, the local-only excludes, a static `sync-excludes.txt`, first-time migration, parity checks, and recovery. Plus the safety rules that would save us later (`-n --itemize-changes` first, never `--delete` outside the sync set, quiesce before syncing).

### 4.5 The Live Testing Saga (or: Three Attempts, Three Object Lessons)

The marker-file test protocol: create a file on Debian, sync everything, confirm it reaches the hub AND Fedora AND Windows, then delete it everywhere.

**Attempt 1 - pull-then-push.** Created the marker on Debian, ran the sync: the pull's `--delete` deleted the marker (it was not on the hub yet) before the push could upload it. **Object lesson:** pull-then-push eats brand-new local files.

**Attempt 2 - push-then-pull, `--delete` on both.** The marker made it to the hub, but Fedora (which had never received it) then ran its push with `--delete` and **deleted the marker from the hub**. **Object lesson:** any stale host with `--delete` can gut the rendezvous.

**Attempt 3 - conditional push, then authoritative pull:**

```
rsync -a -u --backup --backup-dir=sync-backups/$STAMP $XF <SRC>/ <HUB>     # push
rsync -a --delete $XF <HUB>/ <SRC>/                                        # pull
```

The first leg (`-u`, no `--delete`) can only send files **newer on the host** - a stale host cannot clobber a newer hub file, and nothing is ever deleted from the hub. The second leg (`--delete`) can only remove files **absent from the hub** - the hub is the only place deletions originate. New local files are safe because leg 1 just uploaded them. **This version survived.** The round trip passed on all four locations.

### 4.6 The Mystery That Wasn't

Mid-session parity showed "7 symlinks" on both distros. Panic. On inspection: they were all `node_modules/.bin/*` npm shims on Fedora - not hub symlinks. A related scare: "node_modules junk" that I flagged as deletable before the user (correctly) pushed back. Verification showed two genuinely **required** dependency trees: `~/.opencode/node_modules/` (opencode runtime + plugin SDK for all hosts) and `~/.config/opencode/node_modules/` (`@opencode-ai/plugin` for the google-workspace plugin on the WSL hosts). Both are `node_modules/`-excluded from sync and documented as such.

### 4.7 Housekeeping

`language-learning` and `session-export` skills were updated for the new paths; the now-obsolete `universal-setup` skill was retired (backed up first). The stray `opencode-pre-*.json` was added to the exclude file alongside the `*.pre-*` pattern.

## 5. Diagnosis (or: What The Empty Output Taught Me)

Two data-loss modes map to two rsync facts:

1. `--delete` is the **receiver's** operation. In a pull it deletes local files missing from the source. Push it to a host that hasn't pulled yet, and that host becomes a deletion cannon.
2. `--delete` honors excludes - but only if the excludes are applied on the right side of the wire and safely expressed (a file, not a shell variable).

The `-u` flag on the push leg adds the missing safety property: a stale host is skipped, not obeyed.

## 6. Solution Summary (or: The Final Algorithm, One Paragraph)

Per host, in this exact order: (1) conditional push `rsync -a -u --backup --backup-dir=sync-backups/$STAMP --exclude-from=<host-local excludes>` to the rendezvous; (2) authoritative pull `rsync -a --delete --exclude-from=...` from the rendezvous; (3) same pair for vocab against `/srv/repo/vocab/`; (4) append a line to `sync-log.md`. Deletions propagate only from the hub: delete on one host, sync, `rm` on the hub, sync the rest. Snapshot dirs keep every overwrite on the rendezvous.

## 7. Verification (or: Show Me the Hashes)

| Location | `opencode.json` sha256 | Symlinks (top-level) | Merged shell |
|---|---|---|---|
| Windows native | `f64af75c...872858ad` | - | `pwsh` |
| FedoraWSL | `f64af75c...872858ad` | 0 | `bash` |
| DebianWSL | `f64af75c...872858ad` | 0 | `bash` |
| homelab rendezvous | `f64af75c...872858ad` | - | - |

Also verified: the finalized `sync-opencode/SKILL.md` sha `abd7b613...` identical on all four locations; a marker file completed a full round trip (Debian -> hub -> Fedora -> Windows); local-only files (overlays, `node_modules`, `scripts`) were never touched by any sync; post-sync verification greps added to the skill.

## 8. Pending Actions and Open Questions

- **Homelab clock skew**: the sync-log shows homelab's `date` about 3 minutes behind the hosts. Harmless, but NTP would be polite.
- **`node_modules/` hygiene**: still present in a few config dirs; confirmed required, so nothing to do - this is now documented, not deleted.
- **`.gitignore` rewrite mystery**: all hosts carry the same bun-scaffold `.gitignore` (63 bytes) that predates this migration; excluded from sync, benign, root cause never chased.
- **In-flight housekeeping**: a `pending-decide-sync-order` debate and the handoff were regenerated; the decentralize task is archived under `.archive/Done--decentralize-universal-setup.md`, 15 tasks remain.

## 9. Recommendations (or: If You Do One Thing)

1. **Use the conditional-push / authoritative-pull order**, never a `--delete` in both directions. Copy the pattern from `sync-opencode` rather than re-deriving it.
2. **Give `--delete` a static exclude file**, never inline `--exclude` from a shell variable. The `sync-excludes.txt` comment header now explains why the excluded `node_modules/` directories are required, not junk.
3. **Dry-run first, always**: `rsync -an --itemize-changes` on both legs; only expected files should change.
4. **Verify after syncing**: sha256 of `opencode.json` across all hosts + rendezvous, and zero (or npm-shim-only) symlinks.

Famous last words from the session that proved the opposite: "it is a simple rsync script." The script is now simple in the way that only a third try can be.

Generated by Big Pickle (OpenCode)