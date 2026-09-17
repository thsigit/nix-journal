# Windows AI Zoo, Day Two: RAG Wiring, API Keys, and the Prune to Six

**Date:** 2026-09-10  
**Author:** Codebot  
**Topic:** windows, lm studio, anythingllm, local models, rag, lancedb, embeddings

---

## 1. Objective (or: The Cage Doors, Finally Unlocked)

Yesterday's session (2026-09-09) rebuilt the Windows zoo around LM Studio: llama.cpp installed, 18.2 GB of elephants evicted, AnythingLLM repointed at the local server on port 1234. The catch, as always: the lights were on but nobody had actually *asked a question through the whole pipeline* yet. The `.env` changes were sitting un-launched, the embeddings were still set to the built-in `native` engine, and most of the surviving models had never once touched a prompt.

Today's brief was the same shape as yesterday's, but louder:

1. Wire AnythingLLM to local embeddings and prove RAG works end-to-end on this box.
2. Actually test the middle-tier models instead of judging them from the package label.
3. Prune the roster to whatever earns its RAM.
4. One bonus question that came in mid-stream: can we generate images on this thing?

The honest answer to the last one is "we measured a very polite no." The rest, we got.

## 2. Background (or: Where We Left the Animals)

At the end of the diet, the LM Studio library held 9 LLMs and 3 embeddings, all hard-linked into `C:\ai\models`, served on `127.0.0.1:1234`. AnythingLLM's `storage/.env` had been edited to point `LLM_PROVIDER=lmstudio` with `qwen2.5-3b` as the chat model, but the app had not been launched since the edit, and the embedding engine was still `native` (Xenova), so the local GGUF embedders were technically indexed and entirely unemployed.

The previous post's "Open Questions" section was basically today's agenda: activation of AnythingLLM, the qwen duel, vibevoice's fate, and the embeddings question. Also present but unmentioned at the time: AnythingLLM decided to update itself mid-session, which rearranged its own furniture (the chat API moved). More on that in section 4.5.

## 3. Problem (or: The Ghost in the Vector Store)

1. **"LMStudio service could not be reached."** The moment embeddings were switched to the local LM Studio embedder, AnythingLLM refused to talk to it. The URL was right. The port was right. It still refused.
2. **RAG returned a country that was never mentioned.** Once embeddings worked, a query for the test document came back with context about Transnistria, a place nowhere in the corpus. Something in the vector store was not what the workspace claimed it was.
3. **Image generation: existence unconfirmed.** LM Studio's API surface is large; does `/v1/images/generations` exist on it? (Spoiler: no.)
4. **The roster was resting on assumptions.** `starcoder2-3b`, `qwen2.5-1.5b`, `deepseek-r1-1.5b` were all indexed and none of them had a proven job on a 15.7 GiB CPU-only box.

## 4. Work Performed

### 4.1 The Embedding Root Cause (or: BASE_PATH Is Not BASE_PATH)

AnythingLLM's `LMStudioEmbedder` reads **`EMBEDDING_BASE_PATH`**, not `LMSTUDIO_BASE_PATH`. The chat provider and the embedder are wired by different variables, and the embedder's was still pointing at the dead Ollama port from a previous life:

```dotenv
# before
EMBEDDING_BASE_PATH='http://127.0.0.1:11434'   # the ghost of Ollama

# after
EMBEDDING_ENGINE='lmstudio'
EMBEDDING_MODEL_PREF='text-embedding-mxbai-embed-large'
EMBEDDING_BASE_PATH='http://127.0.0.1:1234'
```

One line was the whole mystery. Backups (`storage/.env.bak-*`) were taken before editing, per house rules. Embeddings immediately worked against `mxbai-embed-large` served by LM Studio.

### 4.2 Image Generation: A Polite No

Direct probe against the LM Studio server:

```text
POST /v1/images/generations
-> {"error":"Unexpected endpoint or method. (POST /v1/images/generations)"}
```

LM Studio does not implement image generation, full stop. Meanwhile the AnythingLLM bundle carries image-generation machinery (`/img` slash command, `IMAGE_GEN_*` env keys, image cards), and its provider set is:

| provider | local? | notes |
|---|---|---|
| OpenAI (DALL-E) | no | API key |
| OpenRouter | no | cloud, has free/cheap Flux |
| LocalAI | yes | SDXL on CPU, OpenAI-compatible |
| Ollama | yes | `bmad-sdxl` / flux |
| Lemonade | yes | vLLM desktop (Flux) |

The user's verdict: **skip image generation for now**. The door is documented and wired in AnythingLLM; opening it later is an env-key change, not a rebuild.

### 4.3 starcoder2-3b: Second Opinion (or: The Verdict Stands)

Yesterday starcoder2-3b delivered code-flavored mumbling that ignored a one-line instruction. Defensible this time, a proper system prompt:

```json
{"role":"system","content":"You are a code completion engine. Respond with code only, exactly one line."}
{"role":"user","content":"Write one line of Python that prints hello."}
```

Result, verbatim the important part:

```text
AI: 2

Instruct: You are a code completion engine. Respond with code only, exactly one line.
Human: Write
```

`finish_reason: length` at 64 tokens. The model cloned the prompt and kept typing. Its chat template on this GGUF is effectively broken. Verdict confirmed: starcoder2-3b is a code-completion engine that cannot take instructions.

### 4.4 The Vector Store Resurrection (or: Exorcising Transnistria)

The workspace `assistant-chats` listed exactly one uploaded document (`codex-alpha-notes.txt`, one chunk). The vector retrieval was returning unrelated content anyway. Diagnosis: the LanceDB namespace still contained vector rows belonging to documents that had been deleted through the app - the workspace list looked clean while the vector table held souvenirs.

Reset per workspace (also wipes the doc rows in this build, so re-upload after):

```text
DELETE /api/workspace/assistant-chats/reset-vector-db   -> 200
POST   /api/workspace/assistant-chats/upload-and-embed  -> docId 248a829a-164e-4f83-8f89-c580f35d5fd1
GET    /api/system/system-vectors                      -> {"vectorCount":1}
```

`vectorCount: 1` is the whole proof: one chunk in the store, none of it Transnistria.

### 4.5 The API Key Rite of Passage (or: Why Everything Moved to /api/v1)

The app update struck mid-session: the legacy `POST /api/workspace/assistant-chats/chat` route returned 404. The chat endpoint lives at `/api/v1/workspace/:slug/stream-chat` now, and the v1 layer demands authorization while the legacy layer did not.

Attempt one, `POST /api/request-token`, exploded:

```text
Illegal arguments: undefined, string
  at Object.hashSync (bcryptjs umd/index.js:205:15)
```

The token route is built for multi-user login and crashes in single-user mode (bcrypt gets an undefined salt). Wasted one address book on that.

Attempt two, the actual supported path:

```text
POST /api/system/generate-api-key
-> {"apiKey":{"id":1,"secret":"<redacted>",...},"error":null}
```

`Authorization: Bearer <apiKey>` on the v1 routes worked immediately. (The secret stays redacted here; it is a live credential, rotate it when testing is done.)

### 4.6 The qwen Duel (or: 1.5b vs 3b, Judged by a CPU)

Four prompts, temperature 0, no context, same server. qwen2.5-1.5b (1.12 GB) vs qwen2.5-3b (1.93 GB):

| prompt | qwen2.5-1.5b | qwen2.5-3b |
|---|---|---|
| 17*23 -> single number | 391 (0.9s) | 391 (1.5s) |
| ID->EN translate | correct, rambled to 128 tok (`length`) | correct, stopped at 19 tok (`stop`) |
| 3 tropical fruits, one per line | "1. Mango 2. Pineapple 3. Papaya" | "Pineapple Mango Guava" |
| 2+2 -> single digit | 4 | 4 |
| generation throughput | ~19.7 tok/s | ~5.8 tok/s (~3.4x slower) |

Both are factually correct on the simple stuff. The 3B is clearly better where it hurts - it obeys termination and compresses its answers. The 1.5B rambles off the instruction boundary. And on this box, the 3B's only "loss" (speed) largely evaporates in real RAG traffic, where a ~1,900-token context dominates wall time; the speed edge is best measured in single-turn grunts, not in anything that matters.

### 4.7 The Great Prune (or: Down to Six, No Regrets)

Deletions applied to both sides (canonical `C:\ai\models` file and the LM Studio hard link) plus the `.internal` config cache, the two-sides rule from yesterday:

| model | size | reason |
|---|---|---|
| `deepseek-r1-1.5b` | 1.12 GB | CoT chat took ~60s/turn; AnythingLLM switched off it |
| `qwen2.5-1.5b` | 1.12 GB | lost the duel; tinyllama owns the fast slot |
| `starcoder2-3b` | 1.71 GB | cannot follow instructions; qwen2.5-3b covers code |

Library went `9.24 -> 8.12 -> 7.01 -> 5.30 GB` as each went out. The workspace chat model was switched to the winner before the old one was deleted:

```text
POST /api/workspace/assistant-chats/update
{"chatModel":"qwen2.5-3b"}
-> chatProvider=lmstudio, chatModel=qwen2.5-3b
```

## 5. Verification (or: Proof, Not Vibes)

- `GET /api/system/system-vectors` -> `{"vectorCount":1}` after reset + re-embed.
- RAG chat round-trip on the clean store (before the switch, still on deepseek): answer names `ZIGGURAT42`, **sources = exactly one** (`codex-alpha-notes.txt`, score 0.5155), metrics: LMStudioLLM, 117 completion tokens, 63s, 1.86 tok/s.
- After the switch: `POST /api/v1/workspace/assistant-chats/stream-chat` -> "RAG OK", model `qwen2.5-3b`, provider `LMStudioLLM`, 1,891 total tokens.
- `lms ls` -> 6 models / 5.30 GB: LLMs `emotional-assistant_tinyllama`, `qwen2.5-3b` (loaded), `vibevoice-realtime-0.5b`; embeddings `text-embedding-mxbai-embed-large` (loaded), `text-embedding-nomic-embed-text`, `text-embedding-nomic-embed-text-v1.5`.
- Disk free on C: at end: 254.10 GB.
- `manifest.json.bak` (stale import manifest from the hard-link session) removed as leftover.

## 6. Results (or: The Magic Numbers)

| item | before (yesterday) | after (today) |
|---|---|---|
| AnythingLLM embedding engine | `native` (Xenova) | `lmstudio` + `mxbai-embed-large` |
| RAG store | stale LanceDB vectors contaminating retrieval | 1 vector, verified single-source answer |
| Chat API | legacy `/api/workspace/:slug/chat` | `/api/v1/workspace/:slug/stream-chat` + API key |
| Workspace chat model | deepseek-r1-1.5b (CoT, ~60s) | qwen2.5-3b |
| LLM library | 9 LLMs | 4 LLMs (after 3 deletions + 1.5b kept then cut) -> **3 LLMs** |
| Total models | 9.24 GB | 6 models / 5.30 GB |
| Image generation | unverified | measured: LM Studio = no; AnythingLLM = yes (skipped) |
| Benchmarked models | 2 (qwen family), claimed not proven | 2 (with throughput + quality evidence), 1.5b retired |

The surviving lineup: `qwen2.5-3b`, `emotional-assistant_tinyllama`, `vibevoice-realtime-0.5b`, plus `mxbai-embed-large`, `nomic-embed-text`, and the bundled Nomic v1.5 embedder.

## 7. Recommendations

1. **AnythingLLM embedders and chat providers read different env keys.** `EMBEDDING_BASE_PATH` does not inherit `LMSTUDIO_BASE_PATH`. Keep them both explicit and consistent, or the embedder points at a ghost port and says so only as "service could not be reached."
2. **After deleting documents, reset the workspace vector store.** `reset-vector-db` clears the LanceDB namespace; verify with `system/system-vectors` (vectorCount should match documents, not memories of them). Expect a re-upload to follow - the reset takes the doc rows with it in this build.
3. **Pin the chat model per workspace explicitly.** The `qwen2.5-3b` override survived the app update and the model deletions without complaint. If it had been left on deepseek, the box would still be doing 60-second CoT replies to "what is 2+2".
4. **Prune rule for this machine: the model must follow instructions.** A code-completion model that echoes its prompt and a reasoning model that costs a minute per turn do not earn RAM on a 15.7 GiB CPU-only box. `qwen2.5-3b` covers both niches; `tinyllama` is the fast token.
5. **API keys and secrets.** The v1 API key (id 1) is a live credential; expire or rotate it once the RAG testing is done. Never paste the secret into a report.
6. **Image generation is an env-key away, not a rebuild.** LM Studio cannot do it today. LocalAI (SDXL), Ollama (`bmad-sdxl`), or Lemonade all plug into AnythingLLM via the `IMAGE_GEN_*` keys when/if the mood strikes.

## 8. Open Questions and Follow-Ups

- **Vibevoice** (1.70 GB) is still the reserved resident: a voice-realtime model with no chat tier. Its round-trip remains a future-experiment item.
- **Rotate/expire the AnythingLLM API key** (id 1) when the author gets tired of it.
- **RAG tuning**: `topN=4`, `similarityThreshold=0.25`, and a single-chunk corpus means retrieval is quiet today. Revisit thresholds when the corpus grows beyond one txt file.
- **`nomic-embed-text-v1.5` vs `mxbai-embed-large`** for the embedding house model - mxbai is winning by default deployment, not by duel.
- **Index refresh**: the docs index is hand-maintained; this post joined the repo but has not been linked into `index.md` yet.
- AnythingLLM's own update cycle moved routes under `/api/v1` mid-session; its next self-update may move the furniture again.

---

Generated by Big Pickle (OpenCode)