# The Kebab Chronicles - Part 4: Fifteen Seasons of Japanese History (or: The Researcher Isn't Slow, He's Just Moody)

**Date:** 2026-09-13  
**Author:** Codebot  
**Topic:** kebab, knowledgebase, research, japan, nederland, skills, commands, litellm, timeout, embeddings

---

## 1. Objective (or: One Report Is Nice, How About Eighty-Six Records?)

Part 3 gave kebab a first-class `report` record, an `ingest` command, a `recall` command, and a real embedding path through the LiteLLM proxy - and then proved it all on a single Majapahit report. The natural next question was: what happens when we stop feeding the machine one report at a time and instead ask it to chew through an entire field of history, session by session, until the KB is full of *structured records* instead of prose?

This session is that question, answered at volume:

- A **Japan history KB** built from 15 research sessions - 86 records spanning periods, events, people, places, and organizations - and a stretch where the ancient Jomon era refused to be summarized for roughly an hour.
- A **kebab-kb skill** on the shared hub (the orchestrating kind that *invokes* `general-research` rather than fighting it), plus a harness script that turns "run a period" into one repeatable call.
- A **fine-tuning second run** (Netherlands, 9 sessions, economic history included) to find the skill's rough edges the first run smoothed over.
- A **deepen pass** that turned `kebab diff` warnings into cross-links - and measurably improved semantic recall.
- A **`/kebab` command** so that all of the above has an explicit front door, not just a skills-description prayer.

## 2. Background (or: What Part 3 Left Behind)

Entering this session, the kebab stack was as Part 3 left it:

- `/srv/repo/kebablazen` - the v3 core, webapp stripped, **121 tests green**, featuring `research create/ingest/run/diff/apply` plus the new `ingest` (report) and `recall` (full-text + semantic) commands.
- KB layout `/srv/repo/kb/<domain>/` with the Majapahit corpus migrated in, `report:` type registered, embeddings building 31 chunks via `nvidia/nvidia/llama-nemotron-embed-vl-1b-v2` on the proxy.
- The research pipeline's mid-life crisis: `research investigate` was advertised as "go fetch me evidence," but its default search path (DuckDuckGo and Bing HTML) returned - in the words of the Part 3 post-mortem - junk-heavy results.

What had *not* been tried: running the full `create -> ingest -> run -> diff -> apply` loop many times in sequence, across one whole domain, with real LLM latency in the hot path. That is what Part 4 exists to stress-test.

## 3. Problem (or: The Search Box Was Lying to Us)

Three problems collided before the first period got applied:

1. **`research investigate` was unusable.** Asked for Jomon period sources, it returned the *same Indonesian dictionary page* for every query - "periode". A search box that only knows one word is not a search box. The reliable path turned out to be `research create` plus `research ingest` with curated Wikipedia URLs (Indonesian `Zaman_*` + English `*_period` articles), fetched from the article's own host language.
2. **The Wikipedia language was silently dropped.** `research ingest` rust analog of a classic: feed it `id.wikipedia.org/wiki/Zaman_Jomon` and it fetched from the English Wikipedia, then reported "no article titled..." because the English encyclopedia has no Indonesian title. A one-line language sniff from the URL host fixed it (`gather.py`), and 121 tests stayed green.
3. **The researcher is not slow, the endpoint is moody.** The NVIDIA 120B NIM endpoint has latency that swings from ~55 seconds (for a nearly empty response) to *north of ten minutes* (for a real one). kebab's `OpenAIProvider` enforces a hard urllib socket timeout; when the endpoint dawdled past the 300-second default, the CLI aborted with `Refusing to run: LLM request failed: timed out` and produced **zero claims**. Jomon - 14,000 years of prehistory owed one summary - got this treatment three times in a row.

## 4. Work Performed

### 4.1 Abandoning the Search Box (or: Curated URLs, the Honest Sources)

The pivot: stop asking the internet what to read, and instead point the pipeline at what we already know is worth reading. For each era, two curated URLs - the Indonesian Wikipedia article and the English one. `research create` opens a session, `research ingest` pulls each article into `findings.md` (capped with `--max-chars 8000`, spaced 12 seconds apart because the Wikipedia API rate-limits after about five rapid fetches with HTTP 429 - ask us how we know).

### 4.2 Two Bugs That Wanted to Be Found

Two small, self-inflicted wounds, both fixed in the source and covered by tests:

| Bug | Symptom | Fix |
|---|---|---|
| Ingest ignored the URL's language | `id.wikipedia.org` URL fetched from English WP -> "no article titled ..." | `_wikipedia_lang(url)` in `gather.py`, plumbed into the fetch call |
| Researcher emitted underscore record ids | `jomon_period` instead of `jomon-period` | `_clean_target_id()` slugifies to lowercase-hyphen; system prompt now dares the model to try underscores |

The idealized rendering in prose: sniff the host, slug the id, re-run the suite. All 121 still green.

### 4.3 The Defense Kit (or: 600 Seconds, Three Tries, and a Bracket Pattern)

The Jomon freeze-out produced the day's most reusable knowledge - a defense kit for a moody researcher:

- `KEBAB_LLM_TIMEOUT=600` (and the default raised to match) so a slow-but-valid response stops being an aborted one.
- A 3-attempt retry wrapper around `research run`, gated on `Done: N claims` with `N >= 1`, sleeping 20 seconds between tries.
- `--max-chars 8000` per source so the prompt (and therefore the expected generation wall-time) stays sane.
- A running joke we keep paying for: `pkill -f japan_runner.sh` launched from the same ssh command that also *starts* the runner will match the launcher's own command line and kill the thing it just started. The bracket pattern (`[j]apan_runner.sh`) and keeping orchestration in scripts on the host are the fix. ("Narrator: it was not the researcher's fault, and also not simple.")

With that kit, the anachronistic summary you have all been waiting for: **Jomon, retried detached, finished in ~100 seconds with 7 claims and 7 applied changes.** It was never slow. It was having a long lunch.

### 4.4 Japan: Fifteen Sessions, Eighty-Six Records

A background runner stepped through 15 periods (Jomon through Heisei/Reiwa), each as its own session: create, ingest id+en, run researcher (with the defense kit), diff, apply. The final tally, committed as `8db0222`:

| Type | Records |
|---|---|
| periods | 17 |
| events | 23 |
| entities/people | 22 |
| entities/places | 9 |
| entities/organizations | 15 |
| sources | 2 |

The researcher, left to its own devices, split several sessions into finer-grained canonical periods (14,000 years is a lot of eras) - 15 questions produced 17 canonical `period` records. Embeddings rebuilt: 88 chunks (`88 records including sources`) into `.kebab/vectors.json`.

### 4.5 The Skill Appears (or: It Should Not Take an Hour of Troubleshooting to Repeat This)

Lesson of the day: the Japan run wrapped up in ~45 minutes of wall time, but the *knowledge* behind it (the defense kit, the URL conventions, the pkill gotcha, the NixOS `#!/usr/bin/env bash`, the "hyphens not underscores" rule) deserved a permanent home. Enter the **`kebab-kb` skill** (`v0.3.0`) on the shared hub at `/mnt/c/users/sigit/.config/opencode/skills/kebab-kb/`:

- It **invokes `general-research`** for the scoping + parallel source-gathering/cross-check phases, then diverges into the structured-record pipeline. Not a merger - a hand-off, so the two skills keep clear triggers and general-research's prose-report duty untouched.
- It carries the actual harness as `scripts/kebab_kb_runner.sh` - the single, versioned place where the pipeline gets tweaked (`0.3.0` adds a "Fine-tune log" learned from the second run).
- It was **proven by the second run**: the first time the skill was used standalone, it degraded gracefully from "assume it works" to "this is exactly what the runbook says" - that is the whole point of writing one.

### 4.6 Netherlands: The Fine-Tuning Run (or: En-Dashes Are Fine, People Are Optional)

The second KB, `/srv/repo/kb/sejarah/nederland`, was the skill's first real test - 9 sessions: 8 chronological eras plus one non-chronological **economic history** bonus session (confirmed with the user, who was clearly enjoying this). Findings that made it back into the skill's fine-tune log:

- URLs with en-dashes (`Economic_history_of_the_Netherlands_(1500%E2%80%931815)`) ingest fine. Keep the `%E2%80%93`.
- **9 sessions -> 14 canonical `period` records.** The researcher subdivides; keep article titles consistent so cross-session ids stay canonical.
- **Organization-centric sources yield ~0 `people` records.** Not a bug; expected. (The Netherlands got 14 periods and not a single person - the golden age worked, apparently, in committee.)
- `kebab diff` **warns when a prospective record overlaps an existing one** (`organization:dutch-west-india-company` vs `organization:voc` - "using 'update' may be what you want"). Treat warnings as cross-link candidates, not errors.
- **Zero researcher retries needed** this run. The defense kit is a safety net, not the norm.

Final tally committed as `017486c`: 14 periods, 15 events, 10 places, 14 organizations, 11 sources, 0 people - 64 chunks embedded.

### 4.7 The Deepen Pass (or: Diff Warnings Are Just Relationship Advice)

The skill's step 4 got its first real exercise on Japan: a cross-cutting "hubungan lintas periode" session ingesting the overview articles and applying to existing records - updating `meiji-government`, `tokyo`, `kyoto`, `minamoto-no-yoritomo`, and friends with cross-period relationship claims (KB `v33`). The effect was measurable: semantic recall for "siapa pendiri keshogunan Kamakura" improved from ranking the Tokugawa era near the top to putting `person:minamoto-no-yoritomo` (0.501) squarely first. Cross-links, it turns out, are not decoration. Commit `813dbd1`.

### 4.8 From Skill to `/kebab` (or: Give the Poor Thing a Front Door)

Skills are great when the model decides to load them; commands are better when *you* decide to run them. Discussion (worth having): inline in `opencode.json` vs. file-based under `commands/`. File-based won - `customize-opencode` prefers files for command definitions, they are safe to add (a pure add can not break the config, no backup ceremony needed), and a markdown template is readable in a way a JSON string never is. The hub's 4 existing commands stay inline; opencode merges both sources.

- **`/kebab <topic>`** - hub `commands/kebab.md`, `agent: build`, whose template says, essentially, "load the `kebab-kb` skill and build a knowledge base for: $ARGUMENTS."
- Per-distro symlinks wired (`~/.config/opencode/commands -> hub`), universal-setup skill updated, and `general-research` bumped to `v0.1.1` with a polite note in its description: if you want a persistent *structured KB*, that is kebab-kb's job, not a report's.

## 5. Verification Status

| Check | Result |
|---|---|
| Core suite after `gather.py` + slug fixes | 121 passed |
| Japan, 15 sessions | 86 records + 2 sources; commit `8db0222` |
| Japan embeddings | 88 chunks, `.kebab/vectors.json` |
| Japan deepen pass | KB v33, 9 updates; commit `813dbd1` |
| Netherlands, 9 sessions | 64 records; commit `017486c` (0 people, expected) |
| Netherlands embeddings | 64 chunks |
| Jomon (pathological case) | 3 timeouts -> 600s retry -> 7 claims in ~100s detached |
| Semantic recall Japan (founder query) | `person:minamoto-no-yoritomo` 0.501 (up from Tokugawa-ranked, pre-deepen) |
| Semantic recall Netherlands (VOC query) | `organization:voc` 0.294 + `organization:dutch-west-india-company` 0.217 (sibling cross-link hits) |
| kebab-kb skill + harness | v0.3.0, fine-tune log, used for the Netherlands run |
| `/kebab` command | file-based, `agent: build`, symlinked on both WSL distros |

## 6. Diagnosis (or: How We Nearly Blamed Jomon for a Sunset)

The cheap shot would have been "Jomon is a hard article." It is not. The sequence of evidence:

- Yayoi, the second session, succeeded twice in the same conditions Jomon failed three times.
- The 30B lightning model needed ~55 seconds for a response that consisted of `{}` - a metric of endpoint patience, not content difficulty.
- Jomon, run detached with the 600-second timeout, completed in ~100 seconds with 7 claims.

Conclusion: the upstream NVIDIA NIM endpoint varies wildly in latency (queue depth, load, mood), and a hard client timeout will kill a response that arrives one second past its deadline. The data was never hostile. Fixes are structural, not content-related: keep the timeout patient, retry a few times, shrink the evidence, and never let a single pinky-sized `--max-chars` default stand between you and the Jomon people's pottery.

## 7. Solution Summary

- Pivot from `research investigate` (search-driven, junk-fed) to `research create` + `research ingest` with curated Wikipedia URLs.
- Fix the two pipeline bugs (article language from URL host; hyphen slug canonicalization) with tests.
- Build the defense kit: 600s timeout, 3x retry, `--max-chars 8000`, script-hosted orchestration (and the bracket-pattern pkill habit).
- Encapsulate it all in the `kebab-kb` skill + `kebab_kb_runner.sh` harness, with `general-research` invoked for scoping/sources.
- Proven on a second domain (Netherlands) and hardened by a deepen pass (cross-links from diff warnings) on the first.
- Front door: `/kebab` command (file-based, `agent: build`), symlinked for both WSL distros.

## 8. Pending Actions

- **Restart opencode** for `/kebab`, the `kebab-kb` skill, and the updated `general-research` description to load (config is a session-start snapshot).
- Optional: decide whether `organization:dutch-west-india-company` and `organization:voc` should be truly linked (currently both exist and both surface in semantic recall - defensible, but a named relationship would be cleaner).
- Optional: a third-source pass on the thinnest Netherlands sessions (the economic-history one got two sources, the skill recommends three where coverage is thin).
- Nothing in the KBs themselves: both are committed, embedded, recall-verified.

## 9. Recommendations

- **Write the runbook before the second run.** The Japan session's pain became the Netherlands session's smoothness precisely because the skill existed before the second theme was chosen. Order matters.
- **Keep the harness as the single place to tune.** Every latency or quality tweak lives in `scripts/kebab_kb_runner.sh`; the skill text only references it. No drift, one diff.
- **Let the researcher over-split.** 9 sessions becoming 14 canonical periods is a feature - finer-grained records make semantic recall sharper, and canonical ids keep it from fragmenting.
- **Diff warnings are free code review.** "This overlaps existing X - maybe update instead" is the pipeline pointing at genuine cross-links. The deepen pass exists to turn those warnings into relationships.
- **A moody endpoint is not a bug.** Give it patience, give it retries, shrink what you feed it, and it will do fine - right up until the next memo-QoS surprise. The kit is architecture, not luck.

---

Generated by Big Pickle (OpenCode)