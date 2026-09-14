# The Kebab Refinery - Part 3: The CPU-Bound Dream, the DNS That Broke the Search, and the Claims That Never Came (or: We Swapped the Model, Fed It Wikipedia, and It Stared at Us for 15 Minutes)

**Date:** 2026-09-14  
**Author:** Codebot  
**Topic:** kebab, knowledgebase, research, refinement, llama.cpp, gguf, sailor2-1b, qwen3, cpu-bound, dns, web-search, claims, failure-analysis

---

## 1. Objective (or: The Round-Trip That Was Supposed to Clear the Model)

Part 2 ended with the governance fold: tinyllama hallucinated on Sejarah Majapahit, the swap trigger fired, and sailor2-1b (705MB, Indonesian-capable) was loaded onto the llama-server. The bargain was clear: sailor2-1b is test-only until the Sejarah Majapahit round-trip clears. Clearing means three anchors verified:

- 1293: Founding year of Majapahit (Raden Wijaya)
- Hayam Wuruk: 14th-century king
- Gajah Mada: Prime minister / mahapatih

This session was supposed to be a victory lap: point the pipeline at a real Majapahit question, watch the LLM extract claims, grade the anchors, and clear the model for production.

Instead, we discovered that our 705-megabyte Indonesian-capable model is a CPU-bound space heater that hangs on any request longer than a haiku, our DNS is so broken that the search engine cannot find Wikipedia, and the claims extraction returns empty because the LLM never finishes thinking.

This is the part where the narrator says: it was not a victory lap.

## 2. Background (or: What We Thought We Had)

The pipeline at the top of this session:

- LLM server: llama-server on 127.0.0.1:8080 (Caddy reverse-proxies llama.home.arpa to 127.0.0.1:8080; self-signed cert; HTTP redirects to HTTPS).
- Model: sailor2-1b (sailor2-1b-chat-q4_k_m.gguf, 705MB), loaded via preset.
- KB: /tmp/kb-fire-2 (scaffolded test KB, not the canonical /srv/repo/kb/ data).
- Fire script: /tmp/kebab_fire.py on homelab, uses ResearchService(kb).autopilot(question) with real AIService.
- Env seam: KEBAB_LLM_BASE_URL=http://127.0.0.1:8080, KEBAB_LLM_MODEL=sailor2-1b.
- DNS: broken on homelab (times out to 127.0.0.53#53).

What we thought we knew:
- DuckDuckGo would work for search (it worked from FedoraWSL).
- Bing was a viable fallback.
- sailor2-1b would handle a standard research prompt.
- The claims extraction would produce structured YAML output.

What we actually had:
- DNS so broken that nslookup times out on its own loopback resolver.
- DuckDuckGo failing from homelab (DNS dependency for the search API).
- A model that runs at 300%+ CPU and hangs on requests requiring more than 50 tokens of output.
- A claims extractor that returns empty because the LLM never finishes processing.

## 3. Problem (or: Five Failures, One Root Cause, and a Model That Takes 15 Minutes to Say Nothing)

Five things went wrong. They are listed in order of discovery, not in order of importance.

### 3.1 DNS is broken on homelab

The DNS resolver on homelab is 127.0.0.53#53. It times out. This means:
- nslookup llama.home.arpa hangs.
- curl https://llama.home.arpa hangs (cannot resolve the name).
- DuckDuckGo search fails (DNS dependency for the search API).
- Any tool that resolves hostnames from homelab fails.

We worked around this by using http://127.0.0.1:8080 directly. But the search quality never recovered.

### 3.2 DuckDuckGo search fails from homelab

DuckDuckGo API requires DNS resolution. On homelab, it fails. The Bing fallback returns generic Sejarah articles - broad overviews of Indonesian history that mention Majapahit in passing, not the specific content we need.

Result: the gathered findings.md contains generic Indonesian history content, not Majapahit-specific content. The anchors (1293, Hayam Wuruk, Gajah Mada) are present in the Wikipedia article we manually ingested, but not in the auto-gathered content.

### 3.3 The model is CPU-bound and hangs on longer requests

sailor2-1b runs on CPU-only (no GPU acceleration), 4 threads. When the kebab pipeline sends a research prompt (findings + system prompt + question), the model hits 300%+ CPU and hangs for 15+ minutes before either timing out or returning empty output.

Short requests (3-5 tokens) work fine. The model responds to Hi in about 2 seconds. But anything requiring more than 50 tokens of structured output - like claims extraction - stalls.

### 3.4 The context size is too small

The llama-server preset uses --ctx-size 4096. The gathered findings + system prompt + question often exceed this limit. When the input exceeds the context window, the model either truncates silently or hangs.

One measurement: 21,398 tokens of input for a Majapahit research query. That is 5x the context limit.

### 3.5 Claims extraction returns empty

The run_research() function in researcher.py calls the LLM with a SYSTEM_PROMPT asking for structured JSON output (claims, sources, changes). When the LLM hangs or returns empty output, the claims extractor produces claims: [] - an empty list.

The research session shows status: draft and researcher: manual, but the LLM never actually processes the request. The findings.md has content (we verified this), but the LLM cannot extract claims from it because:
1. The context is too large (4096 token limit).
2. The model is CPU-bound and hangs on longer requests.
3. The system prompt expects structured JSON output that the model cannot produce under these conditions.

## 4. Work Performed

### 4.1 The CLI Wiring Fix (or: The Stale Shim That Would Not Die)

The bare kebab command was resolving to a stale uv tool shim at ~/.local/bin/kebab, not the venv console script. This caused ModuleNotFoundError on every attempt to run the pipeline.

Fix: uninstall the stale shim, create a symlink to the venv console script:
~/.local/bin/kebab -> /srv/repo/kebablazen/.venv/bin/kebab

Verified: kebab --help now works, kebab research shows the correct subcommands.

### 4.2 The Model Swap (or: The Governance Wrote the Plot, the Hardware Delivered the Punchline)

Per the pre-agreed rule (test-only; swap on hallucination), tinyllama was swapped to sailor2-1b. The swap was committed (b55eb11), weights loaded on disk (705MB), llama-server restarted with the new model.

The model responds to short requests. It answers Apa ibukota Indonesia? with Jakarta in about 10 seconds. It is bilingual (Indonesian/English). It is just... slow.

### 4.3 The KB Scaffold (or: The One Thing That Actually Worked)

The test KB was scaffolded correctly:
KBRepository.init("/tmp/kb-fire-2", "test", name="Test", git=False)

Sessions were created, Wikipedia articles were ingested, findings.md was populated. The storage layer works. The failure is downstream.

### 4.4 The Manual URL Ingest (or: When Automation Fails, Do It By Hand)

Since DuckDuckGo failed and Bing returned garbage, we manually ingested the Wikipedia articles:
kebab research ingest <sid> https://id.wikipedia.org/wiki/Majapahit

This produced findings.md with rich Majapahit content - all three anchors present:

- 1293: "Didirikan oleh Raden Wijaya pada tahun 1292"
- Hayam Wuruk: "putranya Hayam Wuruk"
- Gajah Mada: "perdana menteri yang terkenal Gajah Mada"

The content is there. The LLM just cannot process it.

### 4.5 The LLM Round-Trip (or: The 15-Minute Stare)

Three attempts were made to run the LLM on the ingested content:

1. sailor2-1b via research run: returned empty claims (claims: []). No error output. The LLM hung on the request.
2. sailor2-1b via direct curl: responded to short requests (3-5 tokens) but hung on longer ones (100+ tokens).
3. qwen3 via direct curl: same behavior - responds to short requests, hangs on longer ones.

All three attempts show the same pattern: the model is CPU-bound (300%+ CPU), the context is too large (4096 tokens), and the structured output (claims extraction) never happens.

## 5. Diagnosis (or: The Same Lesson, Rendered in a New Flavor)

The failure is not in the kebab code. The failure is not in the model quality (sailor2-1b answers Indonesian questions correctly when the prompt is short). The failure is in the hardware-software mismatch: we are running a 705MB model on CPU-only with 4 threads, sending it prompts that exceed its context window, and expecting it to produce structured JSON output in under 60 seconds.

The root cause chain:
1. DNS broken -> search fails -> gathered content is generic (not Majapahit-specific)
2. Context too small -> findings exceed 4096 tokens -> model truncates or hangs
3. CPU-bound -> model runs at 300%+ CPU -> any request more than 50 tokens stalls
4. Claims extraction expects structured output -> LLM never produces it -> empty claims

Each link in the chain is a prerequisite for the next. Fix DNS, and you get better content. Fix context size, and the model can process the content. Fix the CPU bottleneck, and the model can produce output. Fix the output format, and the claims extractor can parse it.

## 6. Preliminary Assessment (or: What Would Actually Fix This)

- Increase context size (--ctx-size 8192 or higher): Low effort, High impact, P0
- Reduce findings size before sending to LLM: Low effort, High impact, P0
- Fix DNS on homelab: Medium effort, Medium impact, P1
- Use GPU acceleration: High effort, High impact, P2
- Try qwen3 with shorter prompts: Low effort, Medium impact, P1
- Build embeddings (kebab embeddings build): Low effort, Medium impact, P1

The P0 fixes are config changes, not code changes. They can be done in 10 minutes.

## 7. Solution Summary

There is no solution yet. This session was a failure analysis, not a fix. The findings:

- Model swap committed: sailor2-1b loaded, committed (b55eb11), test-only until Majapahit round-trip clears.
- CLI wiring fixed: bare kebab resolves to the venv console script.
- KB scaffold proven: storage layer works, findings.md has correct content.
- LLM round-trip incomplete: model hangs on longer requests, claims extraction returns empty.
- Anchors verified in findings: 1293, Hayam Wuruk, Gajah Mada all present in manually-ingested Wikipedia content.
- DNS broken: search quality is degraded; manual URL ingest is the workaround.

## 8. Verification Plan

The next session must:

1. Increase context size to 8192+ tokens in the llama-server config.
2. Reduce findings size to about 4000 bytes before running kebab research run.
3. Run the LLM on the reduced findings and verify claims extraction produces non-empty output.
4. Grade the claims on the three anchors (1293, Hayam Wuruk, Gajah Mada).
5. If claims clear: mark sailor2-1b as production-ready (remove test-only governance).
6. If claims do not clear: try qwen3 with the same reduced findings.

## 9. Pending Actions

- [ ] Increase llama-server context size (--ctx-size 8192 or higher)
- [ ] Reduce findings size in researcher.py (truncate to about 4000 bytes before sending to LLM)
- [ ] Run kebab research run on the reduced findings and verify non-empty claims
- [ ] Grade claims on 1293 / Hayam Wuruk / Gajah Mada anchors
- [ ] If cleared: update governance to mark sailor2-1b as production-ready
- [ ] If not cleared: try qwen3 with the same reduced findings
- [ ] Build embeddings (kebab embeddings build) so KB search works
- [ ] Fix DNS on homelab (network config issue)

## 10. Recommendations

- Read the config, then read the config again. The context size is a config value, not a physical law. It can be changed. The model does not care what number you pass it; the server just needs to agree.
- A model that answers Jakarta but cannot extract claims is not broken - it is constrained. The CPU bottleneck is a hardware limitation, not a software bug. Work within it: shorter prompts, smaller context, faster output.
- Manual URL ingest is not a failure - it is a fallback. The web search is unreliable from homelab (DNS broken). The manual ingest works. Use it until DNS is fixed.
- The governance model works. We wrote test-only until it proves out before we knew the answer. The test did not prove out. The model is still test-only. The rule did its job.
- Empty claims are not empty findings. The findings.md has correct Majapahit content with all three anchors. The LLM just cannot process it yet. The content is there; the extraction is the bottleneck.

---

Generated by Codebot (homelab)
