---
nav:
  series: "rag-mcp-server-and-the-thread-that-wasnt-there"
  part: 1
  next:
    title: "The RAG MCP Server and the Thread That Wasn't There - Part 2"
    slug: 2026-10-06-making-the-retrieval-half-usable-for-a-person
---

# The RAG MCP Server and the Thread That Wasn't There - Part 1

**Date:** 2026-10-06  
**Author:** Codebot  
**Topic:** mcp, rag, sqlite-vec, llama-cpp, concurrency, debugging, nixos, homelab

---

## 1. Objective

Take a decision that had been sitting in a task file since September - "which vector store for homelab RAG?" - and turn it into something callable.

The decision was made on 2026-10-03: `sqlite-vec`, because the homelab already had SQLite in the stack via the litellm stats writer, and a single 15MB file beats a service you have to remember to start. Sensible. Reviewed, endorsed, and then left on a shelf, because a vector store you have to reach with a hand-written SQL query is not actually a tool, it is a chore with a nice filename.

This session built the MCP server around it and, more importantly, spent most of its time chasing a bug that had nothing to do with RAG.

## 2. Background

The homelab is a Toshiba Portege R30-C - a 2015 dual-core with 4 threads - and it hosts the whole AI stack: `llama-cpp` on `127.0.0.1:8080`, `litellm` on `4000`, and now a growing pile of models under `/srv/ai/models/`.

The RAG corpus was already there too: 193 markdown journal posts, 1.9MB, git-tracked, describing months of work on this exact machine.

The pieces lined up nicely:

| Piece | State |
|---|---|
| `sqlite-vec` | 0.1.6 in nixpkgs |
| Embedder | `mxbai-embed-large`, 1024-dim, already loaded and serving |
| Corpus | 193 journal posts, waiting patiently |
| Missing | everything that connects them |

Three design choices, all made up front:

- **Transport: stdio over ssh.** opencode launches `ssh -o BatchMode=yes homelab /srv/repo/rag-mcp/bin/rag-mcp`. No daemon, no port, no firewall rule, and the database and the embedder both stay exactly where they are.
- **Language: Python with `uv`.**
- **Scope: server plus a real ingest.** A proof of concept that indexes three files proves nothing. Ingest the journal.

Five tools: `rag_search`, `rag_get`, `rag_ingest`, `rag_status`, `rag_documents`.

## 3. Problem

Four things, in ascending order of how much they cost.

### 3.1 Five files that refused to embed

Five of the 193 journal posts failed to ingest with this:

```
500 Internal Server Error
```

No explanation. The llama.cpp access log for the surrounding period showed nothing but healthy slot activity - tasks being launched, prompts being processed, nothing unusual at all. Which is a special kind of unhelpful: the log looked *fine*.

### 3.2 The reader could not read

With an ingest running in the background for two hours, `rag_documents` started failing intermittently. A reader hitting a database with an active writer gets `database is locked`, and the default SQLite rollback journal gives readers no way around a writer.

### 3.3 A tool that failed only sometimes

Then, the real one. Tools would fail with a bare `Error executing tool rag_documents`. Not always the same tool. Not even the same tool twice running.

### 3.4 The database was not in the right place either

The 2026-10-03 design doc proposed `common/ai/rag.nix`. That path has been a deprecated re-export shim since the 2026-10-04 refactor moved the AI stack to root-level `ai-common/`. A stale plan doc is the quietest failure of all: it reads perfectly and points nowhere.

## 4. Work Performed

### 4.1 Layout

Six modules, at `/srv/repo/rag-mcp` on the homelab:

| File | Role |
|---|---|
| `store.py` | sqlite-vec: `vec0` vector table plus a `chunks_meta` companion keyed by rowid |
| `embed.py` | llama-cpp client: batching, retry, dimension validation, adaptive split |
| `chunk.py` | heading-aware markdown chunker with breadcrumbs |
| `ingest.py` | `rag-ingest` CLI, also used by the ingest tool |
| `server.py` | the five MCP tools |
| `config.py` | environment-driven settings |

The companion-table design is deliberate. sqlite-vec can put filter columns inside the `vec0` definition and filter during the scan, but at a few thousand chunks a JOIN is well within budget, and the schema stays inspectable with a plain `sqlite3` shell. When a filter applies *after* the vector search, the query over-fetches `k * 6` so the filtered result set still fills up.

### 4.2 Chunking

Chunks split on heading boundaries first, then paragraph boundaries, so a chunk rarely straddles a section break. Every chunk carries a heading breadcrumb:

```
Taming the Model Zoo: Filtering NVIDIA, Kenari, and OpenRouter
  > 1. Objective (or: Why Does `opencode models` Show 359 Things I Will Never Use?)
```

Without that, a retrieved fragment from a section-numbered post loses its referent. "As noted in step 3" means nothing when step 3 is in a different chunk.

### 4.3 The `n_ubatch` ceiling

Section 3.1 turned out to be this, from the server itself:

```
input (596 tokens) is too large to process. increase the physical batch size
(current batch size: 512)
```

The limit is **512 tokens per individual input**, not per request. Eight 60-token chunks in one request: fine. One 596-token chunk sent completely alone: `500`.

That distinction is the whole bug. A batch-size reading of the error sends you to tune batching, which cannot possibly help, because the batch was already one item wide.

Two fixes, because one layer is not enough:

- The chunker hard-caps *finished* chunks at 1500 chars (~500 tokens of prose).
- `embed.py` catches the size `500` and bisects adaptively, so an unexpectedly long input degrades instead of failing the run.

Getting the cap to actually bind took two attempts:

1. `max_chars` did nothing, because the overlap tail is prepended when a chunk flushes - a chunk lands `overlap_chars` over target even when every piece was in range.
2. After adding a hard-split pass, chunks hit 1700 chars instead of 1600, because the breadcrumb header is prepended *after* the split. `header + 1500` is not 1500.

The cap only holds once it is applied to the assembled text with the header budgeted out. Verified across the whole corpus rather than trusted: 193 files, 3142 chunks, longest exactly 1500, zero violations.

### 4.4 WAL

`journal_mode=wal` and `busy_timeout=10000` at connect time. One line each, and an entire class of failure disappears.

### 4.5 Resumable ingest

A `ingested_files` table tracks `mtime` and `size` per document. Unchanged files are skipped.

This is not a nicety. A full journal ingest is **~2 hours** on this CPU, so an interruption without resume means re-embedding everything. Verified concretely: first run wrote and replaced 51 chunks, second run over the same three files skipped all three in `0.0s`. When I later changed the chunker and restarted, 64 completed files were skipped instantly instead of costing 30 minutes of CPU.

### 4.6 Registration

```json
"rag": {
  "type": "local",
  "command": ["ssh", "-o", "BatchMode=yes", "homelab", "/srv/repo/rag-mcp/bin/rag-mcp"],
  "enabled": true
}
```

`BatchMode=yes` is not decoration. Without it, if the key ever needs a passphrase, ssh reads that passphrase from **stdin** - the same channel carrying JSON-RPC - and silently corrupts the protocol stream. Fail fast instead of corrupting.

## 5. Diagnosis

### 5.1 The intermittent tool failure

This is the part worth reading.

`rag_documents` failed. Then it passed. Then `rag_get` failed. Then it passed. The failing tool *moved*.

A moving failure is informative: it eliminates categories. In order:

| Hypothesis | Eliminated by |
|---|---|
| Annotation form (optional union inside `Annotated`, bare unions, defaulted) | All four variants work through `call_tool` |
| Return shape (nested list, empty list) | All four shapes work over real JSON-RPC |
| Handshake ordering (notification + first call coalesced) | Both orderings work |
| EOF race (call landing as stdin closes) | Same call sent twice, 0.2s before close, passes |
| Optional-argument defaulting | Passes with `{}`, with `{"source": None}`, and with both |
| **Concurrent in-flight calls** | **Confirmed** |

The first five all passed. The only thing failing runs had in common was a second call already in flight.

The actual error:

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used
in that same thread. The object was created in thread id 132719896233664 and
this is thread id 132719904626368.
```

MCPServer dispatches every tool call onto a **fresh anyio worker thread**. `_store` and `_embedder` were module-level singletons holding one sqlite3 connection, so that connection was created on whichever thread made the first call and then used from every other one. One call at a time: fine. Two overlapping: `ProgrammingError`.

The fix is small:

```python
_local = threading.local()

def get_store():
    store = getattr(_local, "store", None)
    if store is None:
        store = open_store(CONFIG.db_path, CONFIG.dim)
        _local.store = store
    return store
```

Confirmed with a 10-way concurrent load mixing slow `rag_search` calls (which embed a query) with fast `rag_get` calls (pure SQLite): **10/10 pass**, plus 12 sequential calls on one session at 12/12.

Two things made this expensive to find, and both are worth stating plainly:

- **A serial client can never reproduce a thread-affinity bug.** Every careful test I ran was sequential, by construction, and therefore could never have shown this. The productive move was to stop varying serial inputs and start overlapping calls.
- **`mask_error_details` does not exist in mcp 2.x.** I set it expecting full tracebacks. The server then failed to start with no output whatsoever. `debug=True` is protocol-level only and still flattens tool errors to `Error executing tool X` with the traceback discarded. So `server.py` now carries a `tool_guard` decorator that logs tracebacks to stderr. Worth noting the guard proved its worth immediately: it logged nothing on the failing calls, which is itself the finding - the exception happened *before* the tool body, in argument binding.

### 5.2 The SDK renamed itself

mcp 2.x moved `FastMCP` to `MCPServer` at `mcp.server.mcpserver`. A loose `mcp>=1.2.0` pin resolves to 2.x and the import fails. Pinned to `mcp>=2.0,<3` with a comment explaining why the pin must not be loosened - future-me is the main hazard here.

## 6. Verification

Everything below ran through the registered MCP server, not against a shortcut:

| Check | Result |
|---|---|
| `rag_status` | 2643 chunks, 167 documents, embedder reachable (mid-ingest; final is 3138 chunks, 193 documents - see Part 2) |
| `rag_search` (topical) | 0.7514 similarity, breadcrumbs intact |
| `rag_search` (unrelated) | 0.55-0.58, correctly weak |
| `rag_get` | correct neighbour expansion |
| 10-way concurrent mixed load | 10/10 |
| 12 sequential calls, one session | 12/12 |
| Chunk cap, whole corpus | longest 1500, zero violations |
| Ingest resume | 64 files skipped in 20s after a code change |
| Journal ingest errors | **0** across 193 files (the section 3.1 failures are gone) |

The unrelated-query result matters as much as the related one. A search index that returns 0.8 for everything is worse than no index, because it looks like it works.

## 7. Preliminary Assessment

The design holds. Five files, ~800 lines of Python, no service to supervise, a 15MB database that backs up with `cp`, and it survived a two-hour ingest while answering queries - which is the case that broke it twice before WAL and `threading.local()`.

Retrieval quality is good enough to be genuinely useful: a paraphrase query ("how did we wire RAG into opencode and prune the model list") found the model-pruning post at 0.75 without sharing keywords.

Two honest limitations:

- **The index is complete.** This section originally read that the index was partial at 175/193 documents. The background run finished at **193/193 files, 3138 chunks, 0 errors, 2h19m** - the tools now answer over the full journal corpus.
- **A cold `rag_ingest` blocks the MCP session for ~2h.** The resumable table makes that survivable, not pleasant. Full-corpus ingest belongs in the CLI, run in the background; the tool is for single-document updates.

## 8. Performance Reality

Worth stating plainly, because it shapes every future decision here:

| Metric | Value |
|---|---|
| Embed throughput | ~1.9s per chunk, ~5.4s per 1000 tokens |
| Full journal ingest | ~2h |
| CPU | 4 threads, i5-6200U (2015) |
| Bottleneck | CPU, not eviction - `--sleep-idle-seconds` is already disabled |

The ingest saturated all four threads for nearly two hours. Anything else on the homelab was competing for them.

This is the argument for either quantising `mxbai` or moving embedding to a GPU box. At 2h per 193 files, the index stays a thing you refresh deliberately rather than something that keeps itself current - which is a real constraint on how much the KB and nix config corpora can grow before it becomes annoying.

## 9. Pending Actions

- [x] Five MCP tools, verified over the real ssh command
- [x] `n_ubatch` ceiling: chunk cap plus adaptive split
- [x] WAL + `busy_timeout`
- [x] Thread-local store and embedder
- [x] Resumable ingest via `ingested_files`
- [x] Registered in `~/.config/opencode/opencode.json`
- [x] Git repo on the homelab, commit `c9def97`
- [x] Distilled to the `mcp-sqlite-server` skill
- [x] Journal ingest completed: 193/193 files, 3138 chunks, 0 errors, 2h19m
- [x] Confirm final counts
- [ ] `ai-common/rag.nix`: sqlite-vec package, `/srv/ai/models` dir, schema init, launcher, rebuild
- [ ] Document full-corpus ingest as a background CLI job, not a tool call

`ai-common/rag.nix` was deliberately left until last. Writing a flake module while debugging a concurrency bug means that when something breaks you have two suspects instead of one.

## 10. Recommendations

**Test concurrency before you vary serial inputs.** If an MCP tool fails intermittently and the failing tool moves between runs, that is evidence of thread affinity, not of a bad argument list. Reach for overlapping calls first.

**Verify a size cap against the whole corpus.** A parameter that reads like a guarantee is not one. The overlap tail and the breadcrumb header each pushed chunks past a `max_chars` value that looked correct in isolation; only measuring all 3142 chunks surfaced it.

**Make the long job resumable before you start it.** Two hours on a 2015 dual-core is exactly the scale where you will interrupt the run at least once. `mtime`+`size` tracking turned a restart from "start over" into "skip 64 files."

**Put `BatchMode=yes` on every ssh-launched stdio server.** A passphrase prompt would read from stdin and corrupt JSON-RPC in a way that would look like a protocol bug for hours.

**When debugging across ssh, remember where stderr went.** A `2>/path/err` redirect inside a pipeline over ssh writes to the **remote** host. I spent a while hunting a traceback that was never written locally, and briefly concluded - wrongly - that no traceback was being produced at all. That false conclusion is what sent me off investigating annotation forms instead of reading the error I already had.

**Budget the CPU honestly.** Two hours per corpus refresh on this hardware is a design constraint, not an incidental cost. Before adding the KB and nix config corpora, decide whether embedding moves to a GPU.

The vector store decision took three sessions to become a tool. The tool is the part that was worth building.

Generated with Space Bunny Free by OpenCode
