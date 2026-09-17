# Pruning Tasks (or: The Keeper Finally Stops Accumulating)

**Date:** 2026-09-17  
**Author:** Codebot  
**Topic:** pruning, task management, model cleanup, experimental setup, anythingllm, bert-tiny, minilm, tinyllm

---

## 1. Objective (or: What Does "Prune" Mean Anymore?)

This report documents a single session of pruning: models off the Windows machine, tasks off the todo list, and a leaked secret out of the git history. The goal was to leave the Windows model zoo with only two working residents -- bert-tiny and vibevoice -- parked as independent research tasks, and to hand them a clean experimental framework (tinyllm) to play with.

## 2. Background

The Windows AI Zoo had grown to an unruly state. `C:\ai\models` once held lm Studio, whisper, Qwen3-VL-4B-Thinking, and a rotating cast of GGUFs. The blog series had drifted from LM Studio (Part 1) to RAG wiring (Part 2) to AnythingLLM (Part 3), and the series parts themselves had lost their numbering. Meanwhile, two models -- bert-tiny (4.4M PyTorch base encoder) and vibevoice (1.6 GB streaming TTS) -- were neither useful in production nor disposable, so they were promoted to research tasks.

## 3. Problem

1. **The model directory was cluttered.** Whisper (a whisper.cpp GGML file AnythingLLM cannot use), Qwen3-VL-4B-Thinking (a vision model missing its mmproj), and the Open WebUI experiment were all dead weight on a 15.7 GiB CPU-only box.
2. **The blog series parts were unnumbered.** Part 1 and Part 2 had been published without the `-part-N` convention the series now uses, breaking the series grouping in `index.md`.
3. **The GitHub Pages push was blocked.** A leaked Google OAuth client secret (redacted) in the gmail MCP part 2 published HTML triggered GitHub secret scanning, halting the Part 3 publish.
4. **Two research tasks had no framework.** bert-tiny and vibevoice needed an orchestration layer (tinyllm) and an experiment plan before they could graduate from "stragglers" to "experiments."

## 4. Work Performed

### 4.1 Models Pruned

Deleted from `C:\ai\models`: whisper (`ggml-base.bin`, 142 MB), `Qwen3-VL-4B-Thinking.Q4_K_M` (3.2 GB), and the Open WebUI directory (`C:\ai\open-webui`). LM Studio's ghost (`~/.lmstudio`) was already gone. C: now has 259 GB free.

The surviving models are bert-tiny (18 MB, PyTorch `pytorch_model.bin`) and vibevoice (1.6 GB, `vibevoice-realtime-0.5B-q8_0.gguf`).

### 4.2 Six GGUFs Registered

Registered into AnythingLLM 1.16.1's bundled Ollama 0.20.7 (`:11434`) via temporary Modelfiles and `llm.exe create`: `mxbai-embed-large`, `qwen2.5-coder`, `qwen3`, `qwen3-vl:4b-instruct`, `sailor2-1b`, `tinyllama`. Store is 12 GB. Verification: qwen3 round-trip PASS, tinyllama rambles ("PASS-weak"), mxbai returns 1024-dim via `/api/embed`.

### 4.3 Series Renamed

Renamed part 1 and part 2 with the `-part-1` / `-part-2` suffixes via `git mv` (100% across all refs). Updated `index.md` latest posts and added a "Windows AI Zoo" series section. Committed `c3c41c5` on `main`.

### 4.4 Part 3 Written and Published

Wrote `2026-09-17-windows-ai-zoo-anythingllm-returns-part-3.md` (139 lines). Published to GitHub Pages -- initially blocked by secret scanning (see 4.5), then republished after redaction. Final gh-pages tip: `6aadad1`.

### 4.5 Secret Redacted

The gmail MCP part 2 post (`2026-09-16-gmail-mcp-wiring-part-2.md`) contained a live Google OAuth client secret (`REDACTED`) in two places (line 67 and 85). Redacted to `REDACTED` in the source, committed (`49e17c0`), reset local gh-pages to clean tip `fee5271`, and republished. **Action item: rotate the secret in Google Console.**

### 4.6 Research Tasks Created

Two pending task files created: `pending-work-with-bert-tiny.md` and `pending-work-with-vibevoice.md`. The bert-tiny task was updated with a MiniLM comparison table, `zozoheir/tinyllm` reference, and the chosen directions (a: RAG pipeline via tinyllm, b: fine-tune classifier via tinyllm). The vibevoice task documents the streaming TTS pipeline requirements (tokenizer.gguf + voice pack + vibevoice.cpp/CrispASR runtime).

### 4.7 Model Research Summaries

| Model | Params | Dims | Status | Use |
|---|---|---|---|---|
| bert-tiny | 4.4M | 128 | base encoder, needs fine-tune | task-parked, directions a+b |
| vibevoice | 1.6 GB | 24kHz WAV | streaming TTS, English-only | task-parked |
| all-MiniLM-L6-v2 | 22.7M | 384 | sentence-optimized | replacement embedder, GGUF available |

## 5. Diagnosis

The pruning revealed a pattern: models accumulate faster than they are retired. The keeper's instinct was to keep everything "just in case," which turned `C:\ai\models` into a museum. The fix is not deletion alone -- it is the promotion of stragglers to explicit research tasks (with files, checkboxes, and comparison tables) so they stop cluttering the runtime and start having a purpose.

The secret-scanning block was a blessing in disguise: it caught a live credential before it reached the public GitHub Pages site. Redaction is not rotation -- the secret still exists in local git history, which is why rotation in Google Console is the recommended follow-up.

## 6. Preliminary Assessment

The Windows model zoo is now minimal and functional: AnythingLLM 1.16.1 with bundled Ollama serving 6 GGUFs, two research tasks parked (bert-tiny, vibevoice), and a clean gh-pages branch carrying three published series parts. The experimental framework (tinyllm) is identified for both tasks.

## 7. Solution Summary

- Pruned `C:\ai\models` to bert-tiny + vibevoice (task-parked).
- Registered 6 GGUFs into AnythingLLM bundled Ollama (12 GB store).
- Renamed blog series parts 1 & 2; committed.
- Wrote and published Part 3; redacted leaked OAuth secret; republished.
- Created two pending task files with research baked in.
- Selected tinyllm as the orchestration framework for both tasks.

## 8. Verification Plan

1. Confirm main = `49e17c0`, gh-pages = `6aadad1`, working tree clean.
2. Confirm the secret no longer appears in the source post or gh-pages branch.
3. Confirm bert-tiny and vibevoice task files exist and contain the chosen directions.
4. Rotate the Google OAuth client secret in Google Console (recommended, not done).

## 9. Pending Actions

- Rotate the leaked Google OAuth client secret in Google Console.
- Begin direction (a): RAG pipeline smoke test with bert-tiny via tinyllm, then swap to MiniLM.
- Begin direction (b): fine-tune a small classifier on bert-tiny via tinyllm.
- vibevoice: acquire tokenizer.gguf + voice pack + runtime (vibevoice.cpp or CrispASR).
- Optionally delete bert-tiny if the experiments prove it has no ceiling worth climbing.

## 10. Recommendations

Keep bert-tiny and vibevoice as task-parked experiments. Use tinyllm as the orchestration layer for both directions (a) and (b). Do not install the full CUDA torch variant -- the CPU-only index (`--index-url https://download.pytorch.org/whl/cpu`) is ~500-600 MB and sufficient for both experiments. Rotate the leaked OAuth secret before any further publishing.

The keeper steps back from the zoo. The animals are accounted for. Part of the work now belongs to the experiments themselves.

Generated by Big Pickle (OpenCode)
