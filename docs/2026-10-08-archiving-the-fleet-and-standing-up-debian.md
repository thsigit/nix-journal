---
nav:
  series: "Fleet to Solo"
  part: 2
  prev:
    title: "From Three Hosts to Solo Fedora (or: We Built a Fleet by Accident, Then Wound Down)"
    slug: 2026-10-08-fleet-to-solo
  next:
    title: "Restoring Fedora's Own Key (or: The Key That Was Never Lost)"
    slug: 2026-10-08-restoring-fedoras-own-key
---

# Archiving the Fleet and Standing Up Debian (or: We Actually Deleted Things This Time)

**Date:** 2026-10-08  
**Author:** Codebot  
**Topic:** opencode, retirement, archiving, debian, ssh, wsl, hub, umbrella-mirror

---

## 1. Objective (or: Working the List)

Part 1 decided the fleet was over. This is the part where we actually take it apart:

1. Retire the three sync/fleet tasks so the ledger stops advertising work nobody wants.
2. Archive `sync-opencode`, `fleet-sync`, and `mesh-bootstrap.sh` - move them off the hub, delete nothing.
3. Grep every `.md` in the config until "fleet" only appears in the retirement notice itself.
4. Give Debian an sshd so it can be an MCP server host instead of an Opencode host.
5. Keep the hub canonical, published, and mirrored.

The interesting part is not any one of those. It is that step 5 bit back and we ended up repairing a backup we had broken ourselves. That gets its own section, because that is the sort of thing a journal is for.

## 2. Background (or: What Part 1 Left on the Table)

Part 1 closed with three unchecked boxes in its Verification Plan and a Pending Actions section pointing at `TASK-finish-and-archive-sync-distro-tasks.md`:

| Part 1 pending item | Status after this session |
|---|---|
| Debian SSH mesh rebuilt - needs `openssh-client`, keygen, sshd, `authorized_keys` | Done, but by hand rather than via `mesh-bootstrap.sh` |
| `mesh-bootstrap.sh` full build | Superseded - the script was retired instead of run |
| Phase 3 retire `sync-opencode`/`fleet-sync` skills, archive stale tasks | Done |

That middle row is worth pausing on. Part 1 left `mesh-bootstrap.sh` as a *pending dependency* ("`--check` passes 9/9; full build requires Debian with `openssh-client`"). The honest next step would have been to run it. The actual next step was to decide the whole mesh was the thing being retired, and archive the script instead. A blocking prerequisite is a fine moment to ask whether the blocker is worth removing.

## 3. Work Performed (or: Eight Small Jobs and One Backhoe)

### 3.1 Making three tasks archivable without lying about them

`close_task` will only archive a task whose `## To Do` section is fully ticked. Three retiring tasks had real, unticked checklists - work that was correct to abandon, but unticked nonetheless. Unchecking them by hand would have been dishonest; leaving them checked off work that never happened would have been worse.

The fix was to separate the *record* from the *state*:

```markdown
## To Do
- [x] Retired 2026-10-08 (fleet-to-solo); see journal 2026-10-08-fleet-to-solo.md

## Retired backlog (obsolete - retained for the record)
- [ ] original item one
- [ ] original item two
```

Only `## To Do` is read by the archiver, so the original checklist survives verbatim under a heading nobody interprets as a promise:

- `TASK-test-sync-opencode.md_2026-10-08.md`
- `TASK-repair-unavailable-skills-sync-opencode-wsl-reset.md_2026-10-08.md`
- `TASK-fleet-sync-implement-push-up-phase-and-wire-config-sync.md_2026-10-08.md`

Active tasks went from 15 to 12, and the three bodies of work are still readable.

### 3.2 Archiving the artifacts (moving, not deleting)

New off-site directory: `homelab:/srv/repo/opencode-v2/archived/`, with `/srv/repo/opencode-v2/.gitignore` containing `archived/` so it never becomes tracked history.

| Path | What it was |
|---|---|
| `skills/sync-opencode/` | The cross-host sync skill, rewritten 2026-09-30 -> 2026-10-06, content-tested but never load-proven |
| `skills/sync-opencode/backups/` | 7 timestamped `self-improve` snapshots, md5-verified before removal from Fedora |
| `plugins/fleet-sync/` | The orchestrator: `verifyConfig`, `syncStores`, `buildPlugins`, report writer - plus its `dist/` |
| `scripts/mesh-bootstrap.sh` | SSH-mesh bootstrap for the three WSL hosts; `--check` passed 9/9 while the mesh was live |

Every move was md5-checked before the Fedora and hub copies were removed. `archived/README.md` records one detail worth keeping: `syncConfigTo()` was imported but never called - config copy was *dead code by design*, because a `session.end` config write had caused the 2026-09-26 outage. The plugin that was named after config syncing had been forbidden to sync config.

### 3.3 Stripping the vocabulary

Every `.md` in the hub was grepped for `fleet`, `mesh`, `sync-opencode`, `all three hosts`, and `three-peer`. Files edited:

- `README.md`, `CONTEXT.md`, `machines.md`, `skills/README.md`
- `skills/session-close/` and `skills/task-triage/` (both the `skills/` copies **and** the `opencode-task-plugin/skills/` mirrors, which differ and need parallel edits)
- `skills/task-claim-audit/`, `skills/wsl-reset/`, `skills/gmail/`

`skills/README.md` needed the most surgery: "Per-host divergence" became "Host-local config", the Live-skills list was corrected (it had been missing `mcp-sqlite-server`, `nixos-profile-refactor`, and `task-claim-audit`), the plugin invariant went from "Exactly 5 plugins" to "Exactly 4", and a new `## Retired 2026-10-08` section points at the archive.

There is no `AGENTS.md` in this repo. People keep asking.

Final state:

```text
$ grep -rniI 'fleet' <hub> --include='*.md' | grep -v '/skills/archive/'
(none)
```

One deliberate survivor: a dated 2026-09-30 `self-improve/backups/task-claim-audit.*.SKILL.md` snapshot still says "takes an entire fleet offline". It is immutable version history of a skill that is still live (and whose live copy was fixed), so it stays.

### 3.4 The check that would have failed a fresh bootstrap

`scripts/bootstrap-wsl.sh` was still doing this:

```bash
check "5 plugins present" bash -c 'for p in model-whitelist opencode-google-workspace \
  opencode-task-plugin self-improving-skills fleet-sync; do ...'
```

`plugins/fleet-sync/` no longer exists, so a clean install would have failed its own verification. Now it checks four. Five other scripts (`sync-plan.sh`, `sync-plan.ps1`, `sync-mem0.sh`, `sync-mem0.ps1`, `install-sync-timer.sh`) carried fleet wording and pointers to a skill that no longer loads; those pointers were redirected to `skills/README.md`.

### 3.5 Debian gets an sshd (finally)

Debian 13 trixie, freshly reset, had no `openssh-*` at all and no `~/.config/opencode` - correct for an MCP-server host. Installed `openssh-client` and `openssh-server` (both `1:10.0p1-7+deb13u4`), which generated host keys as a side effect.

The drop-in at `/etc/ssh/sshd_config.d/60-mcp.conf`:

```text
Port 2222
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
```

Port choice is not arbitrary. WSL2 in mirrored networking mode shares one loopback across Windows and both distros, so all three hosts are `127.0.0.1` and the ports only exist to disambiguate:

| Host | Port | Note |
|---|---|---|
| Windows desktop | 22 | pre-existing OpenSSH server |
| Debian (MCP server) | 2222 | this session |
| Fedora | 2223 | this machine, already listening |

Details that bit us at least once:

- `/run/sshd` had to be recreated by hand (`Missing privilege separation directory`). WSL restarts wipe `/run`, and `sshd -t` fails loudly without it.
- Fedora's `known_hosts` held three stale `[127.0.0.1]:2222` keys from the *pre-reset* Debian, so the first connection died on `REMOTE HOST IDENTIFICATION HAS CHANGED`. Cleared with `ssh-keygen -R "[127.0.0.1]:2222"`.
- The stale pre-reset Debian pubkey was still in Fedora's `authorized_keys` alongside the new one; the dead key was removed and the `windows-fleet` comment renamed.

Fedora's `~/.ssh/config` also got rewritten by hand - the `# Fleet SSH mesh. GENERATED by mesh-bootstrap.sh - edit that script, not this.` header is gone, replaced with a plain topology note. Nothing generates that file now, which is the point.

### 3.6 Proving the mesh in every direction

The mesh is not hub-and-spoke around Fedora - every pair that shares loopback is tested passwordless in both directions:

```text
fedora<->debian :  OK  (2222)
fedora<->windows:  OK  (22)
debian<->windows:  OK  (2222 -> 22)
fedora->homelab:   OK  (192.168.1.3)
```

Debian's ed25519 key (`sigit@debianWSL`) went into Fedora's `authorized_keys` and Windows' `administrators_authorized_keys`, so the MCP-server host can call into all peers as well as be called. Windows keys needed separating too: Windows authenticates out as `sigit@vantage` (`~/.ssh/id_ed25519`) to the homelab and as `sigit@windows` (`~/.ssh/id_ed25519_windows`) to the WSL trio, because homelab only trust-lists `sigit@vantage`.

Host-key bookkeeping was the bulk of it. Windows' `known_hosts` still held the pre-reset Debian entries on `[127.0.0.1]:2222` (rebuilt from a keyscan) and Windows' `administrators_authorized_keys` still had the **stale pre-reset Debian key** that Fedora had already purged - swapped for the current one, and the fleet-era self-trust `windows-fleet` key pulled. Debian's `known_hosts` gained Windows' entry the same way. Fedora's `~/.ssh/config` was already hand-maintained on the way in; Windows' config got the same treatment (mesh-generated header dropped, retired-mesh wording gone).

### 3.7 Publishing

```text
676c0b3 retire the three-host fleet: archive sync skill/plugin, strip fleet references
        34 files changed, 150 insertions(+), 2960 deletions(-)   [16 D, 18 M]
4f15daf mirror-umbrella.sh: auto-detect Windows-disk path so it runs from Fedora
1245ecf mirror-umbrella.sh: push with -C $src, not from the caller's cwd
```

`sync-plan.sh` ran clean (exit 0), publishing the three archived tasks. Hub edits were rsync'd back to `~/.config/opencode/` and byte-verified for every edited doc and script.

## 4. Diagnosis (or: The Day wsl.exe Died)

Halfway through, `wsl.exe` stopped working from Fedora:

```text
/bin/bash: line 1: /mnt/c/WINDOWS/system32/wsl.exe: cannot execute binary file: Exec format error
```

Not a permissions problem, not a path problem. The diagnostic that mattered:

```text
$ ls /proc/sys/fs/binfmt_misc/
register
status
$ cat /proc/sys/fs/binfmt_misc/WSLInterop
cat: ...: No such file or directory
```

`WSLInterop` is the kernel binfmt handler that makes Windows `.exe` files executable from inside a Linux distro. Every one of them goes through it - `wsl.exe`, `powershell.exe`, `cmd.exe`. With the entry gone, no Windows binary runs at all, and therefore no way to start or reach Debian from Fedora.

It reappeared after a WSL shutdown and vanished again the moment Debian booted, which is a clean one-variable experiment: Debian's startup removes a kernel-wide registration that Fedora depends on. (The `WSLInterop` string does not appear anywhere in `/init` or in `/usr/lib`, `/etc`, `/usr/share` - it is built at runtime, so there is no config file to copy.)

Resolution was operational, not clever. The setup script was staged on the Windows disk and fed to Debian from **PowerShell**, which is unaffected:

```powershell
Get-Content "$env:LOCALAPPDATA\Temp\opencode\debian-ssh-setup.sh" -Raw | wsl -d Debian -u root -- bash
```

The first attempt used the obvious redirection and got:

```text
ParserError: The '<' operator is reserved for future use
```

PowerShell reserves `<`. A pipe to `wsl ... bash` does the same job. Once sshd was up this stopped being urgent: Debian answers over SSH now, and it stays enabled across restarts. Still open: Fedora's `wsl.exe` remains broken until the next WSL restart, and Debian only answers while its distro is running - if it ever stops, one `wsl -d Debian` from PowerShell brings it back.

## 5. Verification Status (or: Prove It)

- [x] 3 fleet tasks archived; 12 active tasks remain
- [x] `sync-opencode`, `fleet-sync`, `mesh-bootstrap.sh` absent from hub **and** Fedora; present under `homelab:/srv/repo/opencode-v2/archived/`
- [x] `opencode.json` `plugin` array is 4 entries on both hub and host
- [x] `grep -rniI 'fleet' <hub> --include='*.md'` returns nothing outside `skills/archive/`
- [x] Fedora and hub copies byte-identical for every edited doc and script
- [x] passwordless mesh in both directions for every pair: fedora<->debian, fedora<->windows, debian<->windows, fedora->homelab
- [x] Debian `~/.config/opencode` does not exist; `ssh` unit `enabled` + `active`, listening on `2222`
- [x] Umbrella mirror HEADs match their sources
- [ ] `close_task` on `TASK-finish-and-archive-sync-distro-tasks.md` (all boxes ticked, not yet archived)
- [ ] `sync-plan.sh` re-run after the final tick

## 6. Solution Summary (or: The Shape of It Now)

| Component | Part 1 (Fleet) | Part 2 (Solo) |
|---|---|---|
| Active Opencode host | Fedora + Debian + Windows | Fedora only |
| Debian | Opencode CLI | sshd on 2222, key-only, no Opencode config |
| Sync skill/plugin | `sync-opencode`, `fleet-sync` | archived off-site |
| Plugins | 5 | 4 |
| Fleet refs in docs | everywhere | 1 historical backup snapshot |
| SSH mesh | `mesh-bootstrap.sh` generated | hand-written `~/.ssh/config` |
| Umbrella mirror | Git Bash only, one repo checked | runs from Fedora, all three correct |

## 7. Diagnosis Summary (or: What We Actually Learned)

1. **A blocking prerequisite can be a decision point.** `mesh-bootstrap.sh` needed sshd on Debian; the real answer was that the mesh should not exist.
2. **Archiving is not deleting, and neither is it lying.** Moving artifacts off-site plus preserving superseded checklists under a non-load-bearing heading keeps the record honest without keeping the work alive.
3. **`git -C` on the status command is not `git -C` on the push.** See below - this one cost a backup.
4. **Shared loopback means ports are identity.** Three hosts on `127.0.0.1` only work because 22 / 2222 / 2223 never collide.
5. **binfmt is kernel-global and distro-hostile.** One distro's boot can unregister another distro's ability to run Windows binaries.

## 8. The Backup We Broke (or: A Very Embarrassing Confession)

The umbrella mirror at `homelab:/srv/repo/opencode-v2/{config,tasks,mem0}.git` is the only copy of these repos that is not on the Windows disk. While writing this session's state down, it was checked - and all three reported the same HEAD:

```text
config 676c0b3 retire the three-host fleet: archive sync skill/plugin, strip fleet references
tasks  676c0b3 retire the three-host fleet: archive sync skill/plugin, strip fleet references
mem0   676c0b3 retire the three-host fleet: archive sync skill/plugin, strip fleet references
```

`mem0.git` holding the config repo's commit is not a subtle inconsistency. The push log said exactly how it happened:

```text
/tmp/mirror-tasks.log
 + 7dcc0b6...676c0b3 main -> main (forced update)
/tmp/mirror-mem0.log
 + 88a50ec...676c0b3 main -> main (forced update)
```

Root cause, in `mirror-umbrella.sh`:

```bash
head=$(git -C "$src" rev-parse --short HEAD 2>/dev/null)   # correct: scoped to $src
if git push --mirror "$DEST/$name.git" ...                 # BUG: no -C, so cwd wins
```

The **status** line looked at the right repository; the **push** did not. Run from inside the config hub, git pushed the config repo into all three destinations, and `--mirror` force-updates, so nothing complained. Every previous run had happened to be launched from a context where it did not matter, which is how a script that reports `OK` for three repos can be wrong about two of them.

The earlier `4f15daf` fix (making the script find `/mnt/c` instead of `/c`) was what surfaced this: the script only ever worked in one directory, and nobody had tested it in another.

Repair was simple because the sources were never touched:

```text
config 1245ecf mirror-umbrella.sh: push with -C $src ...   (source tip)
tasks  7dcc0b6 plan: auto-sync from fedoraWSL (2026-10-08 11:43)
mem0   88a50ec mem0: auto-sync from VANTAGE-V14G4 (2026-09-28 17:02)
```

plus `refs/umbrella/main` in `tasks.git`, which had been clobbered down to a config commit, restored to `cc7e3a3` (a tasks commit) by the same re-push. Committed as `1245ecf` with the bug written into the comment, because the failure mode - *green output, wrong destination* - is not discoverable from the script's own output.

Lesson worth the detour: a mirror that reports success without ever comparing its own destination against the intended source is not a backup, it is a habit.

## 9. Pending Actions

1. **Archive the anchor task.** `TASK-finish-and-archive-sync-distro-tasks.md` is fully ticked but still sitting in `active/`; run `close_task`, then `sync-plan.sh` to publish.
2. **Fresh-session smoke test** - confirm `sync-opencode` is absent from the skill list and no `fleet-sync` `dist/` loads.
3. **Debian persistence.** If the distro stops, it needs one `wsl -d Debian` from PowerShell to come back; sshd is enabled but cannot start without the distro running.
4. **WSLInterop.** Fedora's `wsl.exe` stays broken until the next WSL restart. Worth a proper fix (a Debian-side binfmt drop-in) if it recurs.

## 10. Recommendations

1. **Test any path-portable script from a second directory before trusting it.** `4f15daf` and `1245ecf` were the same script found twice - first the paths, then the cwd. A script that only ever ran from its own repo has never been tested, only executed.
2. **Never trust a mirror's own "OK".** Compare `git --git-dir=<dest> log -1` against the source's tip as a separate step, after the push. The push log tells you what git did; only the destination tells you what you have.
3. **Archive by moving, and record where.** `archived/README.md` plus a gitignored directory means the retirement is reversible by someone who was not in the room.
4. **Preserve superseded checklists under a heading nobody parses.** The archiver reads `## To Do` and only `## To Do`; that is a gift, use it.
5. **Give Debian sshd and stop reaching for `wsl.exe`.** Cross-distro control via SSH survives restarts, does not depend on binfmt, and works when PowerShell is not an option.
6. **Keep the hub canonical and the umbrella mirrored.** Both repos and all three mirrors are current as of `1245ecf`.

---

Generated with Big Pickle by OpenCode
