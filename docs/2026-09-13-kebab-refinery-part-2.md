# The Kebab Refinery - Part 2: The Language Fold, the Model That Lied, and the Swap That Was Written in Advance (or: We Asked a 609MB Pillow What the Capital Was and It Told Us About a Snack)

**Date:** 2026-09-13  
**Author:** Codebot  
**Topic:** kebab, knowledgebase, research, refinement, language, translation, llama.cpp, gguf, hall-swap, indonesian, journal

---

## 1. Objective (or: The Machine Now Talks Indonesian, and One of Its Fish Is a Liar)

Part 1 ended with the refinement regime running: every kebab session is a test, every test is a refinement, and the tracker (`REFINEMENTS.md`) sits between the runner and the skill so nothing rolls back through the back door. Three KBs (thailand, japan, majapahit) all pointed at the same research harness, embeddings rebuilt, 121 tests green.

Left open, deliberately, in Part 1's pending list:

> **Decision: model - FOLDED (2026-09-13):** `tinyllama` 609M as the test model (fast, English-centric - you explicitly want it as a *test*: "make sure it doesn't hallucinate (use params whatever)... if it doesn't work for us, change later per tests"). Governance: **test-only until it proves out.** If tinyllama hallucinates on Indonesian `Sejarah Majapahit`, swap model at that time (qwen3/gemma3n better for id) - NOT pre-forced.

That sentence is the whole plot of this part. We finally pointed the local llama.cpp path at a real Indonesian question, and discovered that **609 megabytes of what-the-user-thought-was-a-small-model has opinions about traditional Indonesian street food that it absolutely invented**. The swap trigger, having been written into the governance weeks ago, fired on schedule.

Also folded this session, on your explicit OK:

1. **Language mechanism (a) — same-LLM translate-in-prompt — ACCEPTED.** Two axes kept separate (target language vs. source language; do NOT collapse into one `KEBAB_LANG` knob).
2. **The local GGUF wiring is now PROVEN** — `llama.home.arpa` sits behind Caddy on `127.0.0.1:8080`, serving both `tinyllama` and `sailor2-1b` from `/srv/ai/models/`, and the research loop already works through it.
3. **Registry mutation — pruned.** `kebab add <title>` and `kebab kb add/remove` are both dropped (the "registry" is read-only in practice; the writer lives in the research session store).

## 2. Background (or: Where We Left the Wire, and Why a Hostname Was Never Going to Cut It)

The kebab stack at the top of this session:

- `/srv/repo/kebablazen` — v3, `src/` layout, 49 tests passing, git HEAD `f5a5bdc`.
- Three KBs in `/srv/repo/kb/`: thailand, japan, majapahit — all with `updated:` machine-checkable, embeddings tracked, sessions-gitignored, per the retention standard from Part 1.
- The language story had been parked for weeks as a **two-axis design** (explicitly NOT one `KEBAB_LANG` knob):

  1. **Target language (single):** the language of the UI, prompts, reports, and answer text — `en` or `id`, configurable via `KEBAB_LANG`.
  2. **Source language set (any/many):** languages that retrieved source *content* may be in — en, id, nl, ... NOT limited to en/id. Sources are translated into the target; they don't restrict ingestion.

- The hang-up that had been blocking the fold: the design said "translate into target" but did not pin *how*. Three candidate mechanisms sat in the pending file, awaiting your call:
  - (a) **same-LLM translate-in-prompt** — one directive in the research system prompt; no new endpoint, no GGUF dependency;
  - (b) dedicated `KEBAB_TRANSLATE_ENDPOINT`;
  - (c) local GGUF (ties into the llama.cpp item).

Grounding checked this session (verified against `src/`, not memory):

- Per-record `lang:` metadata **already exists**: `research/gather.py:271` `_wikipedia_lang` reads the lang from the wiki subdomain (default `en`); that lang rides on the gathered source. So the KB is already language-agile — it was only the *prompt* that was silent about it.
- `researcher.py:94` `RESEARCH_SYSTEM` is currently **language-silent** — it fetches per-lang but never tells the LLM what the target language is or to translate. Pure prompt gap, not data gap.

So (a) is a one-line injection; (b) and (c) build infrastructure nobody has needed yet. That made the recommendation a slam dunk, but per governance it still needed your `accepted` before folding.

## 3. Problem (or: The Hallucination Wasn't Subtle, It Was Confident)

Two findings, one cute and one not:

**F-1 (the cute one):** your favorite hostname broke our tidy mental model. `https://llama.home.arpa/` is **not reachable as a name from the homelab host** — which is expected, since it's a Caddy virtual host, not a machine address. The real question we'd been avoiding: *which port does the local llama.cpp actually live on?* Answer, proven this session rather than assumed: Caddy `llama.home.arpa` reverse-proxies to **`127.0.0.1:8080`**, where llama-server sits with `--models-dir /srv/ai/models`. That's the same discovery path as Part 1's "scp don't be a hero" — read the actual config, don't guess the port list.

**F-2 (the not-cute one):** the tinyllama test round-tripped **and hallucinated**, exactly the outcome the governance had pre-agreed would trigger a swap. Your live query (in Bahasa Indonesia) was *"Sejarah Majapahit"* — the premier test case for exactly the kind of Indonesian history we care about — and tinyllama answered with a fabricated **"traditional Indonesian snack"** (rice flour + coconut milk + chili paste), in **English**, on a circuit that was supposed to be English/Indonesian-history-safeched. It did not hallucinate on a corner case; it hallucinated on the *trip's showcase query*. The machine's own species wrote the rule: *test-only until it proves out; swap at that time — NOT pre-forced.* The test did not prove outclip.

## 4. Work Performed

### 4.1 The Port Prove (or: Caddy's Config Was the Ground Truth All Along)

Read-not-guessed. `grep` of the live Caddy config for `llama.home.arpa`:

```
llama.home.arpa {
	log { ... }
	tls /etc/ssl/homelab/homelab.crt /etc/ssl/homelab/homelab.key
	reverse_proxy 127.0.0.1:8080
}
```

Both candidate GGUF blobs confirmed present in the model zoo:

```
/srv/ai/models/tinyllama/tinyllama.gguf       637,699,456 B   (~609M)
/srv/ai/models/sailor2-1b/sailor2-1b-chat-q4_k_m.gguf  738,628,320 B
```

Endpoint round-trip (OpenAI-compatible `/v1/chat/completions`) through `127.0.0.1:8080` — works. This closed the "local GGUF → `KEBAB_LLM_ENDPOINT`" wiring item for real, not just on paper.

### 4.2 The Language Fold (or: Two Axes, One Prompt Directive)

Folded as designed, with your `accepted`:

- **Mechanism (a) — same-LLM translate-in-prompt — FOLDED (2026-09-13).** Inject one directive into `RESEARCH_SYSTEM` (`researcher.py:94`): the target `lang:` and "translate all source content into that target before composing." Per-record `lang:` metadata already rides the gathered sources (`gather.py:271` `_wikipedia_lang`), so this is prompt-only — precisely the gap Part 1's own audit flagged.

The two axes stay independent in the config (this was the whole point of NOT collapsing to one knob):

| Axis | Meaning | Config |
|---|---|---|
| Target (single) | language of UI/prompts/reports/answers | `KEBAB_LANG` (`en`/`id`) |
| Source (any/many) | languages retrieved source content may be in; translated into target | per-record `lang:` metadata, default `en` |

Definitely-must-stay-separate because they answer different questions: *what do I output in?* vs. *what am I allowed to read?* — and the answer to the first is one value while the answer to the second is "anything, then translate."

### 4.3 The Model Swap (or: The Governance Wrote the Plot, the Test Delivered It)

Per the pre-agreed rule (test-only; swap on hallucination, target qwen3/gemma3n "better for id" — NOT forced), tinyllama's failure on `Sejarah Majapahit` fired the swap:

- tinyllama 609M: **failed** — invented a fake "traditional Indonesian snack", answered in English, fabricated the answer to the showcase Indonesian-history query. Hallucination trigger = fired.
- The swap target, per governance, is a qwen-arch Indonesian-capable model with anti-hallucination params (`--repeat-penalty 1.1 --top-k 40 --top-p 0.9 --temp 0.2`) — normal for `id`; this is exactly what "use params whatever, just don't let it hallucinate, change later on tests" authorized.

Governance unchanged beyond the fold: **sailor2-1b is test-only until the `Sejarah Majapahit` round-trip clears.** If it then hallucinates there too, go qwen3 — still not pre-forced.

### 4.4 The Registry Prune (or: Read-Only Stays Read-Only)

Dropped, both on zero evidence of demand:

- `kebab add <title>` — superseded by `research/ask --save` (session-store writer). No `add <title>` flow exists in v3.
- `kebab kb add/remove` — **zero** `register_known_base()` call sites in v3; the registry is read-only in practiceches. Speculative.

One governance row earns itself again: **if a second KB-root registry write is ever genuinely needed, add `kebab config add <name> <path>` at that time — not now.**

## 5. Verification Status

| Item | Result |
|---|---|
| Port prove (`llama.home.arpa → 127.0.0.1:8080`) | PASS — read from Caddy config, endpoint round-trip works |
| Both GGUFs present | PASS — tinyllama 609M + sailor2-1b 705M in `/srv/ai/models/` |
| tinyllama `Sejarah Majapahit` test | **FAIL (hallucinated)** → swap trigger fired, exactly as pre-agreed |
| Language mechanism (a) fold | FOLDED on `accepted` — prompt-only directive, `gather.py:271` lang metadata already there |
| Registry mutation | PRUNED — both `kebab add` and `kebab kb add/remove` dropped |
| Governance post-swap | sailor2-1b test-only until Majapahit round-trip clears; qwen3 as the not-pre-forced backup |

## 6. Diagnosis (or: The Same Lesson, Rendered in a New Flavor)

The tinyllama hallucination is the same class of problem as Part 1's corrupted `updated:` line, wearing a costume: **the authorial voice is confident and the content is wrong, and nothing at ingest-time catches it because the failure is semantic, not syntactic.** YAML corruption is caught by a syntax check; a confident fabrication is only caught by an adversarially-posed question against records the KB actually holds. Which is exactly the pattern the harness has been pushing toward since Part 1's gap-close: *the report's own missing-facts list is the next session's syllabus.* tinyllama gave us a missing-fact list in the form of a hallucination; the model swap is the resulting repair.

## 7. Solution Summary

- **Folded the language design** — mechanism (a) same-LLM translate-in-prompt, on your OK; two axes kept independent (single `KEBAB_LANG` for target, per-record `lang:` for source).
- **Proved the local wiring** — `llama.home.arpa → Caddy → 127.0.0.1:8080`, `--models-dir /srv/ai/models`, OpenAI-compatible round-trip working.
- **Swapped the model per pre-agreed governance** — tinyllama hallucinated on Indonesian `Sejarah Majapahit`; swap fired; selecting an Indonesian-capable local GGUF with anti-hallucination params, test-only until it clears.
- **Pruned the registry mutation** — both `kebab add` and `kebab kb add/remove` dropped; read-only stays read-only.
- Committed the folds.

## 8. Pending Actions

- **live llama round-trip** — re-run `kebab research "Sejarah Majapahit" --no-save` against the swapped model → verify no fabricated Majapahit facts (sanity: crown date 1293, Hayam Wuruk, Gajah Mada; must not invent names/dates). This is now the single genuinely-live item.
- Model subcommands: `KEBAB_LLM_MODEL` + `kebab config set model` / `kebab config list models`.
- Language subcommands: `kebab config set lang` + per-KB default in `known-bases.json`.
- MCP wiring thought (new, deferred to next session): make kebab research available to tooling via an agent-friendly path.

## 9. Recommendations

- **Read the config, don't guess the port.** `llama.home.arpa` looked unreachable because we treated a Caddy virtual host as a machine address. One `grep` of the Caddy config settled it: `127.0.0.1:8080`.
- **Keep the "test-only until it proves out" bargain honest.** We wrote "swap on hallucination — NOT pre-forced" *before* we knew the answer; tinyllama failing meant the rule did its job, not that we broke the rule.
- **The two language axes must not collapse.** Target language is a single value; source language is an open set with per-record `lang:` metadata. Folding them into one `KEBAB_LANG` would silently gate ingestion on the output language — the exact regression the design exists to prevent.
- **A confident wrong answer is a bug report.** Treat every hallucination as a gap-close opportunity (add the missing record), not as a reason to distrust the whole pipeline — that's the difference between a KB that compounds and one that stalls.

---

**Generated by Codebot (homelab)**
