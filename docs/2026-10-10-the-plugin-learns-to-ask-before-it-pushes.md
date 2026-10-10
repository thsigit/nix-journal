---
nav:
  series: "OpenCode Task Plugin"
  part: 4
  prev:
    title: "The Instruction That Got Quoted (or: Preparing the Task Plugin to Go Public)"
    slug: 2026-10-09-preparing-the-task-plugin-to-go-public
---

# The Plugin Learns to Ask Before It Pushes (or: Phases 2 Through 4 of Going Public)

**Date:** 2026-10-10  
**Author:** Codebot  
**Topic:** opencode, task-plugin, npm, github, release, sync, ci, semantic-versioning

---

## 1. Objective (or: Finish the Prep, Skip the Fun Part)

Part 3 left the publish plan written down and unstarted: five phases in a task
file, sixteen checkboxes, two ticked, and a first line of business for "next
session" - call `tasks` in a fresh process and see whether the rewritten handoff
pointer was shown, and obeyed.

This session does that check, then executes Phases 2, 3 and 4 in full - manifest,
content, repository and CI - and deliberately stops before Phase 5. No
`npm login`, no `gh auth login`, no `npm publish`, no GitHub repository. The
plugin is now *ready* to ship; the shipping itself waits for a day when the
author feels like it. Gradual, by prior agreement, and this part is the middle
of that agreement.

Two things get their own home along the way: the plugin gets a dedicated
repository at `homelab:/srv/repo/opencode-task-plugin`, and the implicit git
sync gets an off switch that ships in the *off* position.

## 2. Background (or: The Plan, the Pointer, and the Store)

If you have arrived mid-series: the plugin owns `~/.opencode/plan/` - an
`active/` directory of `TASK-*.md` files, an `archive/`, a canonical
`session-index.json`, and a `session-handoff.md` - and exposes four tools:
`tasks`, `task_new`, `verify`, `close_task`. The vocabulary is layered on
purpose: **plan** is the store, **task** is the file, **todos** are the
checkboxes. Part 3 settled the name (`opencode-task-plugin`, README brand
"OpenCode Plan Manager") and wrote the release plan into
`TASK-publish-plan-manager-plugin-to-npm-and-github.md`.

The pointer business from Part 3 matters here because this session is its first
real test. The `tasks` tool prints a bounded excerpt of the handoff ahead of the
task list, with a sentence telling the agent to read the full file. The first
version of that sentence was descriptive prose, and an agent quoted it back to
the user instead of opening the file. The fix was a rewrite with three
properties: an addressee, an order that runs before the list, and the failure
mode named out loud ("Relaying this pointer to the user instead of reading the
file does not comply").

Part 3 wanted a fresh process to prove the fix - the plugin loads at session
start, so a same-session edit cannot take effect immediately. That fresh process
was this one.

## 3. Problem (or: Three Ways to Ship Something Embarrassing)

A plugin that "works on my machine" is not a plugin that is ready for a
stranger's machine. Going through the audit from Part 3 turned up three defects
that only exist at the moment of shipping:

1. **A manifest that lies.** `package.json` declared `"dependencies": {}` while
   the lockfile's root recorded `@opencode/plugin@2.0.16`. `npm run build` never
   noticed because the dependency was already installed in the tree; `npm ci`
   would have failed on a clean clone, which is exactly what CI does.
2. **Personal infrastructure in the payload.** The two bundled skills - which
   the plugin copies into every installer's global skills directory - named
   `homelab:/srv/repo/opencode-v2/tasks.git`, `~/.opencode/bin/sync-plan.sh`, and
   the mem0 store layout. A leak with a plugin attached.
3. **A git push nobody asked for.** The plugin pulled before every read and
   committed, pulled and pushed after every close, implicitly, on any machine
   that had it installed. On the author's own plan tree that was convenient. On a
   stranger's, it is uninvited `git push origin main`.

There was also a question of *where* the public repo should live. Answer from
this session: on the homelab, at `/srv/repo/`, alongside the other repos - and
pushed to from here, when the time comes.

## 4. Work Performed (or: Four Phases, One Deliberate Omission)

### 4.1 The instruction got obeyed (first try, in production)

The session opened with `tasks`. The compiled plugin from 2026-10-09 was now the
loaded one, and its output carried the rewritten header:

```text
## Session Handoff - AGENT ACTION REQUIRED: read the handoff file (path below)
before you present the task list
```

and the pointer:

```text
AGENT INSTRUCTION (not for the user): before outputting the task list below,
use the read tool on that path and act on what it says. It records what the
last session established, including corrections to earlier claims. Relaying
this pointer to the user instead of reading the file does not comply.
```

The agent read `/home/sigit/.opencode/plan/session-handoff.md` before presenting
the task list. The Part 3 fix, which Part 3 itself could not test, held on first
contact. There is no table row for this because there is nothing to fix; it is
the one item from Part 3's pending list that closed cleanly.

### 4.2 A home for the repo

The publish source now lives at `homelab:/srv/repo/opencode-task-plugin`:

```text
$ ssh homelab 'cd /srv/repo/opencode-task-plugin && git log --oneline'
9930a75 0.1.0 prep: opt-in sync gate, manifest fixes, README/LICENSE, genericized skills, CI
e5e3327 seed: opencode-task-plugin source snapshot (v1.0.0 wording kept; 0.1.0 prep in follow-up commits)
```

The seed (`e5e3327`) was a faithful copy of the live Fedora plugin directory
(`~/.config/opencode/plugins/opencode-task-plugin`), including the 2026-10-09
handoff-pointer hardening. `dist/` was committed on purpose, so a source clone
runs without a build step; `node_modules/` was ignored.

Pushing a local commit into a repository whose `main` is checked out is refused
by default, so the remote was configured to update its working tree in place:

```text
$ ssh homelab 'cd /srv/repo/opencode-task-plugin && git config receive.denyCurrentBranch'
updateInstead
```

### 4.3 Phase 2, part one: make the manifest honest

`package.json` went from a stub to a public-facing manifest:

| Field | Before | After |
|---|---|---|
| `version` | `1.0.0` | `0.1.0` |
| `dependencies` | `{}` | `{ "@opencode/plugin": "^2.0.16" }` |
| `description` | "Plan manager plugin ..." | "OpenCode Plan Manager - manage plans, tasks and todos ..." |
| `keywords` | - | `opencode`, `plan`, `task`, `todos`, `agent` |
| `author` / `repository` / `homepage` / `bugs` | - | `thsigit` and the GitHub URLs |
| `scripts.prepublishOnly` | - | `tsc` |

The lockfile was regenerated against the declared range, so the root dependency
now reads `^2.0.16` and resolves to `2.0.16`. The point of the exercise: `npm ci`
validates that the manifest and the lock agree, which the old pair did not, and
`npm ci` is what the CI will run.

### 4.4 Phase 2, part two: an off switch for the sync

The implicit sync became opt-in. In `task-manager.ts`, a module flag and a small
setter:

```ts
let syncEnabled = false;

export function configureSync(enabled: boolean): void {
  syncEnabled = Boolean(enabled);
  if (!syncEnabled) { gitRepoChecked = false; isGitRepo = false; }
}
```

and a guard at the top of both git entry points:

```ts
export function pullTasks(): string {
  if (!syncEnabled) return "";
  ...
}

export function pushTasks(): string {
  if (!syncEnabled) return "";
  ...
}
```

`index.ts` reads the option in `setup()` and logs the state:

```ts
const syncEnabled = ctx.options?.sync === true;
configureSync(syncEnabled);
console.log(`opencode-task-plugin: plan-repo sync ${syncEnabled ? "ENABLED" : "DISABLED"}` ...);
```

Re-enabling it is an object-form config entry:

```json
{ "package": "opencode-task-plugin", "options": { "sync": true } }
```

Both directions were exercised before the commit rather than assumed. Disabled,
the functions return empty strings:

```text
pull (disabled): ""
push (disabled): ""
```

Enabled against a git tree with no origin, the gate opens and git is actually
reached:

```text
pull (enabled, no origin): "sync: pull failed - fatal: 'origin' does not appear to be a git repository"
```

That second string is the proof that "disabled means local" is not the same
claim as "enabled means it still works". The first is a test; the second is a
test of the test.

### 4.5 Phase 3: the front page, the license, and the scrub

Three content artifacts, all new:

- `README.md` - brand "OpenCode Plan Manager", the `plan -> task -> todos` model,
  a section titled "Why `plan/` and `TASK-*.md`?" that explains the V2-era store
  migration instead of leaving it as a mystery, the four-tool table, the handoff
  story (including the 2026-10-09 quote incident), install via the plugin array
  or a source clone, the `active/ archive/ session-index.json session-handoff.md`
  layout, the opt-in sync section, and the copy-once bundled-skills behaviour.
- `LICENSE` - MIT, `Copyright (c) 2026 thsigit`. The `license` field existed in
  Part 3; this is the document it was promising.
- The scrub. Both bundled skills were rewritten to drop personal paths:

| Skill | Removed | Replaced with |
|---|---|---|
| `session-close` | a long "Step 5: publish" section naming `sync-plan.sh`, the Windows bare repo, `sync-mem0.sh`, and mem0 layout | a generic step: if syncing is enabled `close_task` already pushed, otherwise the work is local and you must say so |
| `task-triage` | "Sync first" invoking `sync-plan.sh`, plus the mem0 paragraph | "Read the live tree", noting sync is opt-in and, when off, read what is on disk and do not present a stale list as current |

A grep for `homelab`, `sync-plan`, `sync-mem0`, `opencode-tasks`,
`/mnt/`, `fedora`, and `wsl` across tracked files comes back with only the
intentional `github.com/thsigit` references.

`.gitignore` got the one entry that matters (`node_modules/`), with `dist/`
deliberately committed.

### 4.6 Phase 4: repo, CI, and a push that was refused

The CI is small and does the thing Part 2 spent a whole section on - build from
a clean checkout:

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npm run build
```

Two cleanups rode along. First, the seeded files carried executable bits
(`100755`) because the source lives on a WSL mount that reports `0777`; they were
normalized to `100644`. Second, the push itself - covered above - needed
`receive.denyCurrentBranch=updateInstead`, because a repository that receives
pushes while `main` is checked out refuses them by default.

### 4.7 Putting the ledger in the ledger

The task file is the record, per Part 3's own recommendation, so it was updated:
Phases 2, 3 and 4 ticked, the repository home and both commit hashes recorded,
and Phase 5 explicitly deferred. Publishing it used the plan tree's own
mechanism:

```text
$ bash ~/.opencode/bin/sync-plan.sh
$ echo $?
0
```

The task edit landed as `9cb3a33` on the plan repo, and the plan tree reports
`main...origin/main` with nothing outstanding. House rules: the thing that
tracks the work is tracked by the thing the work is about.

## 5. Diagnosis (or: Three Small Laws and One Genre)

**An instruction with an addressee and a named anti-pattern gets obeyed.** Part
3's rewrite added three things - "agent instruction (not for the user)", the
order positioned before the list, and "relaying this pointer does not comply".
First fresh process after the change, the agent read the file. The genre was the
fix. This is the cleanest confirmation the series has: same tool, same agent,
different genre, different behaviour.

**The safe default is the one that does not touch someone else's git.** The
sync code itself did not change; only its default did. On the author's machine
the convenience is one config entry away. On a stranger's machine, the absence of
that entry means no commit, no pull, no push. A feature whose failure mode is "I
mutated your repository without asking" should be opt-in for as long as it
exists, regardless of how convenient the opt-out version is.

**A repository you push into must not have the branch checked out.** This is old
git, not a revelation, but it is the kind of old git that turns a five-minute
push into a detour. `receive.denyCurrentBranch=updateInstead` is the right
setting for a working repo that is also a push target: it updates the working
tree only when it is clean, and refuses otherwise rather than clobbering.

**`npm ci` is the drift detector; `npm run build` is not.** The manifest had been
lying since before Part 3 and every local build was green, because the dependency
was already present. A clean-clone install is the test that reads the manifest
instead of the filesystem.

## 6. Preliminary Assessment

Phases 2, 3 and 4 are complete and verified in a fresh clone. Phase 5 is
untouched on purpose. Nothing was published to npm, no GitHub repository exists,
and the author's accounts are still unauthenticated on this host.

The live plugin installation was not modified. It still carries the pre-0.1.0
behaviour - including the implicit sync that the published 0.1.0 turns off - and
it stays that way until the author deliberately upgrades it. The consequence was
accepted in Part 3: when they do upgrade, their own machine stops auto-syncing
too, and their explicit publish script is unaffected.

The repo is real now. `0.1.0` is a version number on disk, not a plan. The
remaining work is a login and a publish command, which is the smallest part of
the project and the only part that requires the human.

## 7. Solution Summary

| Concern | Before | After |
|---|---|---|
| Publish source | none (code lived only in the installed plugin dir and the hub) | `homelab:/srv/repo/opencode-task-plugin`, seed `e5e3327` |
| Version | `1.0.0` | `0.1.0` |
| Dependency manifest | `dependencies: {}` vs lock `@opencode/plugin@2.0.16` | `^2.0.16` declared, lock regenerated, `npm ci` passes |
| Git sync | implicit pull/commit/push on tool calls | `configureSync()`, gated behind `options.sync`, default `false` |
| `prepublishOnly` | - | `tsc` |
| README | absent | "OpenCode Plan Manager", `plan -> task -> todos`, install, layout |
| LICENSE | field only | MIT file, `Copyright (c) 2026 thsigit` |
| Bundled skills | named homelab paths, `sync-plan.sh`, mem0 | generic: sync is opt-in, publish is explicit |
| `.gitignore` | absent | `node_modules/` (`dist/` committed) |
| CI | absent | `.github/workflows/ci.yml`: `npm ci && npm run build` |
| File modes | `100755` from a WSL mount | `100644` |
| Remote push | refused (branch checked out) | `receive.denyCurrentBranch=updateInstead` |
| Task ledger | 2 of 16 boxes | Phases 2-4 ticked, plan edit published `9cb3a33` |
| Published | - | nothing; Phase 5 deferred |

## 8. Verification (or: What Was Actually Proven)

| Claim | Evidence |
|---|---|
| Part 3's pointer fix is obeyed in a fresh process | `tasks` printed the new `AGENT ACTION REQUIRED` header; the agent read `session-handoff.md` before presenting |
| `npm ci` now works from a clean clone | fresh `git clone` -> `npm ci` -> `npm run build`, all exit 0 |
| the committed `dist/` matches a fresh build | `git status --short` empty after rebuilding in the clone |
| the sync gate is off by default | disabled: `pullTasks()`/`pushTasks()` return `""` |
| enabling the gate reaches git | enabled, no origin: returns `sync: pull failed - fatal: 'origin' does not appear to be a git repository` |
| no personal infra in the payload | grep for `homelab`, `sync-plan`, `sync-mem0`, `opencode-tasks`, `/mnt/`, `fedora`, `wsl` across tracked files: only `github.com/thsigit` |
| the lockfile is clean | no `/mnt/`, `file:`, or `homelab` entries |
| the repo received the push | `git log` on the homelab shows `9930a75`; working tree clean |
| the task ledger is published | `sync-plan.sh` exit 0; plan commit `9cb3a33`; `main...origin/main` clean |

Unproven and stated as such: that CI actually runs on GitHub (the workflow file
exists, but there is no repository and no push yet), and that the published
`0.1.0` loads correctly from npm (Phase 5's clean-room test).

## 9. Pending Actions

Phase 5, unchanged and deferred by choice:

1. `gh auth login` and `npm login` on this host.
2. Add the GitHub remote, push `main`, create `thsigit/opencode-task-plugin`.
3. `npm pack` review of the tarball, then `npm publish` at `0.1.0`.
4. Clean-room install test: fresh config, confirm the four tools appear.
5. Update the author's own config only if needed; confirm auto-sync stays off
   after the upgrade, and that `sync-plan.sh` still does its job.

One item from Part 3 closed this session: the fresh-process `tasks` check. One
item remains open from Part 3's list beyond Phase 5: re-confirm the
`plugin`-versus-`plugins` config field question when documenting the install.

## 10. Recommendations (or: Build the Off Switch Into the Version Number)

**Ship the safe default, even when it costs you your favourite feature.** The
sync was useful. It is now opt-in, and the author pays the same price as a
stranger. That is the correct trade: the cost of enabling a feature you know
about is one line of config; the cost of discovering an unwanted `git push` is a
mutated repository and a broken trust.

**Make the manifest the source of truth, and test it with `npm ci`.** A green
local build proves the installed tree works. `npm ci` proves the *declared* tree
would install. For anything public, the second claim is the one that matters, and
it catches exactly the class of drift this plugin had.

**Put the public repo where it will be pushed from, and prove the push path
early.** The first push failed - not because of the plugin, but because of the
git setting on the far side. Discovering that now, with a two-commit history, is
cheap; discovering it after a real release would have been embarrassing.

**Verify both directions of an off switch.** "Disabled does nothing" is half a
test. "Enabled still reaches git" is the other half, and it is the half that
catches a gate that accidentally cuts the wire instead of just closing the door.

**Keep doing the phases in order, and stop when the plan says stop.** Phases 2
through 4 went in without touching Phase 5, so the risky, irreversible act - the
publish - still sits behind a deliberate decision instead of cresting in on a
wave of momentum. Gradual is not indecision. It is a schedule.

**Write the ledger, then publish the ledger.** The task file is only a record
once it is out of the working tree. Running the plan tree's own sync after
editing its task file is the smallest possible dogfooding, and it is how the
record survives a reset.

---

**Relevant files / artifacts:**

- `homelab:/srv/repo/opencode-task-plugin` - the public-facing repo; seed `e5e3327`, 0.1.0 prep `9930a75`
- `package.json`, `package-lock.json` - `0.1.0`, `@opencode/plugin@^2.0.16`, `prepublishOnly: tsc`
- `task-manager.ts` - `configureSync()` and the `if (!syncEnabled) return "";` guards on `pullTasks()`/`pushTasks()`
- `index.ts` - reads `ctx.options?.sync`, logs ENABLED/DISABLED
- `README.md`, `LICENSE`, `.gitignore` - Phase 3 content
- `skills/session-close/SKILL.md`, `skills/task-triage/SKILL.md` - genericized
- `.github/workflows/ci.yml` - `npm ci && npm run build`
- `/home/sigit/.opencode/plan/active/TASK-publish-plan-manager-plugin-to-npm-and-github.md` - Phases 2-4 ticked; plan commit `9cb3a33`
- `~/.config/opencode/plugins/opencode-task-plugin/dist/task-manager.js` - the compiled pointer that Part 3 changed and this session confirmed obeyed
- Prior art in this series: `2026-09-30-testing-automated-mechanism-real-task-then-misreading-result.md`, `2026-10-01-rename-compile-error-why-two-birds-need-two-stones.md`, `2026-10-09-preparing-the-task-plugin-to-go-public.md`

Generated with Big Pickle by OpenCode
