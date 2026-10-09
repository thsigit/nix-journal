---
nav:
  series: "OpenCode Task Plugin"
  part: 3
  prev:
    title: "The Rename, the Compile Error, and Why Two Birds Need Two Stones"
    slug: 2026-10-01-rename-compile-error-why-two-birds-need-two-stones
---

# The Instruction That Got Quoted (or: Preparing the Task Plugin to Go Public)

**Date:** 2026-10-09  
**Author:** Codebot  
**Topic:** opencode, task-plugin, handoff, instructions, naming, npm, github, release

---

## 1. Objective (or: A Five-Second Fix and a Much Longer Conversation)

Part 2 ended with the plugin happily named, `close_task` live, and a REST-ful
future ahead of it. This part is quieter on the surface and does two unrelated
things:

1. Fix a single sentence inside the `tasks` tool - a pointer that told the agent
   what to do, was quoted back to the user as if it were a pleasantry, and never
   got obeyed.
2. Audit the plugin for a public release (npm + GitHub) and settle its name -
   which turns out to be the same naming question Part 2 declared closed.

Nothing was published, renamed, or deleted. This is the session where the
instruction learned to give orders and the plugin learned what it would have to
fix before strangers see it.

## 2. Background (or: The Tool That Will Not Let You Start Cold)

The plugin owns `~/.opencode/plan/`: `active/TASK-*.md`, an `archive/`, a
canonical `session-index.json`, and a `session-handoff.md` that records what the
last session established. Four tools wrap it - `tasks` (list), `task_new`,
`verify`, `close_task` (archive).

The vocabulary has been layered since the V1 era, and it is worth restating
because it drove the decision in section 4.5:

| Altitude | Name | What it is |
|---|---|---|
| Store | `plan` | the one directory, `~/.opencode/plan` |
| Unit | `task` | a `TASK-*.md` file |
| State | `todos` | the checkboxes inside a task |

So: plan -> task -> todos. The path says `plan`, the files say `TASK-`, and the
tools say `task`. That is not drift; it is two altitudes of the same idea.

The `tasks` tool is special because it is the first thing a fresh session
reaches for, and a bare list of files is dangerous - a task list without context
reads as "this is all you need to know", which is how three stale copies of the
handoff once survived three syncs while the tool reported a healthy list. So
`tasks` prints a bounded excerpt of `session-handoff.md` ahead of the list, plus
a pointer to the full file. That pointer is the sentence this session fixed.

## 3. Problem (or: The Instruction Read Aloud Instead of Followed)

A fresh session ran `tasks`. The output ended with:

```text
## Session Handoff (read this before the task list)

**Date:** 2026-10-09 (from file mtime; no **Date:** line in the handoff)

...

Full narrative: /home/sigit/.opencode/plan/session-handoff.md - read it before
acting on the tasks below; it records what the last session established,
including corrections to earlier claims.
```

The agent then did the one thing the sentence did not want: it relayed the
sentence. "Read session-handoff.md before acting on tasks" appeared in the reply
as advice, and the task list was presented - without the file ever being opened.
The user noticed before the damage did:

> You said `Read .../session-handoff.md before acting on tasks` but you didn't
> read it for me.

The user's second point was sharper still: the line was treated as prose. It
looked like narration, it sat inside a block of narration, and it was addressed
to no one in particular. So it was quoted. Which is a different failure from
being ignored - the reader engaged with the text and still did not act on it.

The second thread of the session is the plugin itself. It works, it is not
polished, and its author wants it public via GitHub plus npm. What follows in
section 4.3 is what "not polished" means when you actually look.

## 4. Work Performed (or: Orders Instead of Description)

### 4.1 Rewrite the pointer as an imperative

The fix was three edits in `task-manager.ts`, all of them wording. The header
became an order with an addressee:

```text
- ## Session Handoff (read this before the task list)
+ ## Session Handoff - AGENT ACTION REQUIRED: read the handoff file (path below)
+ before you present the task list
```

The pointer stopped describing and started instructing, and it named the failure
mode out loud:

```text
- Full narrative: <path> - read it before acting on the tasks below; it records
- what the last session established, including corrections to earlier claims.
+ Full narrative: <path>
+ AGENT INSTRUCTION (not for the user): before outputting the task list below,
+ use the read tool on that path and act on what it says. It records what the
+ last session established, including corrections to earlier claims. Relaying
+ this pointer to the user instead of reading the file does not comply.
```

Three properties did the work:

- **An addressee.** "Agent instruction (not for the user)" removes the ambiguity
  that made the old line quotable.
- **An order before the list.** The read is demanded *before* the task list is
  shown, matching the output order the tool controls.
- **The anti-pattern named.** Calling out "relaying this pointer does not comply"
  closes exactly the loophole that was used.

The third edit was documentation, in this file's own house style: a paragraph in
the function's WHY comment recording the 2026-10-09 incident, so a future
"cleanup" of that wording knows it is load-bearing. The convention in this
codebase is that every non-obvious choice carries its reason next to it.

### 4.2 Rebuild and verify the artifact, not the exit code

`npm run build` (tsc) exited clean, which - per the lesson this series keeps
re-learning - is not proof. The proof was grepping the compiled output:

```text
dist/task-manager.js:497: "## Session Handoff - AGENT ACTION REQUIRED: ..."
dist/task-manager.js:527: `AGENT INSTRUCTION (not for the user): ...`
```

The new wording is in the file that actually loads. The plugin is loaded at
session start, so the change takes effect next session; inside the same session
the old wording is still in memory.

### 4.3 The publish-readiness audit (or: Five Things Between Here and Public)

A public release means strangers add this plugin to their config. That reframes
every local shortcut as a defect. The audit found five, plus two curiosities:

| # | Finding | Why it blocks public use |
|---|---|---|
| 1 | `package.json` declares `"dependencies": {}` while the lockfile's root records `@opencode/plugin@2.0.16` | Manifest and lock disagree; `npm ci` fails and the package declares no dependency it needs |
| 2 | No `README.md` and no `LICENSE` file (the field says MIT; the file does not exist) | GitHub front page is empty; license is a promise without a document |
| 3 | Bundled skills leak personal infrastructure | `skills/session-close/SKILL.md` names `homelab:/srv/repo/opencode-v2/tasks.git`, `~/.opencode/bin/sync-plan.sh`, and the mem0 store layout; the plugin copies `skills/*` into every installer's global skills dir |
| 4 | The plugin silently runs `git pull`/`commit`/`push origin main` on tool calls | `pullTasks()` is called from `listTasks()`; a stranger's plan dir may not be a git repo, or may have a different remote |
| 5 | Hard-coded store path `~/.opencode/plan` plus the hard-coded sync | Fine for this author, surprising for everyone else |
| *a* | Hub config uses the field `plugin` (singular); V2 docs document `plugins` | It works today; unresolved whether `plugin` is an alias or a legacy key |
| *b* | `~/.config/opencode/opencode.json` loads bare names like `opencode-task-plugin` | Worth documenting the exact install shape so others reproduce it |

Finding 3 is the one with actual blast radius. A plugin that distributes your
ops runbooks - complete with your homelab hostnames - into every user's skills
directory is not a public plugin yet; it is a leak with a plugin attached.

### 4.4 Name availability (or: The Catchy Name Was Taken by a Stranger)

The author's working title was "OpenCode Plan Manager". It is catchy. It is also
taken, twice, by the same person:

| Probe | Result |
|---|---|
| npm `opencode-plan-manager` | TAKEN - v1.1.11, "A plugin for managing plans in OpenCode" |
| GitHub `yurihbm/opencode-plan-manager` | EXISTS - "tools for better plan management by AI agents", since 2026-02-08 |
| npm `opencode-task-plugin` | free (registry 404) |
| npm `opencode-planmanager` | free |
| npm `opencode-plan-manager-plugin` | free |
| GitHub `thsigit/opencode-task-plugin` | free (git protocol check; see section 8 for the method) |

A direct-collision namespace is worse than an ugly name. Sharing an exact name
with a competing plugin means mutual confusion in every search result, issue
tracker, and "which one did you mean" conversation, forever. The interesting
outcome of the check was not the availability table, though; it was the decision.

### 4.5 The decision (or: Part 2 Was Right the First Time)

The author's mental model, restated in the session, decided it:

> I prefer to work on one task file/dir at a time... Thus, we were using
> `~/.opencode/plan` but keep the name `task`. To keep using name `task`, the
> mental model is `plan -> task -> todos`.

That model makes "Plan Manager" the right *outer* name - the product manages the
plan store - while `task` stays the right *tool-level* word. The two are not in
conflict; they are two altitudes. So the resolution is layered, not split:

- **Package/repo/plugin id:** keep `opencode-task-plugin` (no rename).
- **README title:** "OpenCode Plan Manager" - the catchy brand, carried by the
  front page rather than the package name.
- **Tagline / early section:** teach `plan -> task -> todos`, including the
  V1-to-V2 store migration that explains why files say `TASK-` inside a `plan/`
  directory.
- **npm `description` + `keywords`:** carry `plan`, `todos`, `agent` so search
  finds it despite the package id saying only "task".

Part 2 declared the naming closed at `opencode-task-plugin`; this session
proposed re-opening it and then re-closed it, for a better reason. Naming is
done when the cost of changing it exceeds the confusion it removes. With an
exact-phrase collision already on the board, it does.

### 4.6 Accounts and the handle hunt

Publishing needs two logins and one handle:

- `gh` is installed but not authenticated; `npm whoami` returns `ENEEDAUTH`.
  Both logins are interactive and user-only.
- The git identity is `sigit <sigit@localhost>` - an email that maps to no
  GitHub account by name. The handle was recovered by searching GitHub commits
  authored by the git email: **`thsigit`**, 313 commits, repos including
  `nix-journal` and `opencode-google-workspace`.
- The npm username was declared as **`thsigit`**. Its existence is not
  machine-verifiable (the registry user endpoint returns 405; the maintainer
  search shows zero packages, which is what a fresh account looks like). Login
  will settle it.

### 4.7 The plan, written down

All of it went into a task file rather than staying in chat -
`TASK-publish-plan-manager-plugin-to-npm-and-github.md`, sixteen checkboxes over
five phases (accounts, manifest fixes, content, repo+CI, publish+verify), with
the audit findings, the availability table, and the naming rationale recorded.
Two boxes are done (name, handle); the rest wait on a "go".

The only deliberate scope change: the plugin's implicit git sync ships
**gated off**. The code stays, the behaviour is wrapped in an option defaulting
to `false`, and nothing pushes until it is explicitly asked to. Local
consequence accepted and recorded: this author's own instance stops auto-syncing
too, and their explicit `sync-plan.sh` is unaffected.

## 5. Diagnosis (or: Why Prose Gets Quoted)

The wording bug is a small, generalizable finding about instructions embedded in
tool output:

**Text addressed to no one gets relayed, not obeyed.** The old line was
grammatically an instruction and socially a description. It sat in a block of
narration ("Most recent session recorded:", "Full narrative: <path> - it
records..."), so its genre was *summary*, not *command*. A reader - human or
agent - scans for genre first and content second. The fix was not emphasis; it
was changing the genre: name the addressee, state the action, and name the
failure mode.

**The failure is not "ignored", it is "quoted".** An ignored instruction
produces no engagement. Here the agent engaged with the text enough to surface it
- in the wrong channel. That is why the anti-pattern clause matters: telling the
reader that relaying is not complying removes the satisfying-but-wrong action.

**A tool that prints instructions owns their wording.** `tasks` could instead
just read the handoff itself, but the design deliberately does not (a handoff can
run to tens of KB and `tasks` is called often). Given the choice, the excerpt has
to be an order, because it is the only part of the file the agent sees by
default.

This is the same shape as a lesson this series already carries - verify the
artifact, not the exit code - one level up. There, a clean exit did not mean the
job ran. Here, a present instruction did not mean it was followed. Both are
cases of "the observable said one thing, the intent was another."

## 6. Preliminary Assessment

The instrument is fixed and verified in the compiled artifact; it will take
effect next session. The publish project is fully planned, partially unblocked
(name and handle resolved), and deliberately not started. Nothing was published,
renamed, or deleted.

The audit is the more valuable output. It converts "this plugin works" into a
concrete list of what "public" additionally requires: a declared dependency, a
README, a LICENSE file, scrubbed skills, and a sync path that does not fire
implicitly. Four of those are mechanical. The fifth - the skills scrub - is the
one that stops a personal homelab from shipping inside a stranger's config.

One thing this session did not do: re-test the fixed wording by calling `tasks`
again in a fresh process. That is by design (the plugin loads at session start),
and it is the first item of the next session's verification.

## 7. Solution Summary

| Concern | Before | After |
|---|---|---|
| Handoff header | "Session Handoff (read this before the task list)" | "Session Handoff - AGENT ACTION REQUIRED: read the handoff file ... before you present the task list" |
| Handoff pointer | descriptive prose to a generic reader | imperative addressed to the agent, with the failure mode named |
| Why-comment | silent | records the 2026-10-09 quote-instead-of-obey incident |
| Plugin name | `opencode-task-plugin` | `opencode-task-plugin` (proposed "Plan Manager", rejected on collision + vocabulary) |
| Public brand | - | README title "OpenCode Plan Manager", tagline `plan -> task -> todos` |
| Git sync | implicit pull/commit/push on tool calls | to be gated behind `options.sync`, default `false` |
| Release plan | in conversation | `TASK-publish-plan-manager-plugin-to-npm-and-github.md`, 5 phases |
| Published | - | nothing (no npm publish, no repo, no rename) |

## 8. Verification (or: What Was Actually Proven)

| Claim | Evidence |
|---|---|
| The wording change is in the compiled artifact | `dist/task-manager.js:497` and `:527` carry the new strings after `npm run build` |
| The old wording was quotable prose | reproduced in the session: the pointer appeared in an agent reply with the file unopened |
| npm `opencode-plan-manager` is taken | registry returns v1.1.11; description "A plugin for managing plans in OpenCode" |
| GitHub `yurihbm/opencode-plan-manager` exists | commit/search results; unrelated same-named repo by moondrop12138 also appears |
| `thsigit/opencode-task-plugin` is free | `git ls-remote` (auth prompt = absent) with `thsigit/nix-journal` as a positive control; REST API was rate-limited (403) |
| Handle is `thsigit` | GitHub commit search on the git email: 313 commits, `nix-journal`, `opencode-google-workspace` |
| Not logged in to either registry | `gh auth status` = not logged in; `npm whoami` = `ENEEDAUTH` |
| The plugin's dependency graph is inconsistent | `package.json` `dependencies: {}` vs lockfile root `@opencode/plugin@2.0.16` |
| Bundled skills name personal infrastructure | grep of `skills/` for hostnames and personal paths |

Unproven and stated as such: npm username `thsigit` existence (405 on the user
endpoint; zero maintainer packages), and the `plugin`-vs-`plugins` config field
question (it loads today; the reason is unresolved).

## 9. Pending Actions

All publish work is planned and none of it executed. The task file carries the
checklist; in brief:

1. Phase 0: `gh auth login`, `npm login` (interactive, user-only).
2. Phase 2: declare `@opencode/plugin` and regenerate the lock; set version
   `0.1.0`; gate the git sync behind `options.sync` (default `false`); add
   `prepublishOnly: tsc`.
3. Phase 3: README (title "OpenCode Plan Manager", `plan -> task -> todos`
   section), `LICENSE` file, genericize the two bundled skills, `.gitignore`
   (keep `dist/` committed).
4. Phase 4: `git init`, GitHub Action (`npm ci && npm run build`).
5. Phase 5: `npm pack` review, publish `0.1.0`, create `thsigit/opencode-task-plugin`,
   clean-room install test.
6. Next session, first thing: call `tasks` in a fresh process and confirm the new
   wording shows and is obeyed.

## 10. Recommendations (or: Make the Output Give Orders)

**Instructions embedded in tool output must be imperatives with an addressee.**
"The X is at <path>" is documentation. "Read <path> before you show the list;
relaying this line does not comply" is an instruction. If a tool depends on the
reader doing something, write it the second way - genre before emphasis.

**Name the failure mode, not just the goal.** Telling the reader what *not* to do
("relaying this pointer does not comply") closes the specific loophole that an
over-clever reader will find. Goals describe; anti-patterns constrain.

**A collision in the namespace beats a prettier name.** An exact npm + GitHub
match on a competing plugin is a permanent tax on every future search. When the
catchy name is taken by someone doing the same thing, keep the honest name and
spend the charm on the README.

**Layered vocabulary is a feature when it is documented.** `plan/` containing
`TASK-*.md` files with checkbox `todos` looks like three names for one thing
until the README teaches `plan -> task -> todos`. Document the altitudes and the
old path (`~/.opencode/task`) becomes history instead of a mystery.

**Audit for what a stranger's machine will do, not what yours does.** The plugin
worked perfectly here and still had two behaviours - implicit `git push` and
skills that name a private homelab - that only become defects at the moment of
shipping. "Works for me" and "ready for others" are different tests; run the
second one before the name is public.

**Write the plan into the task ledger, not the chat.** Sixteen checkboxes in a
durable file survive the session; a good conversation does not. The audit
findings and the naming rationale are in the same file, so the next session
inherits the reasons, not just the list.

---

**Relevant files / artifacts:**

- `~/.config/opencode/plugins/opencode-task-plugin/task-manager.ts` - `handoffSummary()`: header, pointer, and the 2026-10-09 WHY note
- `~/.config/opencode/plugins/opencode-task-plugin/dist/task-manager.js:497,527` - compiled wording (verified)
- `~/.config/opencode/plugins/opencode-task-plugin/package.json` - dependency drift; `skills/session-close/SKILL.md`, `skills/task-triage/SKILL.md` - personal paths
- `~/.config/opencode/opencode.json:334-338` - the `plugin` (singular) entries
- `/home/sigit/.opencode/plan/active/TASK-publish-plan-manager-plugin-to-npm-and-github.md` - the plan (16 checkboxes, 2 done)
- `https://github.com/yurihbm/opencode-plan-manager` and npm `opencode-plan-manager@1.1.11` - the name collision
- Prior art in this series: `2026-09-30-testing-automated-mechanism-real-task-then-misreading-result.md`, `2026-10-01-rename-compile-error-why-two-birds-need-two-stones.md`

Generated with Big Pickle by OpenCode
