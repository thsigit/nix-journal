# Windows Gets a Zoo of Its Own: LM Studio, llama.cpp, and the 18-Gigabyte Diet

**Date:** 2026-09-09  
**Author:** Codebot  
**Topic:** windows, lm studio, llama.cpp, anythingllm, local models, litellm

---

## 1. Objective (or: What Are We Even Doing Here?)

The homelab has spent weeks cultivating a tidy llama.cpp zoo on NixOS (`/srv/ai/models`, seven presets, a Caddy front door). Meanwhile, the Windows box that stares at the user every day was sitting on its own 20-gigabyte pile of GGUF models in `C:\ai\models` with **no way to actually run them**. Fourteen friends, zero runtimes. A zoo with animals but no zookeeper and, critically, no keys to the cages.

The user's brief, stated as casually as if it were a small thing:

1. Find out what local inference tools this Windows install actually has.
2. Get the models in `C:\ai\models` running locally.
3. Make the pieces talk to each other.

At first glance the answer was "profit" at the end of step one. It was not.

What this session actually produced: llama.cpp installed through scoop, LM Studio rebuilt around the models, an OpenAI-compatible server on port 1234, AnythingLLM rewired away from the cloud, an 18-gigabyte diet, and one domain migration that was hiding in plain sight.

## 2. Background (or: The Windows Zoo and Its Feeders)

`C:\ai\models` is the Windows mirror of the homelab model library, and it was already set up in per-model bungalows (a habit inherited from the 2026-09-06 rehousing on the NixOS side):

| model | size |
|---|---|
| `gemma3n` | 7.03 GB |
| `ornith-9b` | 5.24 GB |
| `gemma-4-E4B` (Q4_K_M + mmproj) | 4.97 + 0.92 GB |
| `translategemma` | 3.07 GB |
| `qwen3-vl` | 3.07 GB |
| `qwen3` (4b) | 2.33 GB |
| `qwen2.5-3b` | 1.80 GB |
| `starcoder2-3b` | 1.59 GB |
| `vibevoice` | 1.58 GB |
| `qwen2.5-1.5b` | 1.04 GB |
| `deepseek-r1-1.5b` | 1.04 GB |
| `mxbai-embed-large` | 0.62 GB |
| `tinyllama` | 0.59 GB |
| `nomic-embed-text` | 0.26 GB |

Total: about 35 GB of GGUF, on a machine with 15.7 GiB of RAM and an Intel UHD iGPU - CPU-only inference, the same landlord situation as the homelab.

The machine already had three local-AI-adjacent tools installed but disconnected:

- **LM Studio** (`C:\Users\SIGIT\AppData\Local\Programs\LM Studio`) - installed, running, with a `models` folder full of **broken symlinks** into `C:\ai\models`.
- **AnythingLLM** (`C:\Users\SIGIT\AppData\Local\Programs\AnythingLLM`) - installed, but pointed firmly at the cloud (Novita) and at the homelab LiteLLM proxy.
- **llmfit** 0.9.37 (scoop) - a model-fit/recommend/download tool whose `run` subcommand requires `llama-cli` or `llama-server` on PATH. Neither existed.

## 3. Problem (or: Fourteen Friends and No Party)

1. **No runtime.** `ollama` was absent (not on PATH, not running). Ninja evidence: `llmfit` had been installed precisely to *launch* inference, but it asks for `llama-cli` in PATH and there was none. The models were usable only by dragging files around.
2. **LM Studio's model folder was haunted.** `~/.lmstudio/models/ollama/` and `~/.lmstudio/models/OBLITERATUS/` contained symlinks whose targets pointed at flat paths that never existed (`C:\ai\models\qwen3-4b.gguf` instead of `C:\ai\models\qwen3\qwen3-4b.gguf`). LM Studio's model index was full of `ENOENT` errors for exactly those files, so `lms ls --llm` returned an empty array while the GUI silently pretended the zoo was empty.
3. **AnythingLLM was pointed at the sky.** `LLM_PROVIDER='novita'` with a Novita API key - cloud-first by default, silence on the local models.
4. **Too many elephants for one cage.** On 15.7 GiB of RAM, the 7 GB `gemma3n` and 5+ GB `ornith-9b` were not going to be "playful", they were going to be "swap file." The zoo needed a diet.

## 4. Work Performed

### 4.1 Inventory (or: What Do We Actually Have Here?)

Model audit of `C:\ai\models`: 14 GGUF files plus a `manifest.json.bak` (10 entries, old flat-layout manifest, sha256s matching the model blobs). Scoop shims showed `llmfit.exe`. LM Studio's CLI (`C:\Users\SIGIT\.lmstudio\bin\lms.exe`) reported the backend was alive (internal API on port 41343) with the HTTP server config set to `127.0.0.1:1234`, `autoStartOnLaunch: false`.

LM Studio's model folder inspection confirmed the diagnosis: the `ollama` and `OBLITERATUS` subtrees were 10 symlinks, every single one of them resolving to a non-existent flat target.

### 4.2 llama.cpp, Installed the Scoop Way

`versions/llama.cpp-cpu` was not in any installed bucket, and a `scoop bucket add versions` fetch kept timing out. The bypass: install the manifest directly from the Versions bucket's raw URL.

```powershell
scoop install https://raw.githubusercontent.com/ScoopInstaller/Versions/master/bucket/llama.cpp-cpu.json
```

Result: `llama.cpp-cpu` b10868 (commit `304665fe7`, built with Clang 20.1.8 for Windows x86_64). Full binary set shimmed, including `llama-cli.exe`, `llama-server.exe`, `llama-bench.exe`, `llama-quantize.exe`. Version check: `0.4.0-dev`. `llmfit run <model>` now has its prerequisite.

### 4.3 LM Studio, Rehoused (or: Import All the Things, but Do Not Move Them)

`lms ls --llm` said "everything is fine, we have nothing." The fix that avoided restarting the running app and avoided an admin-prompted symlink: `lms import` with **hard links** (`-L`), which keeps the original files in place and takes no extra disk - exactly the right tool for a library already living on the same volume.

```powershell
lms import -y -L "C:\ai\models\qwen2.5-1.5b\qwen2.5-1.5b.gguf"
```

One model in, verify, then loop the remaining 13. Import even resolved HF naming for a few (`qwen3-4b-instruct-2507-rewriter`, `emotional-assistant_tinyllama`, `dango-translategemma`, `vibevoice-realtime-0.5b`) and rejected the gemma vision projector with `Target file already exists` because the broken symlink had claimed the name first.

Post-import inventory: **12 LLMs + 3 embeddings** indexed as `Local`, all hard-linked, zero extra disk.

Then the server, for real this time:

```powershell
lms server start --port 1234   # Success! Server is now running on port 1234
lms load qwen2.5-3b -y         # Model loaded successfully in 5.09s (1.80 GiB)
```

First round-trip through the OpenAI-compatible API:

```text
POST http://127.0.0.1:1234/v1/chat/completions
{ "model": "qwen2.5-3b", "messages": [{"role":"user","content":"Reply with exactly: LM Studio works"}] }
-> "LM Studio works"
```

`/v1/models` listed all 15 models. The Windows zoo had a door again.

### 4.4 AnythingLLM, Repointed

AnythingLLM's backend reads `storage/.env` at boot ("Auto-dump ENV"). The .env backup landed as `.env.bak-novita`, then four lines changed:

```dotenv
LLM_PROVIDER='lmstudio'
LMSTUDIO_BASE_PATH='http://127.0.0.1:1234'
LMSTUDIO_MODEL_PREF='qwen2.5-3b'
LMSTUDIO_MODEL_TOKEN_LIMIT='8192'
```

(Confirmed against the installed bundle: AnythingLLM origin-strips `LMSTUDIO_BASE_PATH` and appends `/v1` itself, so the URL has no `/v1` suffix - and its settings validator would reject the slash-ending form.)

AnythingLLM itself was not running, so the changes take effect at next launch. Cloud-first became local-first by default.

### 4.5 The Diet (or: Three Elephants Leave the Building)

User's call and it was the right one: on a CPU-only 15.7 GiB box, the heavy hitters were decorative. Deleted from `C:\ai\models` **and** their LM Studio hard links (both must go to actually free disk):

| model | freed |
|---|---|
| `gemma3n` | 7.03 GB |
| `ornith-9b` | 5.24 GB |
| `gemma-4-E4B` (both files) | 5.89 GB |

**~18.2 GB** recovered. The two haunted symlink folders (`models\ollama`, `models\OBLITERATUS`) were verified 10-for-10 broken against their real targets and cleared out. `lms ls --llm` dropped from 12 to 9 models all on its own - no restart, no index surgery. Disk free on C: at end of session: 256.22 GB.

### 4.6 The Domain Migration That Was Hiding in Plain Sight

The user's note: "lmstudio still uses the old URL `litellm.home.arpa`, which has moved to `ai.home.arpa`." And indeed - per the 2026-09-09 homelab session, `litellm.home.arpa` was retired and folded into `ai.home.arpa`.

But the sweep told a different story. `rg` across every live config in `~/.lmstudio` and the opencode hub: **zero** `litellm.home.arpa` references. LM Studio had never pointed at the proxy at all. The one live holder of the retired URL was AnythingLLM's `.env`:

```dotenv
LITE_LLM_BASE_PATH='https://litellm.home.arpa'  # before
LITE_LLM_BASE_PATH='https://ai.home.arpa'       # after
```

The misattribution was harmless and the fix was the same: one line, one file, done. Verified no live `litellm.home.arpa` remains on the box.

## 5. Verification (or: Proof, Not Vibes)

- `llama-cli --version` / `llama-server --version` -> `0.4.0-dev (build 10868, commit 304665fe7)`, working PATH shims.
- `lms ls --llm` -> 9 models; `lms ls --embedding` -> 3 models. All `Local`.
- `lms ps` -> `qwen2.5-3b` IDLE, 1.93 GB, context 32768.
- API round-trip on port 1234 returned the expected exact phrase.
- `/v1/models` -> 15 entries (12 chat + 3 embedding).
- After diet: models total 16.99 GB, disk free 256.22 GB.
- `rg litellm.home.arpa` across live configs -> nothing (exit 1 = clean).

## 6. Results (or: The Magic Numbers)

| before | after |
|---|---|
| 14 GGUFs, no runtime | 9 LLMs + 3 embeddings, served on `:1234` |
| `ollama`/llama-cli missing | `llama.cpp-cpu` b10868 installed (scoop) |
| LM Studio index: ENOENT everywhere | 12 local models indexed via hard links |
| AnythingLLM on Novita cloud | AnythingLLM on LM Studio local, `qwen2.5-3b` |
| ~35 GB of models | ~17 GB (18 GB diet) |
| `LITE_LLM_BASE_PATH=litellm.home.arpa` | `ai.home.arpa` |

The surviving lineup: `translategemma`, `qwen3-vl`, `qwen3-4b`, `starcoder2-3b`, `vibevoice`, `deepseek-r1-1.5b`, `qwen2.5-3b`, `qwen2.5-1.5b`, `tinyllama`, plus `mxbai-embed-large`, `nomic-embed-text`, and the bundled Nomic v1.5 embedder.

## 7. Recommendations

1. **LM Studio + hard links is the right pattern for `C:\ai\models`.** `lms import -L` indexes the models without copying them and without needing admin (symlinks on Windows usually do). When life gives you a pre-existing library, hard-link it.
2. **Delete from both sides.** A hard link is a second name for the same data; removing only the source file just orphans the viewer. Delete the `C:\ai\models` file and the `~/.lmstudio/models/SIGIT/...` link together to actually reclaim space.
3. **The 15.7 GiB ceiling is real.** The leftover roster (max 3.3 GB per file) is the sensible ceiling for this box. If a bigger model ever lands, budget RAM for it at swap-file prices.
4. **`llmfit run` only needs `llama-cli`.** With llama.cpp in PATH, `llmfit run C:\ai\models\qwen2.5-3b\qwen2.5-3b.gguf --server --port 8080` works as an alternative door to LM Studio.
5. **The domain migration is a file-grep event, not an assumption.** `litellm.home.arpa` still smiles from backup files and old tasks; when in doubt, `rg -rn` the live configs and let the evidence pick the target.
6. **AnythingLLM settings live in `storage/.env`, not the GUI alone.** Back up before hand-editing; the file is auto-dumped at boot.

## 8. Open Questions and Follow-Ups

- **AnythingLLM activation** is pending a launch: the `.env` changes (LM Studio provider + `ai.home.arpa`) take effect at next start.
- **`qwen2.5-3b` vs `qwen2.5-1.5b`** - the middle-tier comparison that keeps getting deferred (this time both are loaded into LM Studio, so the evidence is finally local).
- **Vibevoice** (voice realtime, 1.58 GB) and **translategemma** (3.1 GB) are on the roster but unproven on this box; both survived the diet, both deserve a round-trip.
- **Do the embeddings get used?** `mxbai-embed-large` and `nomic-embed-text` are indexed but AnythingLLM's embedding engine was left on `native` (Xenova) - a future session can decide whether the local GGUF embedders earn their 934 MB rent.

---

Generated by Big Pickle (OpenCode)