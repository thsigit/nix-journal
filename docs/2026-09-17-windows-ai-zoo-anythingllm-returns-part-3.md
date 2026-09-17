# Windows AI Zoo, Day Three: AnythingLLM Returns (With an Ollama in Its Pockets)

**Date:** 2026-09-17  
**Author:** Codebot  
**Topic:** windows, anythingllm, ollama, local models, gguf, open webui, bert-tiny, vibevoice

---

## 1. Objective (or: The Zoo Keeps Changing Landlords)

Two days of zookeeping have taught us one lesson: the Windows model zoo loves a relocation. Part 1 built the zoo around LM Studio and llama.cpp. Part 2 wired RAG and pruned to six. Then, in the space of a week, the keeper deleted *both* AnythingLLM and LM Studio, moved in with Open WebUI, and then - a few minutes before this session - deleted Open WebUI too.

The loop kept ending in the same place: the Windows machine wants a practical local-AI app on a 15.7 GiB CPU-only box, and Open WebUI's best seat in the house is on the homelab, which already runs it. Maintaining a second instance on Windows was redundant before it was ever deployed.

So the decision, delivered flatly: **reinstall AnythingLLM**, because it is the practical Windows app, and retire the Open WebUI-on-Windows experiment. The session that followed was the setup of the new resident: AnythingLLM 1.16.1 with its own bundled Ollama runtime, six GGUF models registered into it, and two stragglers (bert-tiny, vibevoice) promoted to research tasks.

## 2. Background (or: Where We Left the Animals)

The family tree, for the record:

- **Part 1 (2026-09-09):** llama.cpp installed via scoop, LM Studio hard-linked over `C:\ai\models`, AnythingLLM repointed at the local server, 18 GB of elephants evicted.
- **Part 2 (2026-09-10):** RAG wired with a real embedder (`mxbai-embed-large`), API keys minted, roster pruned to 6 models (3 chat LLMs + 3 embeddings), LM Studio serving on port 1234.
- **The Open WebUI interlude (2026-09-15):** both apps deleted; Open WebUI + llama.cpp installed as a two-process stack (`:8080` interface, `:8081` inference, one `start.ps1`). The model directory was reorganized into per-model bungalows under `C:\ai\models`, each with a `-cpp.yaml` and a fresh roster: `bert-tiny`, `mxbai-embed-large`, `qwen2.5-coder`, `qwen3`, `sailor2-1b`, `tinyllama`, `vibevoice`, `whisper`.

The interlude's own writeup exists: "My Windows Local LLM Setup: Open WebUI + llama.cpp" (2026-09-15). It is now a historical artifact - the keeper outgrew it the same week it was drafted.

## 3. Problem (or: One Interface Too Many, Zero Runtime Selected)

1. **Open WebUI was duplicating the homelab.** The homelab already runs Open WebUI against the LiteLLM zoo. A second instance on Windows means a second `DATA_DIR`, a second port, a second version to babysit, all for the same interface the keeper already maintains on the server. Redundancy with no payoff.
2. **The new AnythingLLM had no models to serve.** A fresh install points at nothing: no LLM provider, no embeddings, and an empty model store. The GGUF files in `C:\ai\models` were orphans waiting for a runtime.
3. **The roster included dead weight.** `whisper` (a whisper.cpp GGML file AnyLLM can't use) and `Qwen3-VL-4B-Thinking.Q4_K_M` (a vision model whose camel had no mmproj saddle) were taking up a literal gigabyte each with no path to usefulness.

## 4. Work Performed

### 4.1 Open WebUI, Closed

The interlude was dismantled: `C:\ai\open-webui` (start script, `DATA_DIR`, everything) removed. The homelab keeps its instance; Windows keeps none. lm Studio's ghost stayed dead too - `~/.lmstudio` was long gone. llama.cpp (scoop shims) survived the purge and remains a usable CLI door, but it is no longer the interface's backend.

### 4.2 AnythingLLM 1.16.1, Reinstalled

AnythingLLM 1.16.1 sits at `C:\Users\SIGIT\AppData\Local\Programs\AnythingLLM`. Crucially for the no-Docker, no-WSL constraint, the desktop build ships its **own bundled Ollama runtime** - no separate Ollama install needed:

```text
resources\ollama\llm.exe
storage\engines\ollama\llm.exe      <- 0.20.7 (the live server)
storage\models\ollama\              <- the model store (content-addressed blobs + manifests)
storage\engines\ffmpeg\             <- ffmpeg/ffprobe for media
storage\engines\meeting-assistant\  <- tinyscribe STT engine
```

The bundled Ollama serves on `127.0.0.1:11434`, `OLLAMA_HOST=0.0.0.0`. Reachable from Windows PowerShell (`Invoke-RestMethod`) but not from WSL curl - a cross-VM networking quirk that cost a moment of confusion.

The AnythingLLM `.env` confirms the wiring: `LLM_PROVIDER='anythingllm_ollama'`, embedding engine still `native`.

### 4.3 The Six Batter Household (or: Registering GGUFs into Bundled Ollama)

Six GGUF models from `C:\ai\models` were registered into the bundled Ollama store via temporary Modelfiles and the `create` subcommand, all through PowerShell so `llm.exe` inherits the right host:

```powershell
$env:OLLAMA_HOST="127.0.0.1"
& "C:\Users\SIGIT\AppData\Roaming\anythingllm-desktop\storage\engines\ollama\llm.exe" `
    create <name> -f "C:\ai\models\_modelfiles\<name>-Modelfile"
```

Registered, each with the layer bytes the manifest records:

| model | tag | layer size |
|---|---|---|
| `mxbai-embed-large` | `latest` | 0.67 GB (1024-dim embed) |
| `qwen2.5-coder` | `latest` | 4.68 GB |
| `qwen3` | `latest` | 2.50 GB |
| `qwen3-vl` | `4b-instruct` | 3.30 GB (fused vision, no mmproj) |
| `sailor2-1b` | `latest` | 0.74 GB |
| `tinyllama` | `latest` | 0.64 GB |

Store total after registration: **12 GB** on disk.

Each model's source directory was then removed from `C:\ai\models` - the content-addressed blobs in the Ollama store own the bytes now, so the original bungalow would just be a second copy. The temporary `_modelfiles\` working directory was cleaned up afterward.

### 4.4 Verification (or: Proof, Not Vibes)

- `/api/tags` on the bundled server lists all six models.
- `qwen3` chat round-trip: PASS.
- `tinyllama` chat: works, rambles - the known "PASS-weak" flavor from Part 2.
- `mxbai-embed-large`: verified via `/api/embed` returning a 1024-dim vector.
- `qwen3-vl:4b-instruct`: fused vision encoder, so no separate `mmproj` hunting - the exact lesson Part 3's other model forgot.

### 4.5 The Two Funerals (or: Whisper and the Saddle-less Thinking Model)

| deleted | size | why |
|---|---|---|
| `whisper\ggml-base.bin` | 142 MB | whisper.cpp GGML; AnythingLLM STT is Xenova ONNX whisper (downloaded on demand), not GGML |
| `Qwen3-VL-4B-Thinking.Q4_K_M` | 3.2 GB | vision GCG whose runtime camel needs an mmproj that was never part of the file |

Both deleted after user confirmation, per house rules. Nothing else in `C:\ai\models` survives except the two holdouts below.

### 4.6 The Two Stragglers Become Research Tasks

`C:\ai\models` now contains exactly two residents: `bert-tiny` (18 MB, PyTorch) and `vibevoice` (1.6 GB, GGUF TTS). Neither is AnythingLLM material (no GGUF chat/embed path for bert-tiny; vibevoice is a TTS, not a chat model). Instead of deletion by default, both were researched and turned into independent tasks:

- **`pending-work-with-bert-tiny.md`** - `prajjwal1/bert-tiny` (L=2, H=128, 4.4M params): a base encoder, not a sentence-embedding model; needs fine-tuning. Includes a comparison table vs `all-MiniLM-L6-v2` (the AnythingLLM default embedder) and a pointer to `zozoheir/tinyllm` for the same niche.
- **`pending-work-with-vibevoice.md`** - `VibeVoice-Realtime-0.5B`: streaming TTS, needs `tokenizer.gguf` + a voice pack (both ~6-8 MB, downloadable) plus a `vibevoice.cpp`/CrispASR runtime. English-only, single-speaker, no AnythingLLM seat.

Both tasks carry their full research (requirements, commands, HF sources, keep-vs-delete options) and wait for the keeper's decision.

## 5. Results (or: The Magic Numbers)

| item | before (interlude) | after (today) |
|---|---|---|
| Windows interface | Open WebUI :8080 (deleted) | AnythingLLM 1.16.1 |
| Inference runtime | llama.cpp :8081 | bundled Ollama 0.20.7 (:11434) |
| Registered models | 0 (bare GGUFs) | 6 (qwen2.5-coder, qwen3, qwen3-vl, sailor2-1b, mxbai-embed-large, tinyllama) |
| Ollama store size | - | 12 GB |
| `C:\ai\models` contents | 8 model dirs | 2 (bert-tiny, vibevoice) |
| STT path | none usable | AnythingLLM local_whisper (Xenova ONNX) |
| Deleted this session | - | whisper (142 MB) + Qwen3-VL-4B-Thinking (3.2 GB) |
| Disk free on C: | - | 259 GB |

The 6-model lineup, registered and verified: **qwen2.5-coder** (code), **qwen3** (general), **qwen3-vl:4b-instruct** (vision), **sailor2-1b** (fast small), **mxbai-embed-large** (embedding), **tinyllama** (fastest, rambly).

## 6. Recommendations

1. **AnythingLLM 1.16.1 + bundled Ollama is the keeper pattern for this box.** The desktop build carries its own Ollama 0.20.7 on `:11434`; no Docker, no WSL, no separate runtime install. `LLM_PROVIDER='anythingllm_ollama'` and a 6-model store is the whole story.
2. **Register GGUFs, then retire the source.** Modelfiles + `llm.exe create` from PowerShell is the repeatable path. Once the blob store owns the bytes, delete the `C:\ai\models` copy (content-addressed = the store wins).
3. **Keep Open WebUI on the homelab, not on Windows.** The server already runs it; a client-box instance is a second thing to update for the same UI. AnythingLLM covers the Windows document/RAG seat.
4. **Fused-vision models beat the mmproj roulette.** `qwen3-vl:4b-instruct` works out of the box; the Thinking variant was saddle-less and deleted. When choosing a vision GGUF, prefer one that bundles its projector.
5. **AnythingLLM STT is Xenova ONNX whisper, not whisper.cpp.** `ggml-base.bin` was never loadable; do not repeat the download. The bundled `local_whisper` fetches ONNX models on demand.
6. **Leave research-grade stragglers as tasks, not corpses.** bert-tiny and vibevoice are neither AnyLLM usable nor worthless; the two task files capture their real constraints (fine-tuning vs missing tokenizer/voice) so a future session decides from evidence.

## 7. Open Questions and Follow-Ups

- **Embedding engine.** `.env` still says `native` (Xenova) while `mxbai-embed-large` idles in the store. Flipping `EMBEDDING_ENGINE` to ollama/mxbai is one of the immediate AnythingLLM settings to evaluate - Part 2 proved the store is worth using over the bundled default.
- **RAG re-wiring.** The Part-2 workspaces and API key survive conceptually, but the new install's `/api/v1` routes and keys were re-established on a fresh backend; a verification round-trip through the new store is pending.
- **bert-tiny + vibevoice** (independent tasks): decide keep/fine-tune (bert-tiny) or fetch the ~15 MB of missing vibevoice companions and a runtime.
- **AnythingLLM self-update behavior.** The 1.16.1 install will eventually move its furniture again (Part 2 saw routes migrate to `/api/v1` mid-session); expect the bundled Ollama version to bump with it.
- **The interlude writeup** ("Open WebUI + llama.cpp", 2026-09-15) was superseded the same week it was drafted; mark it superseded in the index rather than letting it linger as gospel.

---

Generated by Big Pickle (OpenCode)