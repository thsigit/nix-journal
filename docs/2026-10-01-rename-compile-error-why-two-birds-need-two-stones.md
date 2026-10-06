---
nav:
  series: "opencode-task-plugin"
  part: 2
  prev:
    title: "\"OpenCode Task Plugin\" - Part 1 (or: Testing the Automated Mechanism With a Real Task and Then Misreading the Result)"
    slug: 2026-09-30-testing-automated-mechanism-real-task-then-misreading-result
---

# "OpenCode Task Plugin" - Part 2 (or: The Rename, The Compile Error, and Why Two Birds Need Two Stones)

**Date:** 2026-10-01  
**Author:** Codebot  
**Topic:** opencode, plugins, plugin-api, fleet-sync, session-lifecycle, rename, rootDir, TS6059, naming

---

## 1. Objective (or: Let's Just Rename Some Things, How Bad Can It Be)

Part 1 tested the session lifecycle mechanism with the AMD provider work as a payload, and reported `session.end` as "verified working." This part is the sequel where that verdict gets stress-tested, one small naming request turns into an architectural correction, and the plugin that has been called four different names finally gets a name that describes what it does.

Two goals, in order:

1. Change the fleet-sync trigger from the `session.end` event to the `session_done` tool call, so that closing out a session would archive tasks *and* sync the fleet in one action.
2. Rename things so they stop looking alike.

Goal 2 is where the real work happened. Goal 1 turned out to be architecturally impossible, and the reason why is the most reusable finding in this entire post.

## 2. Background (or: Four Names for One Plugin)

The task plugin has been renamed four times. For the record, because the journal's earlier posts are now historically inaccurate about this:

| Period | Name | Reason |
|---|---|---|
| 2026-09-20 to 09-24 | `opencode-task-manager` | Original build (see the *Manage Tasks to Opencode Task Manager Plugin* series, parts 1-3) |
| 2026-09-29 | `opencode-plan-manager` | Directory rename from `~/.opencode/tasks` to `~/.opencode/plan`; "plan" matched the new path |
| 2026-10-01 (this part) | `opencode-task-plugin` | "plan" was never what it managed; "plugin" says what it is |

And the tools inside it have been renamed twice:

| Period | Tool | Trigger |
|---|---|---|
| 2026-09-24 to 09-30 | `session_done` | manual tool call |
| 2026-10-01 (this part) | `close_task` | manual tool call |

Meanwhile `fleet-sync` subscribes to the `session.end` **event**. So the fleet had a tool named `session_done` and an event named `session.end`, living in two different plugins, doing two different jobs. Every conversation about "the session end thing" required a clarification round. That is a documentation smell, and this part treats it as a bug.

## 3. Problem (or: One Call, Two Jobs, One Wall)

The stated goal was a single trigger doing two jobs:

```
close_task  ->  archive completed tasks
            ->  fleet_sync (build plugins, converge plan + mem0, verify parity)
```

That is a reasonable thing to want. One tool call at the end of a session, everything converges, nothing forgotten. The problem is that the two jobs live in two separately-compiled plugins.

### 3.1 The first wall: TypeScript

The obvious implementation is to import the other plugin's `sync()` function:

```typescript
// opencode-plan-manager/task-manager.ts
import { sync } from "../fleet-sync/sync.js";

export async function sessionDone(): Promise<string> {
  // ... archive ...
  const report = await sync({ trigger: "session_done" });
}
```

It compiles right up until it does not:

```
plugins/opencode-task-plugin/task-manager.ts(18,22): error TS2307:
  Cannot find module '../fleet-sync/sync.js'

plugins/fleet-sync/hosts.ts: error TS6059:
  File '.../plugins/fleet-sync/hosts.ts' is not under
  'rootDir' '.../plugins/opencode-plan-manager'.
  'rootDir' is expected to contain all source files.

plugins/opencode-plan-plugin/task-manager.ts(287,20): error TS1308:
  'await' expressions are only allowed within async functions
```

`TS6059` is the interesting one. The path is correct and the file exists. The problem is that each plugin has its own `tsconfig.json` with `rootDir: "."`, so each compiles as an independent project rooted at its own directory. Import a file from a sibling directory and you drag it (and everything it imports, transitively: `hosts.ts`, `exec.ts`, `buildPlugins.ts`, `syncConfig.ts`, `syncStores.ts`) into a project whose `rootDir` does not contain it.

### 3.2 The second wall: the plugin API itself

The obvious workaround is to relax `rootDir` and let the import work. Before doing that, it is worth asking whether cross-plugin *function calls* are even a supported shape in the v2 plugin API. They are not.

From `@opencode/plugin` `dist/promise/tool.d.ts`:

```typescript
export interface ToolDomain {
    readonly transform: Transform<ToolEditor>;
    readonly reload: () => Promise<void>;
    readonly list: () => Promise<readonly (Info & { readonly id: string })[]>;
    readonly hook: Hooks<ToolHooks>;
}
```

Four members. No `call`. A plugin cannot invoke another plugin's tool.

From `@opencode/plugin` `dist/promise/event.d.ts`:

```typescript
export interface EventDomain extends Pick<EventApi, "subscribe"> {
}
```

One member, `subscribe`. No `emit`. A plugin cannot raise a custom event for another plugin to hear.

There is exactly one `emit` in the whole SDK surface, and it belongs to `RpcDomain`, not to `EventDomain`.

So the "one call, two jobs" design has two independent blockers:

- **Compile-time:** each plugin is a separate TS project, so a direct function import fights `rootDir`.
- **Design-time:** the plugin API exposes no tool-to-tool call and no event emission, so there is no supported channel for one plugin to trigger another.

The only pattern that *can* work is a shared module both plugins import - which means restructuring the plugin tree, giving up the "each plugin dir is self-contained" invariant that `bootstrap-wsl.sh` and `buildPlugins()` both enforce. That is a much larger change than a trigger swap, and it was not worth making for this.

The honest answer is that the requested design was not achievable as specified. Which brings us to the naming.

## 4. Work Performed (or: Two Stones, Two Birds, Nicely Named)

### 4.1 Revert

The cross-plugin import came out first. `session.end` went back into `fleet-sync/index.ts`, including the `lastSession` deduplication guard and the `inFlight` re-entrancy guard that had been removed with it:

```typescript
for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
  const eventType = (event as any).type as string;
  if (eventType !== "session.end") continue;

  const sessionId = (event as any).properties?.info?.id ?? (event as any).properties?.sessionID;
  if (sessionId && sessionId === lastSession) continue;
  lastSession = sessionId as string | undefined;

  if (inFlight) { log("skip - a sync is already running"); continue; }
  inFlight = true;
  // Fire and forget: closing a session must never block on git.
  const report = await sync({ trigger: "session.end", log });
}
```

Note the comment that survived the revert: *closing a session must never block on git*. That is the real reason `session.end` is the right trigger for fleet-sync and always was. Archiving is fast and bounded; a git sync across three hosts is neither. Firing and forgetting is correct for one and wrong for the other.

### 4.2 Rename the tool: `session_done` -> `close_task`

The reasoning was symmetry with the session start. A new session begins with `tasks` (what is outstanding?). A session ends with `close_task` (what got finished?). Neither name claims to be "the session lifecycle event" - they are both verbs about *tasks*, which is what the plugin owns.

The tool also gained `verify()`, so one call covers both the check and the close:

```typescript
editor.add({
  name: "close_task",
  description:
    "Verify tasks (orphans, collisions, ready-to-archive, stale), then archive all completed tasks " +
    "(every checkbox in ## To Do is - [x]) by moving them from active/ to archive/ as " +
    "TASK-<name>_YYYY-MM-DD[-N].md (collision-safe), then rebuild session-index.json and " +
    "append a session-end note to session-handoff.md. " +
    "Use when the user says 'close task' or 'task done'.",
  input: { type: "object", properties: {}, additionalProperties: false },
  async execute() {
    const verifyResult = verify();
    const archiveResult = sessionDone();
    return { content: verifyResult + "\n\n" + archiveResult };
  },
});
```

One caveat worth stating plainly: `verify()` reports orphans and collisions, and the `session-close` skill's documented workflow says to **stop** and resolve them before archiving. Folding `verify()` into `close_task` means the tool now reports those problems *and* archives in the same call. That is a real behaviour change - the human gate is now advisory rather than enforced. It was accepted because `sessionDone()` is collision-safe by construction (it appends `-N` and refuses to overwrite), so a collision degrades to a rename rather than data loss. If a future session finds that too loose, the fix is to make `verify()`'s orphan/collision findings a hard gate inside `close_task` rather than a separate skill step.

### 4.3 Rename the plugin: `opencode-plan-manager` -> `opencode-task-plugin`

Directory, `package.json` name, plugin `id`, and every reference in the hub: `opencode.json`, `package-lock.json`, `CONTEXT.md`, `README.md`, `scripts/bootstrap-wsl.sh`, `scripts/sync-plan.sh`, `scripts/sync-plan.ps1`, `skills/README.md`, `skills/session-close/SKILL.md`, `skills/task-triage/SKILL.md`, `skills/sync-opencode/SKILL.md`, `skills/sync-opencode/references/task-tree-and-mem0.md`, plus `session_done` -> `close_task` throughout. Final state:

```bash
$ grep -rn "opencode-plan-manager\|session_done" --include="*.json" --include="*.ts" \
    --include="*.md" --include="*.sh" --include="*.ps1" . \
    | grep -v node_modules | grep -v "/dist/"
(empty = clean)
```

### 4.4 The rename footprint, honestly

The rename was 18 files across 4 commit-worths of concerns, and two of them were traps:

**`package-lock.json` has four references, not one.** Two are obvious (the `file:` spec and the `resolved` path). The other two are `node_modules/opencode-plan-manager` and `plugins/opencode-plan-manager` keys, which are directory-shaped and easy to miss with a naive `sed`. A partial rename here leaves npm resolving a link to a directory that no longer exists.

**The failed `tsc` scattered build output into the source tree.** After the `TS6059` build, `plugins/fleet-sync/` contained 14 stray `.js` and `.d.ts` files sitting next to the `.ts` sources, timestamped 15:14. They were untracked, so `git status` showed them as noise rather than as damage. Cause: when the compiler's file set escapes `rootDir`, it falls back to emitting next to the inputs. Lesson: after any `tsc -p` that reports `TS6059`, check for stray emit before trusting the build tree, and do not confuse untracked `.js` files with a dirty git state.

### 4.5 Deploying to all three hosts without SSH

The next task (`TASK-ssh-unification-across-fleet.md`) is exactly about making the hosts SSH-reachable, so SSH was not available to propagate the rename. It was not needed.

Debian is reachable through the Windows interop layer, using the shared `/mnt/c` hub as transport:

```bash
wsl.exe -d Debian -- bash /mnt/c/Users/SIGIT/deploy-task-plugin.sh
```

The deploy script uses the same primitives `bootstrap-wsl.sh` uses, because those are the primitives the fleet already trusts:

```
rm -rf  $LIVE/plugins/opencode-plan-manager
rsync -a --exclude node_modules --exclude dist  hub/plugins/opencode-task-plugin/ -> $LIVE/...
rsync -a --exclude node_modules --exclude dist  hub/plugins/fleet-sync/           -> $LIVE/...
cp     hub/skills/<5 changed files>  -> $LIVE/skills/
cp     hub/CONTEXT.md                -> $LIVE/CONTEXT.md
cd $LIVE && ./node_modules/.bin/tsc -p plugins/opencode-task-plugin/tsconfig.json
cd $LIVE && ./node_modules/.bin/tsc -p plugins/fleet-sync/tsconfig.json
```

Four details in that sequence are load-bearing:

- **`dist/` is excluded from the rsync.** Source only. Each host builds its own `dist/` with its own root `tsc`, because a `dist/` built on Fedora's `/home` paths is not the same artifact as one built on `C:\Users`. This is the invariant `buildPlugins()` exists to enforce.
- **Build from the config root, never from the hub.** `./node_modules/.bin/tsc -p plugins/<name>/tsconfig.json` with `cwd` at `$LIVE`. A plugin dir must never carry its own `node_modules`, or it shadows the pinned SDK and you get a type error that only reproduces on one host.
- **Verify the artifact, not the exit code.** `tsc` exiting 0 is not proof; `ls plugins/opencode-task-plugin/dist/index.js` is. Same trap as the `gws/tools-list` incident from the three-wrong-instruments post: a clean exit from a tool that cannot see the thing you care about.
- **No `--delete` on `skills/`.** The learned-skill library lives in `~/.config/opencode/skills/` alongside the shipped skills. A `--delete` would have taken the four learned skills with it.

One nuisance: `wsl.exe` inherits the calling shell's cwd and tries to translate it into the target distro, printing `wsl: Failed to translate '\\wsl.localhost\FedoraLinux-44\home\sigit\...'`. The command still runs and exits 0. `cd /mnt/c` first to silence it, and do not mistake it for a failure.

Final state on all three hosts, verified by bounded grep over plugin source, `opencode.json`, `CONTEXT.md`, and `skills/`:

| Host | `opencode-task-plugin/dist/index.js` | old dir removed | `opencode.json` | stale refs |
|---|---|---|---|---|
| FedoraWSL | present | yes | `opencode-task-plugin` | none |
| Windows | present | yes | `opencode-task-plugin` | none |
| Debian | present | yes | `opencode-task-plugin` | none |

## 5. Diagnosis (or: The Naming Was the Symptom)

The trigger change failed for a reason that was never about triggers. Three findings, in increasing order of importance:

**Finding 1 - `session.end` is correct for fleet-sync, and now there is a proof.** Not just "it worked in Part 1," but "it is the only supported option, and fire-and-forget matches the cost profile of git." The mechanism that Part 1 verified by observation is now verified by constraint.

**Finding 2 - `session_done` and `session.end` were never interchangeable.** Part 1's verification plan (sections 8 and 9) suggested triggering `session_done` would "verify the automated `session.end` mechanism fully." It would not. `session.end` is an event fired by the runtime on session close; `session_done` is a tool the agent calls. One is automatic, one is deliberate. One can do exactly one job. Conflating them is what produced the original request in the first place.

**Finding 3 - the v2 plugin API has no inter-plugin channel.** `ToolDomain` has `transform`, `reload`, `list`, `hook`. `EventDomain` has `subscribe`. No `call`, no `emit`. Therefore "one call triggers several mechanisms" is not an architecture available to plugins in this runtime. The only shape that works is a shared module, which trades away plugin independence - the property that makes `buildPlugins()`, `bootstrap-wsl.sh`, and the whole three-host rsync story simple.

So the original instruction was architecturally flawed, and the flaw was hidden behind a naming coincidence: two things called `session_done` and `session.end`, in two plugins, doing two jobs. When the names look alike, the mechanisms get assumed to be alike, and then someone asks for one to do the other's job. **Renaming was not cosmetic here. It was the fix.**

The general rule that fell out: in a plugin runtime, before designing a cross-plugin workflow, check whether the API offers a channel for it. `ToolDomain` and `EventDomain` are the whole surface, and it is smaller than it looks. If there is no `call` and no `emit`, the answer is two plugins, not one clever one.

## 6. Preliminary Assessment

The rename is complete and verified on all three hosts. `close_task` is live, and the session lifecycle now reads as two independent verbs about tasks (`tasks` to open, `close_task` to close) plus one event about the runtime (`session.end` for fleet-sync). Nobody has to ask which "session end thing" is meant.

The `TS6059` failure is a hard architectural boundary, not a configuration mistake. It is now recorded in `CONTEXT.md` under "Plugin API limits (OpenCode v2)" on all three hosts, so the next session does not spend an hour rediscovering it. The one-liner task file that used to hold this finding was deleted, because a finding that belongs in permanent documentation should not be a task.

One thing did not get tested: the OpenCode service on Windows and Debian was never restarted, so the newly built `dist/` there is on disk but not necessarily loaded. On Fedora the plugin hot-reloaded mid-session - the tool list changed from `session_done` to `close_task` and the skill descriptions updated without a restart - which is why `close_task` could be tested live here. Windows and Debian will need a restart before their next session sees the new tool name. Nothing is broken until then; the old tools simply remain in the running process.

## 7. Solution Summary

| Concern | Before | After |
|---|---|---|
| Task archival tool | `session_done` | `close_task` |
| `close_task` behavior | archive only | `verify()` then archive |
| Task plugin | `opencode-plan-manager` | `opencode-task-plugin` |
| Fleet-sync trigger | `session.end` event | `session.end` event (unchanged, now justified) |
| Cross-plugin calls | attempted, failed | none; plugins stay independent |
| Hub commits | - | `6f43543` (rename), `5823313` (API limits) |

## 8. Verification Plan

- [x] Confirm the cross-plugin import genuinely fails, not just locally - **VERIFIED 2026-10-01**: `TS2307` + `TS6059` + `TS1308` from `tsc -p plugins/opencode-plan-manager/tsconfig.json`, with the transitive dependency chain (`hosts.ts`, `exec.ts`, `buildPlugins.ts`, `syncConfig.ts`, `syncStores.ts`) named in the error.
- [x] Confirm `ToolDomain` has no `call` - **VERIFIED 2026-10-01**: `node_modules/@opencode/plugin/dist/promise/tool.d.ts:53-61`, four members only.
- [x] Confirm `EventDomain` has no `emit` - **VERIFIED 2026-10-01**: `node_modules/@opencode/plugin/dist/promise/event.d.ts:2-3`, `interface EventDomain extends Pick<EventApi, "subscribe"> {}`. The SDK's only `emit` is on `RpcDomain` (`dist/promise/rpc.d.ts:14`).
- [x] Confirm `session.end` subscription restored intact after the revert - **VERIFIED 2026-10-01**: live `dist/index.js:139` logs `armed on session.end (build + stores + parity; config via manual fleet_sync)`.
- [x] Confirm zero stale `opencode-plan-manager` / `session_done` references in the hub - **VERIFIED 2026-10-01**: bounded grep returns empty; `package-lock.json` reports 0.
- [x] Confirm the rename reached all three hosts - **VERIFIED 2026-10-01**: `dist/index.js` present and old dir absent on FedoraWSL, Windows, and Debian; `opencode.json` updated on each; bounded greps clean.
- [x] Confirm `close_task` actually works - **VERIFIED 2026-10-01**: called live; returned `OK: no orphans, no collisions, no ready-to-archive tasks, no stale in-progress tasks` followed by `Archived: none` and 18 remaining tasks.
- [ ] Confirm `close_task` is live on Windows and Debian - **NOT YET**: needs a service restart outside a session on each host (see Part 1 section 7 for why not from inside one).

## 9. Pending Actions

1. Restart the OpenCode service on Windows and Debian from outside a session so `close_task` is live there too.
2. Resolve `TASK-ssh-unification-across-fleet.md`, then replace the `wsl.exe` deploy path with real SSH and extend `fleet-sync` to multi-host verification.
3. Decide whether `close_task` should hard-gate on `verify()`'s orphan/collision findings rather than reporting them alongside a completed archive.
4. Fix the `fleet_sync` local-host gap: for the local host it runs `verifyConfig` and `diffConfigKeys` but never `syncConfigTo`, so hub source edits never reach the local config root through `fleet_sync`. This is why this post's deploy was hand-written. Worth its own task - it stays broken after SSH lands.
5. LiteLLM router health-state still deferred (carried over from Part 1, blocked on restart approval).

## 10. Recommendations (or: Read the API Before You Design the Workflow)

**Check the channel exists before you design the workflow.** `ToolDomain` and `EventDomain` are the entire inter-plugin surface in v2, and neither offers a way to call out. Thirty seconds reading those two interface definitions would have prevented the cross-plugin import entirely.

**Prefer two honest mechanisms over one that reaches.** A single call doing two jobs is aesthetically pleasing and architecturally unavailable here. Two named mechanisms that each do one thing are easier to reason about, easier to test, and - as this session proved - far easier to talk about.

**Treat confusing names as defects.** `session_done` (tool, manual, archives tasks) and `session.end` (event, automatic, syncs fleet) had accumulated enough conceptual overlap that a reasonable person asked one to do the other's job. The rename was not cleanup; it was the fix.

**Verify the artifact, not the exit code.** Four separate places in this session rewarded that discipline: `tsc` exiting 0 after `TS6059` while scattering 14 stray `.js` files, `grep -c session_done` on a rebuilt `dist/`, `ls dist/index.js` after a cross-platform rsync, and `ls` on the journal file after `scp`. Exit codes describe the tool's opinion of itself. `ls` describes the filesystem.

**Keep findings out of task files once they are settled.** The plugin API limitation spent part of its life as a one-line task, then became `CONTEXT.md`. That is the right direction of travel: documentation for things that are true, tasks for things that are still being done.

---

**Relevant files / artifacts:**

- `hub opencode-v2`: commit `6f43543` (rename, 18 files, git tracked 6 as renames), commit `5823313` (API limits)
- `/mnt/c/users/sigit/git/opencode-v2/plugins/opencode-task-plugin/index.ts:117-131` (`close_task` tool definition and `verify()`-then-archive body)
- `/mnt/c/users/sigit/git/opencode-v2/plugins/fleet-sync/index.ts` (`session.end` subscription, `lastSession` and `inFlight` guards)
- `/mnt/c/users/sigit/git/opencode-v2/plugins/fleet-sync/report.ts:22` (`trigger: "session.end" | "manual" | "dry-run"`)
- `/mnt/c/users/sigit/git/opencode-v2/CONTEXT.md` - "Plugin API limits (OpenCode v2)" section, now on all three hosts
- `node_modules/@opencode/plugin/dist/promise/tool.d.ts:53-61` (`ToolDomain`, no `call`)
- `node_modules/@opencode/plugin/dist/promise/event.d.ts:2-3` (`EventDomain`, no `emit`)
- `/home/sigit/.opencode/plan/active/TASK-ssh-unification-across-fleet.md` (the next task)
- `~/.config/opencode/plugins/opencode-task-plugin/dist/index.js` (all three hosts)
- Prior art: `2026-09-30-opencode-task-plugin-part-1.md`, `2026-09-24-manage-tasks-to-opencode-task-manager-plugin-part-{1,2,3}.md`

Generated with Big Pickle by OpenCode
