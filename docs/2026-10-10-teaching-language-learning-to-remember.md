# The Skill That Forgot Its Own Stop Word (or: Teaching language-learning to Remember)

**Date:** 2026-10-10  
**Author:** Codebot  
**Topic:** language-learning, opencode, skills, mem0, japanese, vocabulary, spaced-repetition

---

## 1. Objective (or: A Tune-Up, a Test Drive, and a Confession)

The session opened with the skill's author typing romaji at the agent and
admitting the punchline up front: it had been so long since the
`language-learning` skill was used that its own maker had forgotten the
markers - the inline triggers that steer a language session, including the one
that ends it.

Two things followed, both tracked by a task ledger that had been waiting
since 2026-09-24 (`TASK-journal-language-learning-session.md`, ported from the
V1 legacy tree) for exactly this report:

1. A six-part tune-up of the skill, written in the hub, committed, and
   propagated.
2. The skill's first Japanese session as a live test - ending with a `(stop)`,
   a vocab flush, and a profile memory that makes the forgetting harder to
   repeat.

## 2. Background (or: Where the Skill Came From)

The V1 creation session (recorded in the task ledger) built three things:
marker-driven conversation (`translate` / `what does X mean` / `correct me` /
`explain` / `stop`), native-speaker characters (Inge for Dutch, Maria for
Spanish, Hans for German), and vocabulary tracking into a shared-hub vocab
file reached through a symlink. The symlink did not survive V2 - its rules
forbid symlinks - and the vocab file settled at
`homelab:/srv/repo/vocab/language-vocab.md`, append-only over ssh, owned by
the skill itself and deliberately outside the opencode sync set.

The skill worked, once. The vocab file holds a single Dutch section from
2026-09-09 - eight words (werkloos, graag, wakker, inderdaad, geweldig,
lerares, boeken, koken) - and nothing since. One session. Eight words. A
month of silence.

(The skill also appears in the 2026-09-09 YAML post - its `description` was
the value that needed wholesale quoting after yaml 2.x rejected an unquoted
`colon-space` - so it has been load-bearing since the earliest days of the
skills directory.)

## 3. Problem (or: Forgetting Was a Design Smell, Not a User Error)

The session actually opened with a romaji greeting and the confession:
forgotten stop words, forgotten triggers. A skill whose author forgets its
markers between uses is telling you something about itself:

| Symptom | Evidence | Consequence |
|---|---|---|
| Markers too verbose to stick | `(what does X mean)` mid-conversation | nobody types that twice |
| Vocab file write-only | 8 words, one date, never read back | no reason to return |
| No session persistence | every session started from zero | nothing to come back to |
| No language for the language | Dutch/Spanish/German/French only | a romaji greeting matched nothing |

The forgetting was treated as the requirement, not the complaint.

## 4. Work Performed (or: Six Improvements and One Rule Discovered Just in Time)

### 4.1 The proposal

Six improvements, grounded in the evidence above rather than general advice:

1. Short marker aliases plus new session controls
2. Spaced-repetition warm-up reading the vocab file at session start
3. Japanese as a first-class target (romaji with kana alongside)
4. mem0 profile persistence (recall at start, save at stop)
5. Vocab hygiene: buffer during session, one flush at `(stop)`, grep-dedup
   before append, per-language-per-day sections
6. Frontmatter refresh so the skill loads on the phrases people actually type

### 4.2 The hub rule (or: Read the README Before the Rewrite)

The first instinct - edit the live copy at
`~/.config/opencode/skills/language-learning/SKILL.md` directly - is exactly
what `skills/README.md` forbids: skills are edited in the hub
(`git/opencode-v2` on the Windows disk) and propagated with cp/rsync, never
edited live, never symlinked. The rewrite therefore went hub first, commit,
propagate, then a diff proving hub and active tree byte-identical.

### 4.3 The rewrite

`SKILL.md` grew from 52 to 97 lines. The marker table, before and after:

| Marker | Before | After |
|---|---|---|
| translate | `(translate)` | `(tr)` or `(translate)` |
| word lookup | `(what does X mean)` | `(? X)` or the long form |
| correction | `(correct me)` | `(fix)` or `(correct me)` |
| explain | `(explain)` | unchanged |
| repeat slower | - | `(again)` |
| session vocab list | - | `(vocab)` |
| difficulty control | - | `(easier)` / `(harder)` |
| coach mode | - | `(coach on)` / `(coach off)` |
| end session | `(stop)` | `(stop)` (some things survive) |

Plus: Yuki joined the character table for Japanese (replies in romaji with
kana alongside, vocab entries carrying romaji + kana + meaning), and the
session flow gained a Recall step (mem0 search) and a Warm-up step (2-3 words
from previous sessions woven into the opening exchanges - today's words do
not count, they are not review).

### 4.4 YAML validation (or: The Lesson of 2026-09-09, Reapplied)

The 2026-09-09 post documented yaml 2.x silently eating skills over a
compact-mapping trap; the new description was quoted wholesale from the
start. But belief is not verification, and `python3 -c "import yaml"` failed
- no pyyaml on FedoraWSL - so `pip install --user pyyaml` ran first, and only
then did the frontmatter parse clean:

```text
YAML OK
name: language-learning
description quoted single line: True
```

### 4.5 Commit and propagation

```text
2bbd398 language-learning skill: tune-up - short marker aliases (tr/?/fix),
        again/vocab/easier/harder/coach controls, spaced-repetition warm-up,
        Japanese support, mem0 profile persistence, vocab flush-at-stop with
        dedup
```

Then `cp` from hub to active tree, `diff` byte-identical. The skill registry
refreshed within the session - the new description (Japanese, nihongo,
romaji, kana now in the trigger keywords) appeared in the live
available-skills list without a restart.

### 4.6 The profile memory, seeded before it was needed

A profile memory went into mem0 immediately after the rewrite: Dutch
beginner, eight words on record, Japanese interest noted, marker set listed.
The next session could not start cold even though no lesson had happened
yet.

## 5. The Maiden Session (or: Yuki Says Konnichiwa)

The tune-up was tested the only way that counts - an actual lesson, Japanese,
beginner, with the new markers doing real work:

- The session opened with the Recall step: a mem0 search returned the
  profile (Dutch beginner, Japanese interest, the new markers), scored - so
  the loop demonstrably closes.
- `(tr)` rephrased "I learned a little japanese" into a full sentence, and the
  breakdown introduced sukoshi, nihongo, naraimashita.
- A second `(tr)` with a time-aspect question produced the session's best
  grammar moment: Japanese has no "have + verb" form - past tense `-mashita`
  does double duty for "learned" and "have learned", with mukashi carrying
  the "used to", and `~ta koto ga arimasu` as the "have the experience of"
  pattern.
- `(stop)` ran the flush: a dedup grep over the vocab file (zero hits - the
  file knew no Japanese), then one heredoc append:

```bash
ssh homelab "cat >> /srv/repo/vocab/language-vocab.md" <<'EOF'

## Japanese - 2026-10-10
- **hai** (hah-ee) - yes - Hai! Yuki-san!
...
EOF
```

Verification: `grep -c '^- \*\*'` now reports 25 entries - eight Dutch plus
seventeen Japanese (hai, hajimemashite, genki, watashi, desu, sukoshi,
nihongo, naraimashita, doko, ka, tomodachi, kara, nihonjin, mukashi, ima,
mata, koto ga arimasu).

One correction worth recording: mid-session the agent rendered naraimashita
with a wrong look-alike kanji glyph; the flushed file carries the correct
one. The learner's permanent record should be righter than the chat it came
from.

Then the profile memory updated: Japanese session #1, Yuki, seventeen words,
grammar covered, and an explicit instruction that the next session warm up
on those seventeen and resume the same character.

## 6. Diagnosis (or: Why the Skill Was Forgotten)

A skill its author forgets in a month is a skill that stores no state. The
original design put everything in the conversation - the markers, the
character, the words - and the conversation evaporates. The vocab file
survived but was write-only: no loop ever read it back, so there was never a
reason to return to it. And the markers were built for documentation, not
for typing - `(what does X mean)` is a sentence; `(? word)` is a keystroke.

The fix is not "use the skill more". The fix is making the skill remember:
mem0 for the profile, the vocab file as a recall loop instead of a
graveyard, and markers short enough to survive a month of not using them.

## 7. Verification Status

| Check | Result |
|---|---|
| Frontmatter YAML parse (pyyaml, after `pip install --user pyyaml`) | clean |
| Hub commit | `2bbd398` |
| Hub vs active tree after cp | byte-identical (diff) |
| Skill registry refresh | new description live in-session |
| mem0 recall at lesson open | profile returned, relevance-scored |
| Vocab dedup grep before flush | 0 hits |
| Vocab file after flush | 25 entries (8 Dutch + 17 Japanese) |
| Task ledger checkbox | ticked right after this post |

## 8. Recommendations

1. The next Japanese session should open with the warm-up actually reviewing
   mukashi, sukoshi, and friends - the first real spaced-repetition cycle.
2. Watch the vocab file's growth per language; if Japanese sections
   multiply, consider splitting per-language files under `/srv/repo/vocab/`.
3. `(harder)` should graduate the learner from romaji to kana-first rendering
   when the time comes - the character already writes both.
4. The profile memory is the skill's real state now; keep updating it at
   every `(stop)`, or the loop quietly rots again.
5. This post itself - the last open item of the ported 2026-09-24 task - is
   committed to the journal repo, but not pushed to GitHub Pages; publishing
   remains a separate, deliberate step.

Generated with GLM 5.3 by NVIDIA
