# Splitting the Task Tree Out of the Hub (or: Two Copies of Truth, Neither One Synced)

**Date:** 2026-09-26  
**Author:** Codebot  
**Topic:** opencode-v2, task-manager, git, synchronization, systemd, wsl, overlay-config, silent-failure

---

## 1. Objective (or: Everyone Agreed the Tasks Were Fine, So Why Were They Not Fine?)

Three tasks sat in `active/` with every box ticked and a status line reading
"Complete". The archiver refused them. I had already written off the archiver as
broken, which is the kind of conclusion that feels like progress right up until
it turns out to be the bug.

The session had two halves:

1. Find out why completed work would not archive, and archive it honestly.
2. Fix the reason the task tree had drifted across four hosts in the first
   place, and make it redistribute itself.

Part two was requested mid-session, in the form of: "we need a better mechanism
so every time `tasks/` is updated, it will be redistributed to the rest of the
distros." That sentence is the whole post, really. Everything below is the
story of how badly that was not true.

## 2. Background (or: The Task Tree Had Two Homes and Neither Was Talking)

The `opencode-task-manager` plugin hardcodes its tree:

```ts
// task-manager.ts
const BASE = path.join(HOME, ".opencode", "tasks");
```

So every host has a real task tree at `~/.opencode/tasks`. Separately, the
canonical config hub (`/mnt/c/users/sigit/git/opencode-v2/`, mirrored to
`/srv/repo/opencode-v2-hub/`) also carried a `tasks/` directory, which
`bootstrap-wsl.sh` copied to each new distro with a one-shot `cp -r`.

Two copies. One is what the plugin reads and writes. The other is what gets
shipped. Nothing watches either side. They had already diverged in both
directions, and neither was authoritative.

| | `~/.opencode/tasks` (live) | hub `tasks/` (shipped) |
|---|---|---|
| Read/written by | the plugin, and by me editing markdown | nobody, except `cp -r` |
| Git tracked | no (not a repo at all) | yes |
| Files (2026-09-26) | 67 | 62 |
| `TASK-remaining-v2-recovery` | archived | still in `active/` |
| `session-handoff.md` | newer | older |

The two had even double-archived the same three tasks on different dates,
producing a `_2026-09-25` copy in the hub and a `_2026-09-26` copy in the live
tree, because two different sessions had each decided to archive them in the
tree they could see.

## 3. Problem

Three problems, stacked, which is how these things usually arrive.

**3.1 Completed work would not archive.** The archiver read three tasks as
"not done" when every checkbox in them was ticked.

**3.2 The task tree could not converge.** There was no mechanism, and the
mechanism that existed (a one-shot `cp -r` at bootstrap) had demonstrably
failed to keep four hosts in agreement.

**3.3 A latent config regression, found en route.** Windows' live
`opencode.json` had drifted to hash `7907F43A...` while the hub and both
distros all sat at `55f38C41...`. The diff was an extra `mcp.gws` entry with a
hardcoded Windows path, inlined into the *shared* file. The `sync-opencode`
skill warns in as many words that a `gws` entry in the shared config
"displaces the plugin and breaks distros", so any redistribution mechanism
would have shipped that breakage to both distros with enthusiasm.

## 4. Work Performed

### 4.1 Why the archiver said "not done" (it was reading the wrong file)

The plugin's `todoSection()` and `checkboxMarkers()` only look inside a section
literally headed `## To Do`. Two of the three tasks were written with numbered
sections:

```markdown
## 1. Rotate leaked Google OAuth credentials
- [x] Treat the previously printed client ID as compromised
- [x] Rotate them in Google Cloud Console
```

No `## To Do` heading, so `markers.length === 0`, so `isDone()` returns false.
Forever. No number of ticks would have helped, and neither would any tool call
to the plugin, because the plugin was never going to look at that file.

This is the sort of bug that survives for months because it presents as
"the tool is broken" rather than "the tool is reading a heading you do not
have".

### 4.2 The Windows gws regression

v2 merges config from `OPENCODE_CONFIG` over the global file, later overriding
earlier and only for conflicting keys. So the fix is a minimal overlay holding
only the host-specific entry, with the shared file restored to hub parity:

```json
// C:\Users\SIGIT\.config\opencode\opencode.windows.json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "gws": {
      "type": "local",
      "command": ["node",
        "C:/Users/SIGIT/.config/opencode/node_modules/@dguido/google-workspace-mcp/dist/index.js"],
      "environment": {
        "GOOGLE_CLIENT_ID": "{env:GOOGLE_CLIENT_ID}",
        "GOOGLE_CLIENT_SECRET": "{env:GOOGLE_CLIENT_SECRET}",
        "GOOGLE_WORKSPACE_SERVICES": "{env:GOOGLE_WORKSPACE_SERVICES}"
      },
      "enabled": true
    }
  }
}
```

The merge was verified rather than assumed, because "merges" and "replaces the
whole `mcp` object" are both plausible readings of the docs and only one of
them keeps `mem0` alive:

```
$ opencode mcp list
gws   connected
mem0  connected
```

Both up, shared file hash back to `55F38C41...`, matching the hub. The old
config was kept as `opencode.json.pre-gws-overlay-20260926-141000`.

Worth noting: the `sync-opencode` skill contained, in its own words, that there
is "no `opencode.windows.json` in v2" and the filename "no longer does
anything". That claim contradicted lines 65-66 and 106 of the same file, and it
is almost certainly what led to the gws entry being inlined into the shared
file in the first place. A confidently wrong skill is worse than no skill,
because it is load-bearing.

### 4.3 Splitting the task tree into its own repository

Tasks are mutable shared state. `opencode-v2` is a config bundle that must stay
byte-identical everywhere. Trying to serve both roles from one repo with a
mirror is what produced the mess, so they were separated:

```
remote: sigit@192.168.1.3:/srv/repo/opencode-tasks.git

Windows     C:\Users\SIGIT\.opencode\tasks     (v2)
DebianWSL   ~/.opencode/tasks                 (v2)
FedoraWSL   ~/.opencode/tasks                 (v2)
homelab     ~/.opencode2/tasks                (still v1 - see 4.6)
```

`tasks/` was gitignored in the config hub (with the rationale written into the
ignore file, so it survives a `cat .gitignore` six months from now), and the
full pre-split task history stays in the config repo's history at `ceeaf10` and
earlier. The live tree was seeded as `b18a467` and the repo reached `65f7111`
by the end of the session.

Each host's tree is now a clone, so the plugin's hardcoded path is satisfied by
a real git working copy and redistribution reduces to `git pull`.

### 4.4 The sync script

`scripts/sync-tasks.sh` (Linux) and `scripts/sync-tasks.ps1` (Windows). The
load-bearing step is not the pull, it is the auto-commit:

1. refuse to run mid-merge or mid-rebase
2. provision a per-repo git identity if missing (never `--global`)
3. auto-commit any local edit
4. fetch, fast-forward, rebase if diverged
5. push

Step 3 is why this is safe to leave on a timer. Without it, every task edit
would need a human to remember a commit and a push, which is the exact failure
mode being fixed. The rule that makes it safe: a plain file edit needs no
ceremony, and a plain `git pull` is never enough.

Two deliberate constraints:

- **PowerShell is a separate script, not a bash callout.** Git bash has no
  `flock`, so the Windows timer would have run with no lock and a manual run
  could collide with a timer tick. The PowerShell version takes an exclusive
  file handle instead. Verified: an overlapping run exits 2.
- **It never force-pushes and never resolves conflicts for you.** A rebase
  conflict aborts and stops, because a script that guesses at a merge is worse
  than a script that stops.

### 4.5 The timers, and a bug that hid in plain sight

`scripts/install-sync-timer.sh` installs a systemd `--user` timer on Linux and
a Task Scheduler job on Windows, both every 5 minutes.

The first version used `OnUnitActiveSec=5min`. It ran three times and then
stopped, silently:

```
$ systemctl --user list-timers opencode-sync-tasks.timer
NEXT LEFT LAST ... UNIT
-     -   Sat 2026-09-26 14:30:34 WITA 1ms ago opencode-sync-tasks.timer ...

$ systemctl --user is-active opencode-sync-tasks.timer
active
```

`NextElapseUSecMonotonic=infinity`. The unit was `active` and doing nothing
forever, because after a `Type=oneshot` service completes and returns to
`inactive`, systemd stopped re-arming the `OnUnitActiveSec` trigger. There is
no error, no failed unit, nothing in `journalctl`. A monitoring check that only
asks "is the timer active?" would have reported healthy indefinitely.

The same trigger type is also wrong for WSL on its own terms: monotonic time
does not advance while a suspended VM runs, so an idle distro never reaches its
next elapse, and nothing catches up on resume. Measured on Fedora - last tick
14:25:13, no further runs across several wake cycles, and a 45-second wait
after explicitly waking the distro produced nothing.

`OnCalendar=*:0/5` compares against real time, and `Persistent=true` fires
immediately for occurrences a suspended host slept through. After reinstall:

```
NEXT                             LEFT   LAST
Sat 2026-09-26 14:40:00 WITA 4min   Sat 2026-09-26 14:35:16 WITA 35s ago
```

Fired on the boundary, re-armed for the next slot.

### 4.6 The homelab is still on v1

The homelab has not been upgraded to OpenCode v2, so its clone sits at
`~/.opencode2/tasks` rather than colliding with the v1 layout. That decision is
recorded in four places on purpose - both `.gitignore` files, `machines.md`,
and `bootstrap-wsl.sh` via `OPENCODE_TASKS_V1_LAYOUT` - because the failure
mode is a host quietly syncing a path nothing reads.

When the homelab moves to v2: move the clone, re-run `install-sync-timer.sh`,
drop the layout flag, delete the notes.

### 4.7 Documentation that was actively wrong

Correcting the docs turned out to be more valuable than adding new ones.

- `wsl-reset` told you to hand-restore `tasks/` from the hub and verify the tree
  "matches backup". After the split that is exactly backwards: the hub has no
  `tasks/`, the task repo *is* the backup, and a hand-restore would drop a stale
  copy over a good clone. It now tells you not to back tasks up at all.
- `machines.md` claimed FedoraWSL "uses the default managed service port". It
  uses 49374. Windows is 49576, Debian 49475. All three differ, because the WSL
  distros share the Windows loopback relay.
- The "Windows currently has two skills the hub lacks" note was stale; the
  skills are tracked now, and an untracked skill directory is precisely what the
  next destructive sync deletes on every distro.
- `bootstrap-wsl.sh` carried its own inline copy of the systemd unit heredocs
  alongside `install-sync-timer.sh`. That duplication is how the `OnCalendar`
  fix landed in one file and had to be hand-copied into the other. Step 11 now
  delegates, so there is one definition and it is the one proven on live hosts.

## 5. Diagnosis

The drift was not a sync bug. It was an architecture bug with three causes:

1. **Two unsynchronised copies of mutable state.** One for the tool, one for
   distribution, with no reconciliation. Drift was inevitable and silent.
2. **No trigger keyed to the filesystem.** The obvious hook - "push when the
   plugin mutates a task" - cannot work, because the plugin is not the only
   writer. Checkboxes get flipped by an agent editing markdown with a text
   editor. A tool-call hook would have missed most updates, which is the worst
   possible failure: it would look like it worked.
3. **No observable state.** A log written into the tree (`.sync-state`) was
   itself being committed, so a quiet host and a busy host were
   indistinguishable, and every timer tick on every host would have produced a
   commit.

## 6. Preliminary Assessment

The mechanism works, and it works unattended, which is the part that was in
doubt. The proof that matters is not that the script runs, it is that nothing
had to be run by hand:

| Event | Who did it |
|---|---|
| Edit a task file on Windows | me |
| Auto-commit and push | the Task Scheduler job, alone |
| Pull it on Fedora | Fedora's systemd timer, alone, 4 min later |
| Deletion of a scratch file | propagated the same way, unattended |

A scratch file was used for the propagation proof rather than flipping a real
checkbox, because a test that lies about task state is not a test.

## 7. Verification Status

| Host | Commit | Tree | Sync trigger | Result |
|---|---|---|---|---|
| Windows | `65f7111` | clean | Task Scheduler, 5 min | `0x0` |
| DebianWSL | `65f7111` | clean | systemd `--user` | active |
| FedoraWSL | `65f7111` | clean | systemd `--user` | active |
| homelab | `65f7111` | clean | systemd `--user` | active |
| origin | `65f7111` | - | - | - |

Also verified: `opencode mcp list` shows gws and mem0 both connected on Windows;
shared `opencode.json` hashes identical across hub and all three hosts; task
index reads 20 active, `verify` reports no orphans, collisions, or
ready-to-archive tasks.

## 8. Things I Got Wrong (or: The Post About the Fix, Including the Parts Where the Fixer Was Wrong)

A report that only lists successes is marketing, so:

- I first reported the hub's `tasks/` as "stale". It was actually *ahead* on one
  file, uncommitted. The real problem was two trees, not one lazy tree, and I
  had the direction of the drift backwards.
- I described the `@opencode/plugin@2.0.16` pin as version drift needing a
  change. Checking instead of assuming showed all three hosts have 2.0.16
  installed and working, matching the pin exactly. Only the *binaries* differ
  (2.0.17 on Windows, 2.0.18 on both distros), which is harmless. The pin was
  correct and I left it alone.
- I verified the timer design with a shell diff that reported `IDENTICAL` after
  both extractions returned empty. A false pass. It took three attempts, one
  invalid failure test, and a PowerShell quoting problem to get a real answer -
  and the right answer was to delete the duplicated code rather than keep
  testing it.
- I suggested a "throwaway wsl-reset on Debian" to test the bootstrap path. That
  was a genuinely bad idea: destroying a working distro to exercise a shell
  script, when the script's logic was already proven on three live hosts. The
  gap was one duplicated heredoc, and the fix was to remove the duplicate.

## 9. Pending Actions

1. **The bootstrap path has never run end to end.** Its task-tree logic is the
   same code proven on three live hosts, and the duplication that made it
   drift-prone is gone, but nobody has reset a distro through it. A future reset
   is the real test, and the `wsl-reset` verification step now checks the clone,
   the script, and that the timer is enabled *and* active.
2. **The homelab v1 to v2 move** is documented in four places and automated in
   none. Four manual steps when it happens.
3. **Part A of `TASK-v2-fleet-parity-and-whitelist-followups`** is untouched:
   the per-distro parity checks and the deferred decision on an explicit
   free-model whitelist. This is the only outstanding item of real work, and it
   is unrelated to the sync mechanism.
4. **A suspended WSL host does not tick.** Convergence happens when a host next
   starts rather than on a fixed wall clock. This is benign - a session editing
   tasks keeps its own distro alive - but the docs say so rather than claiming
   literal 5-minute fleet redistribution.

## 10. Recommendations

1. **Split state by mutability, not by convenience.** Config is a bundle that
   wants to be byte-identical everywhere; tasks are mutable shared state that
   wants history and conflict detection. One repo serving both, with a mirror,
   is how you get two silent copies.
2. **If a tool's data has one true path, make the distribution mechanism a clone
   of it.** Then redistribution is `git pull`, history comes free, and the
   plugin's hardcoded path is satisfied rather than fought.
3. **Auto-commit is what makes a sync timer safe.** Without it, the timer is a
   suggestion. With it, a file edit needs no ceremony and the timer is a
   guarantee.
4. **Never use a monotonic timer in WSL, and never trust `is-active` as proof a
   timer works.** Monotonic time stops while the VM is suspended, and
   `OnUnitActiveSec` stops re-arming after a oneshot completes. Use
   `OnCalendar`, and verify by watching an actual firing that re-arms.
5. **A silently-dead sync is worse than no sync**, because it produces
   confidence. Put the log somewhere untracked (`.git/`), keep the commit
   message self-describing (`tasks: auto-sync from <host>`), and check
   convergence by commit hash across hosts, not by asking whether a process is
   running.
6. **A confidently wrong skill is an incident waiting to happen.** The "v2 has
   no overlay" claim had already caused a real config regression by inlining a
   host-specific entry into a shared file. When documentation contradicts
   itself, the contradiction is the bug report.
7. **Provenance beats tidiness for backups.** The double-archived tasks
   (`_2026-09-25` and `_2026-09-26`) looked like a mistake to clean up, but the
   09-25 copies were still recoverable from `a4fdf55` when the 09-26 copies were
   written, which is what made deleting them safe. Check the history before
   pruning.

## 11. Relevant Files

| Path | What |
|---|---|
| `sigit@192.168.1.3:/srv/repo/opencode-tasks.git` | the task repo |
| `~/.opencode/bin/sync-tasks.sh` | Linux sync (distros, homelab) |
| `~/.opencode/bin/sync-tasks.ps1` | Windows sync |
| `~/.opencode/tasks/.git/sync-state.log` | per-host log, rotated at 200 lines |
| `scripts/install-sync-timer.sh` | single definition of the systemd units |
| `scripts/bootstrap-wsl.sh` | clones the task repo, delegates to the installer |
| `.config/opencode/opencode.windows.json` | Windows gws overlay |
| config hub `dbd5f84` | latest commit; `tasks/` gitignored with the rationale |

## 12. If It Recurs

- Tasks missing on one host, present on another -> compare `git log --oneline -1`
  in each tree, and each host's `.git/sync-state.log`. A host whose log is
  silent is a host whose timer is not firing.
- Timer `active` but nothing syncing -> check `NextElapseUSecRealtime`. If it is
  empty or `infinity`, you are back on a monotonic trigger.
- Two hosts editing the same task -> expect a rebase conflict and a stopped
  script. That is the designed behaviour. Resolve it by hand; do not make the
  script smarter.
- A task that will not archive -> check for a literal `## To Do` heading before
  suspecting the tool.

That's the mechanism working. Part 2, whenever there is one, will presumably
involve me noticing that the timer has been quietly dead for a week and calling
it a feature.

Generated with Big Pickle by opencode
