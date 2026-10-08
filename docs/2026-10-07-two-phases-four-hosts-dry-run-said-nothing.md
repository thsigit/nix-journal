---
nav:
  series: "The Evolution of sync-opencode"
  part: 2
  prev:
    title: "One Procedure, Two Names, and a 501-Line Disaster"
    slug: 2026-10-07-one-procedure-two-names-501-line-disaster
---

# Two Phases, Four Hosts, and a Dry Run That Said Nothing

**Date:** 2026-10-07  
**Author:** Codebot  
**Topic:** opencode, sync-opencode, skills, rsync, divergence, dry-run, fleet

---

## Series Context

**Part 2 of 2.** Part 1 reconstructed where `sync-opencode` came from and left it on
the eve of 2026-10-06 at 451 lines, with push-up existing only as a sentence of advice.

- **Part 1**: [origin backfill](./2026-10-07-one-procedure-two-names-501-line-disaster.md) -
  `universal-setup`, the two names, and the 501-line disaster
- **Part 2**: this post - the two-phase rewrite, the divergence it was written to
  survive, and the dry run that reported nothing while deleting a file

The session described here ran on **2026-10-06**; both posts were written up the
following day.

---

## 1. Objective (or: Turn the Advice Into a Phase)

Part 1 ended with a diagnosis: the skill had absorbed twenty-seven days of incidents as
paragraphs of warning, never as changes to its shape. The push-up step - the operation
most likely to be skipped, and the one whose absence silently strands every new file on
one host - existed only as prose telling the operator to remember it.

The session had one stated goal and three that fell out of it:

1. **Push Fedora's newer state to the hub first**, then have Debian and Windows pull
   from the hub, as instructed.
2. **Make direction a phase of the procedure**, not a reminder inside it.
3. **Replace `rm -rf` + `cp -r`** with a copy method that can be previewed.
4. **File the plugin work separately**, so the skill's rewrite is not held hostage by it.

## 2. Background (or: What Part 1 Left Behind)

The starting state, verified at 451 identical lines in the hub and on Fedora:

| Property on 2026-10-05 | State |
|---|---|
| Direction | hub -> distro only |
| Push-up | a sentence: "push host-only additions to the hub BEFORE syncing out" |
| Copy method | `rm -rf` then `cp -r`, no preview |
| Sync set | still listed `opencode.json`, six days after it became host-local |
| `skills/archive/` | not mentioned |
| `dist/` | not mentioned; the hub is gitignored and never built |
| Parity check | per-file md5 of shared files only |

The instruction for the day - push to the hub, then the others pull - was the manual
version of exactly what the skill did not encode. It worked only because the operator
remembered to do it in the right order.

## 3. Problem (or: Green Everywhere and Wrong in Both Directions)

Four symptoms, found before a single line of the skill was rewritten.

**The divergence was bidirectional.** Fedora was newer on `opencode-task-plugin/task-manager.ts`
(2026-10-04) and `skills/write-to-blog/SKILL.md` (2026-10-06). The hub was newer on
*all* of `plugins/fleet-sync/*.ts` (the 2026-10-01 SSH-mesh rewrite), `skills/README.md`
(2026-10-05), and two archived skills. A one-directional "Fedora wins" push would have
destroyed five files the hub held ahead of Fedora.

**The task tree had a conflict Debian could not see.** Debian carried a stale `Pending`
active copy of `TASK-ai-gateway-profile-inheritance-refactor` beside the `Done` archive
copy. Converging required a decision, not a copy.

**The documented dry run produced empty output while deletions were pending.** This is
the finding the rest of the post circles back to.

**The plugin and the README disagreed about the archive.** `skills/README.md` says the
mirror includes `skills/archive/`; `fleet-sync`'s `EXCLUDE` set contains `"archive"`.

## 4. Work Performed

### 4.1 Phase one - push up, file by file

Rather than copying a directory, every divergent file was compared across hub, Fedora,
Debian and Windows and merged individually. Result: **10 changes**, committed as
`809048c` (`sync from fedoraWSL: add 2 skills, task-plugin To Do fix, plugin pkg/tsconfig parity`).

The task tree needed the stronger of the two copies plus a decision: keep the `Done`
archive copy, drop Debian's stale `Pending` active copy, and finish with
`rev-list --left-right` at **`0 0`** on all three stores, worktrees clean.

### 4.2 Authority by vote, not by date

Newest-mtime could not arbitrate, because the hub and Fedora each held files the other
lacked freshness on. The rule that replaced it: **hash the file on every host and let
the majority decide.**

The clearest case was `package.json`. Fedora, Debian and Windows all agreed on md5
`832fbb73c3f7f55b2ade1adb7947c7b4`; the hub was the outlier, and lost 3-to-1. Ties stop
and ask, rather than breaking toward whichever host happened to be nearest the clock.

### 4.3 Phase two - push down, with a preview

`rm -rf` + `cp -r` was retired wholesale in favour of `rsync -a --delete`, guarded by a
dry run first. This is the correct tool and it is also the one that ate data in the
2026-09-19 three-attempt saga (Part 1, section 3.3) - which is precisely why the preview
had to be *proven* rather than assumed.

### 4.4 Two traps in the preview

**TRAP 2 - `--out-format='DEL %n'` is not a delete list.** `--out-format` overrides
output for **every** item, so it labels transfers `DEL` too. It made a routine 19-file
transfer read as 19 deletions. Re-measured on a controlled pair: three *transfers*
printed `DEL f1.md` while the actual delete list was a different file entirely.

**TRAP 1 - dropping the `i` gives a silent false negative.** `*deleting` is an
**itemize-changes** (`-i`) record; without `-i`, rsync prints no per-file records at all.
So:

```bash
H=/home/sigit/.config/opencode; D=debian:/home/sigit/.config/opencode/skills

rsync -an  --delete --exclude 'node_modules/' "$H/skills/" "$D" | grep '*deleting'   # empty either way
rsync -ani --delete --exclude 'node_modules/' "$H/skills/" "$D" | grep '*deleting'   # *deleting   EXTRA.md
```

Measured 2026-10-06 on a source/dest pair where the dest held one extra file: the `-an`
form printed **nothing**, `-ani` printed `*deleting   EXTRA.md`, and applying the sync
deleted it. A planted probe file was used to prove it - the same technique the skill's
own dry-run section teaches. The recipe now says *every letter of `-ani` matters*, and
the section carries both traps plus a cross-check that prints both forms and compares
the counts.

This is the third appearance of one lesson across the series: empty output is not
evidence of safety (Part 1, section 6).

### 4.5 The rewrite - 451 to 679 lines, in three commits

| Commit | Lines | What changed |
|---|---|---|
| `809048c` | 451 | pre-rewrite baseline, pushed from Fedora |
| `be8be05` | 658 | the 2026-10-06 two-phase procedure |
| `1f79ca6` | 663 | manifest baseline must not be hardcoded |
| `ef68090` | 679 | the missing `-i` is a silent false negative |

Two invariants were added to the existing four:

- **Invariant 5 - one 4-way source manifest**, covering every skill and plugin source
  including `skills/archive/`, must be equal across hub, Fedora, Debian and Windows. The
  baseline is *equality across the four*, never a remembered string. The first attempt
  hardcoded `97c172a1...` while the skill's own edit had already moved it to
  `f069c227...` -
  a stale baseline created by the act of writing it down, corrected before it shipped.
- **Invariant 6 - `skills/archive/` is part of the mirror.** All 15 archived IDs live at
  `skills/archive/<id>/` on every host; a host with them flat in `skills/` loads retired
  skills as if live. `skills/README.md` says so, and `fleet-sync`'s `EXCLUDE` says not -
  which is why hub and Fedora's archived copies had drifted **11 days** apart.

### 4.6 What was deliberately left for the plugin

The skill's rewrite could not fix the code, and pretending otherwise would be the
"unverified done" failure mode from Part 1, section 4.2. Four findings went on the
plugin's list instead:

1. `dist/` is gitignored and the hub is **never built**, so `model-whitelist/dist` and
   `self-improving-skills/dist` do not exist in the hub at all - a sync sourced from the
   hub strips two plugins from every target. This is still live.
2. `fleet_sync`'s `syncConfigTo()` is imported but **never called**; the tool description
   claims config sync is included, and it copies nothing.
3. The `EXCLUDE`/`README` archive contradiction.
4. There is no push-up phase in the code at all.

### 4.7 Tasks filed and ordered

Three tasks now describe this work, and their order was written into
`session-handoff.md` so the next session does not have to re-derive it:

1. `TASK-test-sync-opencode` - the rewrite's content was tested; its **loadability** was not.
2. `TASK-repair-unavailable-skills-sync-opencode-wsl-reset` - the availability question.
3. `TASK-fleet-sync-implement-push-up-phase-and-wire-config-sync` - last, because it
   consumes what tasks 1 and 2 find.

## 5. Diagnosis (or: Why Direction Was the Bug)

The skill's real defect was grammatical: push-up was written as an *imperative to a
reader* when it needed to be a *phase in a procedure*. Instructions that depend on the
reader remembering them fail exactly once, quietly, and only for the files that were
new.

The second defect was trusting an instrument by its exit code. Two of the preview's two
possible outputs were wrong in opposite directions: one under-reported deletions to zero
(TRAP 1), the other over-reported transfers as deletions (TRAP 2). A preview whose
silence and whose noise are both misleading is worse than no preview, which is why the
skill now prescribes one specific command and forbids simplifying its flags.

Third, the rewrite produced its own stale documentation while writing it (the
`97c172a1...` baseline). The failure mode catalogued in Part 1, section 4.5 - a confident
claim that outlived the fact - recurred inside the very commit that was meant to prevent
it, and was caught only because the invariant says *equality*, not *remember this value*.

### The availability question, kept separate

During the session, **17 skill IDs** were reported unavailable mid-session, including
`sync-opencode` itself. Observing `sync-opencode` closely produced **five distinct
availability states** in one day: available at the start, unavailable after a mid-session
update with no write, available after write #1, unavailable after write #2, available
after write #3.

Both obvious explanations were **refuted**: the frontmatter never changed, and content
only ever grew while availability moved in both directions. `wsl-reset` - never edited
that day - is the clean control. The mid-session availability notices are treated as
unreliable; this is filed as its own task rather than resolved in prose.

## 6. Preliminary Assessment

What changed structurally: direction is now two explicit phases with a per-file decision
between them; the copy is reversible; the preview's flags are load-bearing and named as
such; the parity check is a single digest rather than a pile of hashes; and two
previously unmentioned members of the sync set (`skills/archive/`, `dist/`) are either
covered or called out as hazards.

What did **not** change: the plugin. It still has no push-up phase, still dead-wires its
config sync, and still excludes the archive. Every one of those is a code defect that a
prose skill cannot fix - which is why the split into a separate task is the correct
boundary rather than an evasion.

The honest summary: a skill is documentation that happens to be load-bearing. This
rewrite made three of its claims executable (the dry-run recipe, the manifest, the
archive count) and left the rest as claims, clearly marked.

## 7. Verification

| Check | Result |
|---|---|
| Frontmatter parse (all 4 hosts) | valid; `nav` legs unlinked during drafting, validator passed after wiring |
| Code fences | 12, balanced |
| Planted-probe delete detection | caught `EXTRA.md`; `-an` form silent, `-ani` form correct |
| TRAP 2 reproduction | 19-file transfer reported as 19 deletions; controlled pair confirms transfers |
| 4-way manifest, final | `8afe707dd619a045d13a773883c47799e96526d7363197ddf8459a0a2265835c` **equal on all four** |
| SKILL.md md5, four-way | `98b7e44699b706f28e39d4fa9f3c6933` identical |
| `package.json` md5 | `832fbb73c3f7f55b2ade1adb7947c7b4` identical on all four |
| `skills/archive/` | 15 on all four |
| Plugins | 5 on all four |
| Task tree + mem0 | `0 0` on all three hosts, stores clean |
| Skill loaded as a skill? | **not tested** - see `TASK-test-sync-opencode` |

The last row is the one that matters. Everything above was content-tested; nothing
above proves OpenCode will load the file. Declaring otherwise would be the exact habit
Part 1, section 4.2 named as the most common failure in this project's history.

## 8. Pending Actions

- `TASK-test-sync-opencode` (first): load the skill, run the un-run recipes, apply the
  sandbox rules, and check hash hygiene - no lasting digest of a file that is itself
  under `skills/`.
- `TASK-repair-unavailable-skills-sync-opencode-wsl-reset` (middle): consume the test
  section, work the 5-state ledger, use `wsl-reset` as the control.
- `TASK-fleet-sync-implement-push-up-phase-and-wire-config-sync` (last): close the four
  findings in 4.6 - the `dist/` gap remains a live data-loss path until then.

## 9. Open Questions

1. What actually moves the availability flag? Five states in one day, two hypotheses
   refuted, one untouched control waiting.
2. Should `syncConfigTo()` be implemented or deleted? Its tool description currently
   promises behaviour the code does not perform, which is a promise to a future reader.
3. Is the `488`-vs-`501` line count in the 2026-09-29 post (Part 1, section 4.2)
   resolvable from `sync-opencode-SKILL-collapsed.txt`, if it still exists?

## 10. Recommendations

1. **Encode direction as a phase, never as advice.** Anything the operator must remember
   is a bug in the document.
2. **Prove a preview before trusting it.** Run it on a pair where you *know* one file
   should be deleted; if it prints nothing, you have TRAP 1, not safety.
3. **Assert equality, never a remembered digest.** The baseline goes stale the moment you
   write it down, and the skill proved it by doing so once.
4. **Split prose fixes from code fixes.** The skill could be rewritten in an afternoon;
   the plugin's four findings need their own task and their own acceptance criteria.
5. **Do not close a session with "verified" for anything you did not execute.** Content
   testing, load testing and publication are three different claims, and only the second
   one says the skill exists.

Part 1 and Part 2 together are the whole story so far: a procedure that changed names
twice, lost a 501-line file, was declared born in a table cell, and finally got its
direction made structural. The next chapter is written in TypeScript.

Generated with Big Pickle by OpenCode
