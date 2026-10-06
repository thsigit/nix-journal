# Three Wrong Instruments: Verifying Changes With Tools That Cannot See Them

**Date:** 2026-09-30  
**Author:** Codebot  
**Topic:** opencode, v2, config, overlays, fleet-sync, verification, false-positives, git

---

## 1. Objective

Document a single day in which three separate investigations all failed the same way: a
measurement tool was asked a question it could not answer, returned a confident answer
anyway, and was believed. Twice the wrong answer nearly caused a fleet-wide outage. Once
it was published to this journal as fact, and had to be retracted twenty minutes later.

The three instruments:

| # | Instrument | Question asked | What it actually measured |
|---|---|---|---|
| 1 | `opencode debug config` | "what is the effective config?" | the config a long-lived **service** loaded at boot |
| 2 | `opencode debug config` (output shape) | "what must the file look like?" | how the tool **renders** a normalised form |
| 3 | `fleet_sync` self-check | "is the fleet converged?" | only **this host's** tree |

Along the way: a per-host identity mechanism that never worked, a plugin that
self-reported healthy while the fleet was seven commits apart, and a `bash` invocation
that never ran the command it appeared to run.

## 2. Background

The fleet is three OpenCode v2 hosts: Windows native, and two WSL2 distros (FedoraWSL,
DebianWSL). Config is authored in a git-tracked hub on the Windows disk
(`/mnt/c/users/sigit/git/opencode-v2`) and copied out to the distros. Two data stores -
the plan tree and the mem0 store - are three-way git peers against bare repos on the same
disk. A `fleet-sync` plugin had existed for months, doing exactly one thing: publish mem0
on `session.end`.

Two things set up the day. First, a task file specified a plan to unify all of that into
one plugin. Second, the previous day's entry (`2026-09-29-false-verifications-and-the-v1-question.md`)
had concluded "do not downgrade to v1" partly on the basis that four discrepancies were
"our own layout, not v2". This session found that one of those four had never been
actually tested.

## 3. Problem

The task spec contained instructions. Following them literally would have broken the
fleet. Four separate problems, in ascending order of how much damage they would have done.

## 4. Work Performed

### 4.1 The wrong source of truth (caught before execution)

The spec said:

```
SOURCE: /mnt/c/Users/SIGIT/.config/opencode (hub, canonical)
```

That path is the **live Windows install**. It is not a git repository, and it holds
`service.json`, `auth.json` and `mem0.key`. The actual hub is a different directory:

| | `git/opencode-v2` | `.config/opencode` |
|---|---|---|
| git repo | yes, HEAD `0ac1e4c` | **fatal: not a git repository** |
| holds secrets | no (correctly gitignored) | **yes** |

An `rsync --delete` from the spec's path would have stripped the `mcp` block fleet-wide -
the same class of outage as 2026-09-26. A source of truth is where things are *authored*;
a deployment target is where they land. That distinction was not written down anywhere,
which is why a spec author picked the wrong one.

### 4.2 Instrument #1: the service remembers, the disk does not

While testing a config change, `opencode debug config` reported an `mcp` block that had
been deleted from disk. Decisive test:

```
disk: mcp REMOVED
  A: via the RUNNING SERVICE (default)    -> mcp present? True
  B: via a FRESH PROCESS (isolated port) -> mcp present? False
```

The service (pid 470) had started at 08:29 and was reading config from 2.5 hours earlier.
A junk `__probe__` key written to disk confirmed it independently: `debug config` never
saw it.

The correct invocation is:

```
OPENCODE_SERVICE_PORT=1 opencode debug config
```

`--standalone` is listed in `opencode debug --help`, is **not accepted** by `debug config`,
prints help, and **exits 0**. Exit 0 with no output reads as success, which is how a
broken verification gets trusted.

**Consequence:** on a host whose service stays up for days, "debug config says the config
is fine" proves only what was true at boot. This is the same failure class as the older
traps in this fleet - `mcp list` reporting `connected` while every call fails, `tools/list`
returning 88 tools, `tokens.json` mtime bumping without a refresh succeeding.

### 4.3 Instrument #2: the display shape is not the requirement

`debug config` renders a normalised form, in which MCP servers appear nested under
`mcp.servers`. The files on disk use the flat `mcp: { gws, mem0 }`. From that difference
I concluded, and wrote down, that v2 requires nesting and our files were "silently
ineffective."

Both shapes were then tested:

| Shape in the shared file | Effective servers read |
|---|---|
| flat `mcp: { gws, mem0 }` | `['gws', 'mem0']` |
| nested `mcp: { servers: { gws, mem0 } }` | `['gws', 'mem0']` |

v2 accepts both. There is no schema drift. The claim came from reading a tool's output and
inferring a requirement of the input - instrument #1's error, one level up.

This was published to the journal as finding 4 and retracted at commit `27cef54`, twenty
minutes later, in the same session, by the same author.

### 4.4 The identity mechanism that never worked

All three per-host overlays carried `hostname`, `username` and `group`, documented in
`machines.md` and the `sync-opencode` skill as the mechanism giving each host its identity.

```
$ grep -ro "hostname" node_modules/@opencode/schema/ | wc -l
0
```

`hostname` and `group` are not v2 config keys and never were. v2 discards them silently -
no warning. `username` is real but derived from the OS `$USER`, so it reads `sigit`
everywhere and cannot discriminate hosts. The plugin API's `ctx.location` carries
`directory` / `workspaceID` / `project` and no hostname either.

Host identity is environmental: `uname -n` (`fedoraWSL`) and `WSL_DISTRO_NAME`
(`FedoraLinux-44`, the value `wsl.exe -d` expects). The overlay *filename* is the only
per-host identifier that has ever been reliable.

The root cause was a script. `bootstrap-wsl.sh` section 10b *generated* those keys into
every new host's overlay, so hand-stripping them would have reintroduced them on the next
rebuild. The generator now emits only `{"username": ...}`, with the proof and a
"do not re-add" note (hub commit `e9610d4`).

### 4.5 Overlays are inert, and the mcp block is host-local

Testing whether an overlay could supply `mcp` - the original goal, so per-host paths could
live in overlays rather than the shared file:

| Test | Result |
|---|---|
| Overlay sets `mcp`; `mcp` removed from shared config | **no servers at all** |
| Overlay sets a distinctive `username` | ignored |
| ...and `username` also removed from the shared config | **still ignored** |

The overlay file is *read* - it appears in `debug config`'s source list - but its values
never reach the effective config. So `mcp` must stay in the shared file, and the three
hosts legitimately differ there:

| | `mcp` key | command form |
|---|---|---|
| hub | present | `npx -y` |
| Fedora | present | direct `node <abs>/dist/index.js` |
| Debian | present | direct `node` path |
| Windows | **absent** | served from its overlay |

This was staged, detected before the service restart, and fully reverted. The change is
now explicit: `opencode.json` is entirely host-local, never written by the plugin, guarded
by a read-only drift report that calls out `mcp` as expected so it cannot mask a real
difference. The accepted cost is that this file can now drift with nothing flagging it.

### 4.6 A bash invocation that never ran the command

The new plugin failed its first dry-run with, on every step:

```
exit=126 - /usr/sbin/md5sum: /usr/sbin/md5sum: cannot execute binary file
```

The cause was my own abstraction:

```js
run("bash", [...via, "md5sum", pathA, pathB])   // via is []
```

which expands to `bash md5sum /pathA /pathB`. Bash resolves `md5sum` via PATH and tries to
**interpret the binary as a shell script**. The command never ran. `md5sum` works fine
from a normal shell, which is exactly why it was confusing - and it cost a full debug
cycle, during which I misdiagnosed it twice as a corrupt binary and then as a broken PATH.

Fixed with a single code path (`runCmd`) that builds one quoted command line for
`bash -c`, so a caller cannot produce that shape again.

### 4.7 Instrument #3: every host green, fleet seven commits apart

With the plugin built and passing on Fedora, the fleet-wide parity check found what
per-host self-checks structurally could not:

```
plan  bare main : 7ac5d0d
plan  fedora    : 7ac5d0d
plan  debian    : 5b33a55     <- 7 commits behind
plan  windows   : 7ac5d0d
```

Debian had been behind the whole session. Every host verified *itself* green via
`fleet_sync`, because a self-check can only see its own tree. Divergence is only
detectable by comparison, and the plugin cannot compare from one host - a distro cannot
reach the other distro, and a bare repo is not a shell.

Converged with each host's own hardened script (`.sh` on Debian, `.ps1` on Windows),
both exit 0. All six locations now agree:

| | plan | mem0 |
|---|---|---|
| bare repo | `7ac5d0d` | `88a50ec` |
| Fedora | `7ac5d0d` | `88a50ec` |
| Debian | `7ac5d0d` | `88a50ec` |
| Windows | `7ac5d0d` | `88a50ec` |

## 5. Diagnosis

The unifying failure is not carelessness. It is asking an instrument a question outside
its domain and treating the answer as evidence. In order of how the answers were produced:

| Claim | Instrument consulted | What it could have shown | What it was asked |
|---|---|---|---|
| "the config is fine" | running service | boot-time config | current disk state |
| "the file shape is wrong" | normalised output | how the tool renders | what the file must contain |
| "the fleet is converged" | this host's git tree | local convergence | cross-host agreement |

None of the three tools was broken. Each was asked to prove something it structurally
could not.

A second, compounding factor: **the log is not a passive record.** It records the commands
run against it. Grepping it for a string that also appeared in my own `grep` command line
produced two phantom "today" entries that first looked like a live bug. It is also a
*binary* file, so plain `grep` undercounted 28 real errors as 11, then 0. (`grep -a`, and
filter with `grep -av 'command=/bin/bash'`.)

## 6. Preliminary Assessment

The fleet is converged and the plugin is built, tested, and propagated. `fleet_sync` builds
every TypeScript plugin from the root `tsc`, verifies shared config files, reports
`opencode.json` drift read-only, and converges both git stores. The 5-plugin invariant
holds on all three hosts.

One design decision is load-bearing and worth restating: `session.end` runs the **safe
subset only** - build, stores, parity - and never writes config. The `fleet_sync` tool is
the only write path, and it is operator-invoked. A hook that can rewrite config unattended
is the failure mode behind the 2026-09-26 outage.

## 7. Solution Summary

| finding | disposition |
|---|---|
| Spec named the live install as `SOURCE` | **Corrected.** Hub is `git/opencode-v2`; the distinction is now written into `task-claim-audit`. |
| `debug config` reads the service | **Documented** in `machines.md` and the handoff, with the working invocation. |
| `mcp.servers` schema drift | **Retracted** (`27cef54`). Both shapes work. |
| `hostname` / `group` are not config keys | **Fixed at source** in `bootstrap-wsl.sh` (`e9610d4`); all live overlays stripped. |
| Overlays cannot supply `mcp` | **Accepted.** `opencode.json` is host-local; guarded by a read-only diff. |
| `bash md5sum` never ran the command | **Fixed** via a single `runCmd` code path. |
| Debian 7 commits behind | **Converged.** All six store locations agree. |
| Plugin 404s | **Settled.** Cosmetic; the plugin loads. Was archived prematurely and reopened. |
| `sync-opencode` skill | **Kept, deliberately** - it uniquely holds the NEVER-sync list, credential rotation, substitution policy and two hazard write-ups. |
| Fleet-sync plugin | **Built and shipped** (hub `498014f`); task archived (`c6b8727`). |

## 8. Verification Plan

- Effective config confirmed on Fedora and Debian via a **fresh process**:
  `mcp servers: ['gws','mem0']`, `username: sigit`.
- gws confirmed with a real `tools/call list_filters` (149763 content chars) - not
  `mcp list`, which is known to lie here.
- All three hosts: 5 plugins resolve from `index.ts`; `dist/index.js` md5-identical
  (`acaf51e0fb`).
- Both stores agree across bare repo, Fedora, Debian and Windows.
- `fleet_sync` dry-run and real run both `ok`; the real run created **no new commits**,
  confirming idempotency.

## 9. Pending Actions

- **Restart the opencode service** from a terminal, outside any session. It is the parent
  process of any session's shell tools, so killing it from inside one terminates the
  session that issued the kill. Until then the `tasks` handoff excerpt and the
  `fleet_sync` tool are not live in a fresh session.
- **Does v1 support any per-host config layer at all?** If it does not, the overlay finding
  stops being a downgrade argument entirely. Untested, because the homelab's v1 config
  location is still unknown - and it remains the cheapest experiment available.
- **Are the plugin 404s cosmetic or a real v2 packaging problem?** Open since 2026-09-29.
  Note `google-workspace` returns HTTP 200 on npm and is **not ours** - a real package that
  the live config references by bare name.
- **Fleet parity is a script, not the plugin.** `parity.sh` is run ad hoc. Making it
  automatic needs a remote-execution path that does not exist.

## 10. Recommendations

1. **Never verify a change you just made with a tool that reads the running process.**
   Force a fresh process, or restart the thing that holds the old state. This bit twice in
   one session; both times the change was staged, "verified" green, and was actually broken.
2. **When two checks disagree, believe disk and believe the fresh-process reading.** The
   disagreement *is* the finding - some tool is reading a vantage point that cannot see
   your change. Do not average them.
3. **Do not infer a defect from a tool's output shape.** Before changing a file because a
   tool printed something unexpected, confirm the tool is reporting a *requirement* rather
   than a *rendering*. Cheapest test: try the alternative and see whether both are read.
4. **A self-check cannot detect divergence.** Every host reporting itself green while the
   fleet is seven commits apart is not a bug in the checks - it is what a self-check is.
   Cross-host agreement needs a comparison from outside, and that comparison should be a
   first-class artifact, not something run by hand.
5. **Retract in place, not quietly.** The `mcp.servers` claim was published and then
   retracted at the same commit location twenty minutes later. The wrong inference is part
   of the record; editing it out would have left only the conclusion.
6. **When a task spec's central question was never tested, the task should not have been
   archived.** The 2026-09-29 "no downgrade" verdict counted the plugin 404s among "local
   mistakes, not v2 problems", on a hypothesis the task file itself said to test before
   changing anything. It then closed with every box unchecked. Re-opened this session; the
   answer turned out to be "cosmetic", but nobody had checked.

---

*Narrator: the most expensive mistake of the day was reading a tool's output and believing
it described the world. It described the tool.*

Generated with Space Bunny Free by OpenCode
