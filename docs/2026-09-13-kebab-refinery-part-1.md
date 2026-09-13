# The Kebab Refinery - Part 1: When Every Session Is a Test (or: We Broke Twenty-One Records With a Heredoc and Built a Refinement Regime)

**Date:** 2026-09-13  
**Author:** Codebot  
**Topic:** kebab, knowledgebase, research, refinement, thailand, japan, majapahit, runner, sanity, git, tracker

---

## 1. Objective (or: The Machine Works, Now Let's Keep It Honest)

The Kebab Chronicles ended with a working v3: three knowledge bases (Japan, Netherlands, and a freshly built Thailand), a `/kebab` command, a skill with a harness, and 121 green tests. The natural next step, in the proud tradition of people who just got something working: start breaking it on purpose.

The deal we made ourselves: **every kebab session is now a test, and the goal of a test is refinement.** Each run either passes (and gets logged) or surfaces something worth fixing - and the fix itself has to survive a lifecycle (`proposed -> open -> implemented -> verified -> rule`) before it counts as a rule. This part documents the first harvest of that deal, which turned out to be a doozy:

- A **real data-corruption bug** - 21 records with literal Python garbage baked into their `updated:` lines, already committed to git. Because of course it was already committed.
- The **KB-grounded analysis pattern** - pull knowledge out of the KB with citations to record ids, cross-check every critical claim twice, admit loudly what the KB does not cover, and feed the resulting report back into the KB.
- A **gap-close pattern** - the report's "not in KB" list becomes the next session's syllabus.
- The **refinement tracker** (`REFINEMENTS.md`) and the **post-apply sanity check** built into the harness so the bug that bit us once cannot roll back in through the back door.
- Two unrelated source files in `/srv/repo/kebablazen` that had been sitting dirty since the Japan run, doing all the right things.

## 2. Background (or: What Part 4 Left Behind)

Entering this session, the kebab stack was:

- `/srv/repo/kebablazen`, v3 core, 121 tests green; KB data in `/srv/repo/kb/sejarah/`.
- Japan (86 records, deepen pass at `813dbd1`, v33), Netherlands (64 records, `017486c`), Thailand freshly built - 9 sessions, 80 records (8 periods, 18 events, 18 people, 12 places, 17 orgs, 7 sources), commit `64887f3`.
- The `kebab-kb` skill at `v0.3.0` with `scripts/kebab_kb_runner.sh` - the single place where the pipeline is tuned. The runner already had an **automated link pass**: after `apply`, it parses the session diff and adds cross-type `-kingdom` aliases and `rama-<n>` aliases, idempotently, bumping `updated`.
- The `/kebab` command (file-based, `agent: build`) symlinked on both WSL distros.

What had *not* happened: using the Thailand KB as the *subject* of a report that cites the KB itself, then asking the KB to absorb its own review. That is what this session exists to test.

## 3. Problem (or: The Corruption Was Already Committed)

Before the first report could be drafted, the fact-gathering pass stopped on something ugly. A throwaway script that bumped `updated:` in alias-touched records had been piped through an ssh heredoc - **unquoted**. Bash stripped the quote context around a Python f-string, and the remote side cheerfully wrote this *literal* into 21 record files:

```yaml
updated: + __import__(datetime).date.today().isoformat() + 
```

Valid YAML, wrong in every other way, and already committed at `64887f3`. The KB had been sitting on 21 records whose "last updated" wall was made of Python source. (Narrator: it was the f-string, and it was not subtle.)

Textbook P0: it failed silently, it was already in history, and no test would have caught it because no test read the file back. The whole point of the sanity check in section 4.4 is that this exact letter cannot post again.

## 4. Work Performed

### 4.1 The Repair (or: Scp Don't Be a Hero)

The fix was embarrassingly simple once the mechanism was clear: write the script locally, scp it, run it - never pipe Python source through an unquoted heredoc yet again. A fixer (`fix_kb_updated.py`) walked all 21 files, rewrote only the mangled `updated:` line, and reported:

```
total fixed: 21
```

grep confirmed zero residual `__import__(datetime)` in the KB. Repair commit `c646f1e`, embeddings rebuilt (`e40939c`), recall re-validated: querying "Thonburi Taksin reunified Siam after Burmese destruction" returned `event:founding-thonburi-1767` (0.713), `person:phraya-taksin` (0.633), `organization:thonburi` (0.595). Damage contained.

The lesson went straight into the skill as a rule (R-1) and later into the sanity check: *write/edit scripts via scp; keep heredocs quoted (`<<'PY`).*

### 4.2 The KB-Grounded Analysis (or: Citation Galore, With an Honesty Clause)

New pattern, tested mid-session: write an analytical report whose *every factual sentence* cites the KB record it came from, apply the cross-check rule (critical dates/claims need two or more distinct record ids; single-source claims are tagged), and **flag** anything the KB does not hold as "tidak ada record pendukung" instead of inventing it.

For Thailand the question was "Pengaruh invasi Burma terhadap lanskap politik Thailand, 1569-1782." The report that came out (Indonesian, dated, with a per-claim citation map) was honest enough to include a **Celah cakupan** section listing three real holes: the Toungoo sack of 1569, Naresuan's independence recovery (1590-1605), and the 1688 French expulsion. Then we got to fix them.

### 4.3 The Gap-Close (or: The Report's To-Do List)

Each flagged gap became a session, run through the harness. Two Thailand sessions produced seven fresh records and closed every hole the report had named:

| Session | New records |
|---|---|
| Toungoo/Naresuan | `person:naresuan`, `event:burmese-siamese-war-1568-1569`, `event:siege-of-ayutthaya-1569` |
| 1688 revolution | `person:constantine-phaulkon`, `person:phetracha`, `event:siamese-revolution-1688`, `event:siege-of-bangkok-1688` |

The report then got an **addendum** - same file, a new section - so the audit trail survives: "these gaps were real when flagged; here is the record that closed each one, plus what the new material does to the original findings." The 1688 revolution turned out to matter beyond itself: Ayutthaya attacked by Konbaung in 1765-67 was a court that had shut itself off from Western Europe since 1688. The gap-close is basically a plot twist.

The same pattern ran against the other two KBs (one report each, ingested): japan's *Restorasi Meiji and sentralisasi kekuasaan*, majapahit's *Pendirian 1293 sampai awal kemunduran*. Both flagged gaps too. Japan's (1912-1945/Pacific War) closed with `event:pacific-war`; majapahit's (the decline) closed substantially - 13 changes including `person:raden-gajah` and enriched `event:paregreg`, `fall-majapahit-demak-1527`, `demak-sultanate`, `trowulan`.

### 4.4 The Sanity Check (or: The Machine Finally Reads Its Own Homework)

The runner gained `kebab_kb_sanity_check()`, run automatically after every session's link pass, plus a standalone `--check <ROOT>` mode. It scans every record and report for R-1-class corruption (`__import__(`, malformed `updated:`), asserts `.kebab/vectors.json` exists and is git-tracked, flags deleted-tracked files, and echoes `git + kebab status`. Problems mean a loud `!! SANITY CHECK FAILED` and a non-zero exit; the `DONE` marker still prints, but the exit code tells automation the truth. New KBs (no commits, no vectors yet) degrade to warnings, not failures - first sessions are allowed to build their wings first.

> Note in passing: our first `updated:` regex over-matched every single valid file, because `[[:space:]]*` greedily backtracked and happily matched the legit space before the quote. The corrected pattern is `^updated:[[:space:]]*([^'0-9[:space:]]|$)` - and yes, this is the part where the tool built to catch our own sloppiness immediately caught our own sloppiness. We upgraded it and moved on.

Verified three ways: thailand (`.. sanity ok`, exit 0), a scratch fixture with the exact R-1 corruption (`2 problems`, exit 1), and the same fixture after correcting (`ok`, exit 0).

### 4.5 The Tracker (or: Every Session Is Now a Test)

`REFINEMENTS.md` joined the skill directory as the single source of truth for refinements, with a session ledger and the lifecycle `proposed -> open -> implemented -> verified -> rule`. Priorities: **P0** integrity, **P1** workflow, **P2** polish. Content gaps (missing records) are not refinements - those are data, closed by more sessions, keeping the queue clean. The `SKILL.md` frontmatter got bumped to `0.4.1`, and we forced ourselves to obey the version-in-sync-with-fine-tune-log rule we had already violated once (R-5: the frontmatter said 0.3.0 while the log said 0.4.0. Caught it while writing the tracker. The tool is stronger than the tool.)

Seed entries:

| Entry | Class | Status |
|---|---|---|
| R-1 | ssh-heredoc quote-mangling corrupted 21 records | rule (repair `c646f1e`) |
| R-2 | `recall --semantic` needs the full LLM env | rule |
| R-3 | majapahit retention mismatch (ignored vectors, tracked research/) | closed (`a78628d`) |
| R-4 | runner post-apply sanity check | implemented, verified |
| R-5 | skill version drift | implemented |
| R-6 | single explicit commits in multi-KB loops | open (discipline) |

### 4.6 The Retention Alignment (or: Three KBs, Same House Rules)

Majapahit had wandered: it ignored `.kebab/vectors.json` (so embeddings were not in history) and committed `research/` sessions (which Japan and Thailand deliberately gitignore). Aligned at `a78628d`: every KB now tracks embeddings, ignores `research/` and `__pycache__/` only. One convention, enforced by the sanity check's R-3 probes.

### 4.7 The Handoff and the Two Volunteers (or: Dirty Files That Did the Right Thing)

`KB-HANDOFF.md` in `/srv/repo/kebablazen` was rewritten from the pre-runner era into the present (KB inventory, runner + `--check`, retention policy, refinement regime, operational gotchas) and committed as `a508874`.

While committing the doc, `git status` revealed two files that had been sitting modified since the Japan run, doing exactly the right jobs:

- `src/kebab/research/gather.py` - `_wikipedia_lang()`: id.wikipedia.org URLs finally fetch from Indonesian, not English (the Part 4 story).
- `src/kebab/research/researcher.py` - hyphen slug normalization (`jomon_period` -> `jomon-period`), `KEBAB_LLM_TIMEOUT` env support with default 600.

Both were verified live via the editable install (slug `King Rama I` -> `king-rama-i`; `KEBAB_LLM_TIMEOUT=999` -> timeout 999; Indonesian fetch returning 2478 chars; full-text + semantic recall healthy) and committed as `7d97f91`.

## 5. Verification Status

| Check | Result |
|---|---|
| Corruption repair (thailand) | 21 files fixed; 0 residual `__import__(datetime)`; commit `c646f1e` |
| Embeddings rebuilt | `e40939c` (thailand), recall top-3 correct post-repair |
| Thailand gap-close | +7 records, commit `d1dea51`; all report gaps closed |
| Thailand cross-check + addendum | 18/18 cited records present in v23; commit `b4ee7f4` |
| japan analysis + gap | report ingested `a21f2c5`, `event:pacific-war` `d5d95ad` |
| majapahit analysis + gap | report ingested `802993b`, Paregreg session 13 changes `bb48efc` |
| Retention alignment | majapahit `a78628d`; all KBs track vectors, ignore research/ |
| Runner sanity check | thailand `ok`; corrupt fixture 2 problems exit 1; clean fixture exit 0 |
| kebab research source fixes | slug + timeout + lang-fetch verified live; commit `7d97f91` |
| Handoff doc | rewritten, committed `a508874` |
| Skill / tracker | `v0.4.1`, REFINEMENTS.md, R-1..R-6 logged |

KB inventory at end of session:

| KB | Records | Sessions | Version | Head |
|---|---|---|---|---|
| thailand | 88 | 11 | 23 | `b4ee7f4` |
| japan | 90 | 16 | 35 | `d5d95ad` |
| majapahit | 37 | 9 | 19 | `a78628d` |
| nederland | 64 | 9 | 19 | `017486c` |

## 6. Diagnosis (or: The Regression That Nobody Saw Coming)

The corruption was not a kebab bug - it was an orchestration bug wearing a disguise. The pipeline's writers (`apply`, `ingest`) are validated and tested; nothing anywhere read the record files back through a *frontmatter* lens between apply and commit. So a hand-out-of-band script that wrote valid-but-wrong YAML sailed straight into history. Two structural conclusions:

1. **Out-of-band writers are the risk.** Any change to records that does not go through `kebab apply`/`ingest` deserves the read-back guarantee - hence the sanity check scanning for exactly the corruption letter that shipped.
2. **The KB-grounded report is the free correctness harness.** Citing record ids per sentence forced us to confront, in public, what the KB did not know; the gap list then became deterministic next-session work. Analysis and roadmap in one artifact.

## 7. Solution Summary

- Repaired the 21 corrupted records (scp'd script), rebuilt embeddings, re-verified recall.
- Established the analysis pattern (per-sentence record-id citations, cross-check rule, honest gap flags) and the addendum pattern (same file, retroactive audit trail).
- Closed every flagged gap across three KBs with harness sessions.
- Added the post-apply sanity check + `--check` mode to the runner (R-4), and the refinement tracker (R-1..R-6) to the skill.
- Standardized retention policy across KBs; rewrote the handoff; committed the two volunteer research fixes.
- Skill versioned `0.4.1`, frontmatter forced to agree with the fine-tune log.

## 8. Pending Actions

- R-6 discipline is the only open code-free item; an easy pass: one explicit commit per action, message naming the KB, no chained `--amend` in loops.
- Next real KB session earns the first live ledger row (`L-8`) proving the sanity check fires inside a production run, not just `--check`.
- Optional: a named relationship between `organization:voc` and `organization:dutch-west-india-company` (still two records, still both surface - defensible, would be cleaner as a link).
- Optional thin-session follow-ups: the majapahit 1309-1350 transition and nederland economic-history third source.
- Publishing this series via `/srv/repo/nix-journal/scripts/publish.sh` whenever the mood strikes.

## 9. Recommendations

- **Let the machine read its own homework.** The sanity check cost one hour and caught, within twenty minutes, a bug in itself. Money well spent.
- **Flag gaps in reports, then close them as sessions.** "Not in KB" is a roadmap item, not a reason to fudge the prose. The readers of the report become the itinerary.
- **The addendum beats the rewrite.** Evidence: the 1688-1782 throughline appeared only because the addendum compared old claims against new records instead of papering over the history.
- **One house rule for KBs.** Embeddings tracked, sessions ignored, `updated:` machine-checkable - enforced by the runner, not by prayer.
- **Track refinement, not just output.** A KB is a data store; the *skill* is where the compounding happens. The lifecycle (`proposed -> open -> implemented -> verified -> rule`) keeps every improvement auditable and every rule earned.

---

Generated by Big Pickle (OpenCode)