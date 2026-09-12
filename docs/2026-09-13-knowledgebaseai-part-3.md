# The Kebab Chronicles - Part 3: Un-Archived, Given a Home, and Taught to Answer for Itself (or: We Retired It Last Week, So Naturally We Brought It Back)

**Date:** 2026-09-13  
**Author:** Codebot  
**Topic:** kebab, knowledgebase, research, skills, yaml, litellm, ingest, recall

---

## 1. Objective (or: What Do You Do With a Knowledge Base Nobody Can See?)

The previous entry - *2026-09-12-kebab-webapp-autorun-and-retirement* - closed the kebab web chapter with a staged funeral: services layer frozen in `knowledgebasebuilder-legacy`, webapp archived, Caddy vhosts dropped, systemd units gone, and two open questions left on the table:

1. Does a future kebab revisit want the GUI at all, or is the CLI the honest home for a research pipeline?
2. If it returns, should plan/apply be web-exposed, or is that review workflow better left to git + a terminal?

Less than twenty-four hours later, the answer to both arrived in the form of a different question entirely: *"how do I make my `general-research` skills write into the knowledge base, and how does an agent recall what's already there?"* That reframes everything. No GUI, no web re-run - the research *deliverable* itself (the final report) should land in the KB, and recall should be a CLI command an agent can call. This session is the third act of the kebab saga: unfreeze the core, add a first-class `report` record, wire the skills to it, migrate the live KB into a proper umbrella, and prove the whole loop against the real LiteLLM proxy.

## 2. Background (or: What Part 2 Left Behind)

Part 2 delivered the kebab core: a CLI knowledge base where markdown-in-git is the canonical store, indexes and LLM output are disposable, and a research session produces `findings.md`, `sources.md`, `claims.yaml`, and `changes.yaml` for a human to review with `kebab diff` / `kebab apply`. The web chapter then bolted on a services layer (`kebab/services/`) and a FastAPI API until the whole thing hit the retirement wall over evidence quality on junk-heavy search results.

The state entering this session:

- `knowledgebasebuilder-legacy` - frozen v2 reference (webapp + API still present).
- `kebablazen` - the core library, last touched at services-layer commits (`eebbb34` lineage preserved in git history).
- `/srv/repo/sejarah/majapahit` - a live KB for Majapahit history: 31 records, 8 research sessions, version 17, its own git repo, and a built `.kebab/vectors.json`.
- The research pipeline's *output* was claims + proposed changes. The finished long-form report was never a first-class citizen.

## 3. Problem (or: The Archive Is Not the Answer)

The retirement left a gap disguised as a 'lesson': the research loop proved it could gather, think, and propose changes - but the *final report* (the thing a human actually reads and a knowledge base should preserve) had no home. It lived in `~/Documents/`, unindexed, unreachable by the KB's own search. And the KB itself had no notion of "a report." Records were entities (person/place/organization/event/period) and sources. A finished research deliverable was structurally homeless.

Compounding it: the embedding path - the part that makes semantic recall possible - had never been validated against the live homelab proxy in this incarnation. Phase B's risk check was: does `nvidia/nvidia/llama-nemotron-embed-vl-1b-v2` actually return vectors through `ai.home.arpa`?

## 4. Work Performed

### 4.1 Un-Freezing the Core (or: `git checkout` Is a Time Machine)

The first job was deciding the webapp did not get to hold the core hostage. Strategy: copy `knowledgebasebuilder-legacy` forward to a working repo at `/srv/repo/kebablazen`, then strip the web-only layers out as a single, reviewable commit - preserving full git history (the plan's part-2 commits `eebbb34` and friends remain reachable).

Removed:
- `webapp/` (React frontend).
- `src/kebab/api/` (FastAPI) and its `kebab-api` script entry.
- `tests/test_api.py` (the only web-dependent test).

Kept: `kebab/services/`, `kebab/research/`, `kebab/kb/`, `kebab/storage/`, all CLI commands, all 115 core tests.

That landed the suite back at green as commit `eebbb34` (**"v3: strip webapp + FastAPI api, keep CLI/services core"**). `kebab --help` showed the full command surface again, now including `research` subcommands. The CLI was, as recommended last week, the honest home.

### 4.2 The `report` Record (or: Giving the Deliverable a Room of Its Own)

Design decision: a report is a **first-class record type**, not a claim. One finished research deliverable = one `reports/<slug>.md`, with structured frontmatter and the full prose as the body. This respects the core principle (markdown is canonical) while giving the long-form report a permanent address.

The implementation was small enough to be a single coherent commit, largely because kebab's index/search/vector layers are type-agnostic - they iterate `TARGET_DIRS`:

| Change | File | What it does |
|---|---|---|
| Register `reports/` | `src/kebab/config.py` | `REPORT_DIR = "reports"` added to `TARGET_DIRS` and `REQUIRED_KB_DIRS`; `kebab init` now scaffolds it, and index/search/embed build picks reports up for free |
| Report model | `src/kebab/models/report.py` | `Report` + `SourceRef` pydantic models; `from_frontmatter` fills defaults (`id` from `subject`, category `general`, language `id`, dates today) |
| Ingest service | `src/kebab/services/report_ingest.py` | `ingest_report()`: validate frontmatter (subject required), normalize id, write `reports/<slug>.md`, persist normalized id, git commit, optional vector reindex |
| CLI commands | `src/kebab/cli.py` | `kebab ingest <file>` (validate/write/commit/reindex) and `kebab recall <query> [--semantic]` (full-text by default, top-k chunks semantic) |

Report frontmatter schema (the contract `general-research` now emits):

```yaml
---
subject: Arsitektur Majapahit
category: sejarah
tags: [arsitektur, candi, trowulan]
language: id
sources:
  - url: https://id.wikipedia.org/wiki/Arsitektur_Majapahit
    title: Arsitektur Majapahit - Wikipedia
created: 2026-09-13
---
```

Six new tests (`tests/test_report_ingest.py`) cover frontmatter normalization, defaults, source parsing, write path, missing-subject rejection, and same-slug overwrite. One early bug fixed mid-suite: `from_frontmatter` needed to default `id` from `subject` and `category` from `general`; the two throwaway failures are why the suite insists on being run before committing.

**121 tests passing**, committed as `3a268fc` (**"feat: report record type with ingest and recall commands"**).

### 4.3 De-Risking the Embeddings (or: Does the Proxy Actually Vectorize?)

Never assume. Before building recall-on-embeddings, the homelab proxy was probed directly:

```bash
curl -s -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" http://localhost:4000/v1/embeddings \
  -d '{"model":"nvidia/nvidia/llama-nemotron-embed-vl-1b-v2","input":"test embedding"}'
```

Response: `{"data":[{"embedding":[-0.0178, ...]}]}` - a real vector. The model is registered in LiteLLM, and the OpenAI-compatible `/v1/embeddings` path works. `kebab build` reuses that to write `.kebab/vectors.json`; `kebab recall --semantic` reads it. Risk retired early instead of when the skill first ran.

### 4.4 Rewiring the Skills (or: Agents Learn to Write Into the KB)

Two skills changed on the shared hub (`/mnt/c/users/sigit/.config/opencode/skills/`):

- **`general-research`**: now requires kebab-compatible frontmatter on every report and ends with a KB ingest step - scp the finished `.md` to `homelab`, then `ssh homelab 'kebab ingest <file>'` into `/srv/repo/kb/<category>/`. The report is no longer a file that dies in `~/Documents`; it has an address in the corpus.
- **`kb-recall`** (new): an agent-facing recall workflow - identify the domain (`/srv/repo/kb/<domain>/`), run `kebab recall "<query>"` (full-text default, `--semantic` when keywords miss), read the stored report, cite `report:<slug>` + path. Empty result means "not in the KB yet," not "unknown."

Skill frontmatter is written in YAML 2.x, which bite twice in one session:

| Trap | Symptom |
|---|---|
| Unquoted flow tokens in `argument-hint` | `Nested mappings are not allowed in compact mappings` - `<subject> [scope: broad|narrow] [...]` needs full quotes |
| Unquoted colon+space inside `description` | BLOCK_AS_IMPLICIT_KEY parse failure - quote the whole description value |

Rule learned (and it will recur): **quote every multiline description and every value containing `: `, `[`, or `{`** in skill frontmatter. Both skills now parse clean under `yaml` 2.9.0.

### 4.5 The Migration (or: One Umbrella to Rule Them All)

The KB gets a proper home: `/srv/repo/kb/<domain>/`. The live Majapahit corpus (`/srv/repo/sejarah/majapahit`, self-contained git repo) moved in whole:

```
/srv/repo/kb/sejarah/majapahit/
    kb.yaml, entities/, events/, periods/, sources/, research/
    reports/arsitektur-majapahit.md   (new)
```

- Old `/srv/repo/sejarah` deleted after verification.
- Two untracked research sessions (`candi-sukuh-dan-candi-ceta` and `-2`) folded in as commit `8beab1b`.
- Vector index rebuilt: **31 records, 31 chunks** embedded via the proxy.
- Live ingest + recall round-trip proved the whole path - see Verification.

## 5. Verification Status

| Check | Result |
|---|---|
| Core suite after v3 strip | 115 passed (pre-existing, green) |
| + report model/ingest/recall | 121 passed (6 new) |
| Embeddings through LiteLLM proxy | `/v1/embeddings` returns vector, model registered |
| `kebab build` on migrated KB | 31 records / 31 chunks -> `.kebab/vectors.json` |
| `kebab ingest arsitektur-majapahit.md` | `report:arsitektur-majapahit`, git committed `838345c` |
| `kebab recall "punden berundak"` (full-text) | top hit `report:arsitektur-majapahit` |
| `kebab recall "gedung candi lawas jawa"` (semantic) | top hits `report:arsitektur-majapahit` (0.434) + `place:candi-bajang-ratu` (0.284) |
| Skill frontmatter under yaml 2.9.0 | both `general-research` and `kb-recall` parse clean |
| /srv/repo/sejarah | gone; KB lives at `/srv/repo/kb/sejarah/majapahit` |

Semantic recall incidentally demonstrated why RAG matters: a paraphrase ("gedung candi lawas jawa") with no keyword overlap still surfaced the right report *and* a related place record from the existing corpus.

## 6. Scope Correction (or: Mem0 Is Fine, Everybody Stand Down)

Early in planning, the memory system (mem0) was on the retirement list as the research memory's successor. That was an overreach. The correction: **mem0 stays fully active** for every opencode session - preferences, decisions, learnings, the works. The only change is the research *deliverable path*: `general-research` writes into the KB via `kebab ingest`, and `kb-recall` pulls it back. That is the entire scope. No MCP removal, no `MEM0_API_KEY` deletion, no mem0 skill retirement. (The misread nearly triggered a hub-config backup for nothing; good thing the user vetoed the first backup call.)

## 7. Pending Actions

- Wire any remaining research-producing skills (e.g. `write-to-blog` attendance not needed - that targets the journal) to the KB ingest convention if desired.
- Optionally make `kebab ingest` auto-run on the homelab via a `.path` watcher instead of the skill calling ssh + scp each time.
- Consider a `kebab` git-hook or post-apply step that rebuilds only the changed record's chunks for large KBs (31 records is fine; 500 might not be).

## 8. Recommendations

- **The CLI remains the honest home.** Last week's open question, answered with evidence: no GUI returning. `ingest` + `recall` give the pipeline a survivor's life without resurrecting the webapp.
- **Keep reports whole.** One `report` record per deliverable beats per-claim fragments for recall quality - semantic search retrieves the chunk, then the agent reads the full report behind the cited id.
- **Keep the type-agnostic design.** Adding `"report": "reports"` to `TARGET_DIRS` was ~5 lines of config plus a model; every lower layer (index, search, vectors) lit up for free. Future record types get the same deal.
- **Quote YAML 2.x frontmatter defensively.** Any skill that carries brackets, colons, or quoted examples in `description`/`argument-hint` will eventually eat a parse failure; quote the whole value once and move on.

---

Generated by Big Pickle (OpenCode)
