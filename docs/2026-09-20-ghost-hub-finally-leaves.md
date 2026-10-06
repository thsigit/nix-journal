# Cleanup Universal-Setup References (or: The Ghost of the Hub Finally Leaves)

**Date:** 2026-09-20  
**Author:** Codebot  
**Topic:** opencode, decentralization, configuration hygiene, sync-opencode, housekeeping

---

## Trilogy Context

**Part 3 of 3 (Final)** — This session removes the last stale references to the retired universal-setup skill.
- **Part 1**: [Decentralizing the opencode Hub](./2026-09-19-learned-stop-worrying-love-conditional-push.md) — kills shared hub, creates rendezvous + sync-opencode
- **Part 2**: [Plugin Consolidation and Sync](./2026-09-19-why-plugin-two-different-directories.md) — unifies plugin locations, fixes sync-excludes

---

## 1. Objective (or: Sweep the Floor After the Party)

Part 1 killed the shared hub and replaced it with a decentralized rendezvous. Part 2 consolidated plugin locations and fixed the sync-excludes. This session removes the last lingering references to the dead `universal-setup` skill from active configuration files — skills README, backup-opencode, sync-opencode, and the session handoffs.

The hub is gone. The symlinks are gone. The skill is retired. But the docs still talked about it. Time to close that loop.

---

## 2. Background (or: What Parts 1 and 2 Left Behind)

| Part | What It Did | What It Left |
|---|---|---|
| **Part 1** | Decentralized config: each host owns a real copy; rendezvous at `/srv/repo/opencode-hub/`; `sync-opencode` skill with conditional-push + authoritative-pull | `universal-setup` skill retired (backed up), but references remained in `skills/README.md`, `backup-opencode/SKILL.md`, `sync-opencode/SKILL.md`, handoffs |
| **Part 2** | Moved `opencode-google-workspace` to `~/.config/opencode/plugins/` on all distros; removed `plugins/*/skills/` exclude; updated overlays; synced | Plugin location unified, but handoff still listed "Added task: decentralize universal setup" as a pending item (it was done) |

The `universal-setup` skill itself was archived to the backup tray at `/mnt/c/users/sigit/.config/opencode-backups/universal-setup-SKILL-retired-decentralize-20260919-150124.md` — preserved, not deleted.

---

## 3. Problem (or: Dead Code Walking)

Three categories of stale references in active files:

1. **`skills/README.md`** — still listed `universal-setup` in the "Current skills" line alongside 20 active skills
2. **`backup-opencode/SKILL.md`** — pointed readers to "the `universal-setup` skill first" for hub layout context (the hub no longer exists)
3. **`sync-opencode/SKILL.md`** — kept a "Retire `universal-setup`" step in the migration checklist (migration complete)
4. **`tasks/next-session-handoff.md`** (both Windows and Fedora) — still had "Added task: decentralize universal setup" in the 2026-09-18 work log, even though Part 1 completed it

These are cosmetic but confusing. A new reader would think the universal setup still exists or is relevant.

---

## 4. Work Performed (or: Six Edits, Two Hosts, Zero Surprises)

### 4.1 Backup First (Per `backup-opencode` Convention)

Every file backed up to `/mnt/c/users/sigit/.config/opencode-backups/` with `-pre-universal-setup-cleanup-<timestamp>` suffix before editing:

```
README-skills-pre-universal-setup-cleanup-20260920-*.md
SKILL-backup-opencode-pre-universal-setup-cleanup-20260920-*.md
SKILL-sync-opencode-pre-universal-setup-cleanup-20260920-*.md
next-session-handoff-pre-universal-setup-cleanup-20260920-*.md
```

Times two hosts (Windows native + FedoraWSL) = 10 backup files.

### 4.2 Edits Applied

| File | Change |
|---|---|
| `skills/README.md` (both) | Removed `universal-setup,` from skill list (line 29) |
| `skills/backup-opencode/SKILL.md` (both) | Line 17: "`universal-setup` skill first" → "`sync-opencode` skill first" |
| `skills/sync-opencode/SKILL.md` (both) | Deleted line 6: `**Retire \`universal-setup\`**: replace with this skill...` |
| `tasks/next-session-handoff.md` (both) | Removed "Added task: decentralize universal setup" line from 2026-09-18 section; kept "Decentralized the universal setup - complete" in Completed Work |

### 4.3 Left Intact (Historical Records)

| Location | Reason |
|---|---|
| `sync-backups/*` | Immutable snapshots — never edit |
| `tasks/done/Done--decentralize-universal-setup.md` | Audit trail of completed work |
| `tasks/.archive/Done--decentralize-universal-setup.md` | Same |
| `sessions/2026-09-02-refactor-litellm-litellm-cli-XUM6oPfQ.md` | Session record describing the old hub |
| Frontmatter keyword `universal-setup migration` in `sync-opencode/SKILL.md` | Appropriate historical context for the skill |

---

## 5. Verification (or: Show Me the Grep)

After edits, only one reference pattern remains in active (non-backup) skill files:

```bash
grep -r "universal-setup" skills/ --include="*.md" | grep -v sync-backups
# Output:
# skills/sync-opencode/SKILL.md:... universal-setup migration.
```

The frontmatter `description` field keeps `universal-setup migration` as a front-load keyword — correct, since that skill *was* the migration target.

No references in `backup-opencode/SKILL.md`, `README.md`, or handoffs.

---

## 6. The Trilogy Complete

| Part | Title | Core Achievement |
|---|---|---|
| **1** | Decentralizing the opencode Hub | Killed shared hub symlink model; created `sync-opencode` with conditional-push + authoritative-pull; verified parity across 4 locations |
| **2** | Plugin Consolidation and Sync | Unified plugin dir to `~/.config/opencode/plugins/`; fixed `sync-excludes.txt` to sync plugin-bundled skills; updated all overlays |
| **3** | Cleanup Universal-Setup References | Removed stale docs from active config; backed up per convention; handoffs reflect reality |

The config is now internally consistent: no symlinks, no shared hub, no ghost references. Every host owns its config; the rendezvous is passive; the skills describe the current architecture.

---

## 7. Recommendations (or: What Not to Do Next)

1. **Don't resurrect `universal-setup`** — the decentralized model works. The rendezvous + conditional-push pattern is proven.
2. **Don't edit `sync-backups/`** — they are point-in-time recovery points. If you need to restore, copy from there to the active location.
3. **Do run parity checks periodically** — `sha256sum opencode.json` across hosts + rendezvous, `find ~/.config/opencode -type l` for symlinks.
4. **Do update handoffs at session end** — `manage-tasks` handles this; the handoff is the source of truth for "what is done vs pending."

---

## 8. Final State

```
~/.config/opencode/
├── opencode.json                 # universal base (synced)
├── opencode.windows.json         # Windows overlay (local)
├── opencode.fedora.json          # Fedora overlay (local)
├── opencode.debian.json          # Debian overlay (local)
├── CONTEXT.md                    # synced
├── workstyle.md                  # synced
├── skills/                       # 21 skills (synced)
├── plugins/                      # 2 plugins + skills (synced)
├── tasks/                        # 15 pending + archive (synced)
├── application_architecture/     # synced
├── commands/                     # synced
├── sessions/                     # synced
├── mem0/                         # synced (offline buffer)
├── sync-backups/                 # rendezvous-only, never synced
├── sync-log.md                   # rendezvous-only
└── sync-excludes.txt             # in sync-opencode skill dir
```

Three hosts. One rendezvous. Zero symlinks. Zero stale docs.

---

*Part 3 of 3 (Final). The hub is dead. The docs are clean. The rendezvous waits.*

Generated with Big Pickle by OpenCode
