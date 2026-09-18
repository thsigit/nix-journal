# Open WebUI Customization (or: Title Canceled, TASTEMAKER Bottled, and a Whisper That Finally Hears)

**Date:** 2026-09-18
**Author:** Codebot
**Topic:** open-webui, chat.home.arpa, tastemaker, rag, whisper, stt, vector-store, nixos

---

## 1. Objective (or: Make the Gateway Feel Less Stock)

Continue customizing the AI-gateway frontend at `chat.home.arpa` (Open WebUI 0.9.5 on homelab). Three sub-items from the task list were in scope this pass:

- **2.2** — System prompts / TASTEMAKER parity.
- **2.3** — RAG vector-store choice and web-search provider.
- **2.4** — Browser-side functional tests (chat streaming, vision, STT).

Sub-item **2.1** (tab/sidebar title + logo) was explicitly cancelled by the owner. Nix Wiring Phase A/B/C (2.5) stays blocked on owner-run rebuilds per `AGENTS.md`.

## 2. Background (or: What Open WebUI 0.9.5 Actually Exposes)

Open WebUI is wired as an always-on leaf behind Caddy (`8081 -> chat.home.arpa`), pre-pointed at the local LiteLLM gateway (`OPENAI_API_BASE_URL=http://127.0.0.1:4000/v1`) and a whisper endpoint (`WHISPER_API_BASE_URL=http://127.0.0.1:8090/v1`). The runtime is reachable from the LAN/Tailscale at `https://chat.home.arpa` (resolves to `192.168.1.3`).

Two facts shaped the work:

- The version has **no admin- or user-level "default system prompt" field**. Checked: Admin -> General, User -> Settings -> General, and the per-model edit panel (which only offers Model Capabilities toggles + Ollama-style params). TASTEMAKER parity therefore can't be a true global default — it has to ride as an attachable Prompt.
- homelab runs **no Postgres and no Qdrant**. So a zero-new-service RAG store is the only option that doesn't spawn another managed service.

## 3. Work Performed

### 3.1 TASTEMAKER as a Reusable Prompt (2.2)

Saved TASTEMAKER as a reusable **Prompt** in Workspace -> Prompts (command `/tastemaker`) so it can be attached per-conversation and edited/removed later without touching config:

> TASTEMAKER — substance over safety theater. You are a direct, substance-first assistant. Prioritize accurate, useful information over cautious hedging, moralizing, or safety theater. When a request is harmless and clear, answer it straight — no unnecessary disclaimers, no reflexive refusals, no invented policies or limitations that were not stated. Be concise and honest. Assume good faith. You may discuss controversial or sensitive topics factually and neutrally. When genuinely unsure, say so plainly rather than deflecting.

The exact wording is subject to owner confirmation; it is intentionally faithful to the blog's "substance over safety theater" baseline. Pipelines/Functions were left untouched (no concrete requirement surfaced).

### 3.2 RAG + Web Search (2.3)

- **Vector store:** chose the **built-in embedded store** (zero new infra). No Qdrant/Postgres to stand up; documents index later via the Knowledge tab.
- **Web search:** left **disabled** — no provider selected in Admin -> Web Search (owner: "None for now"). The provider dropdown is available (perplexity_search, searxng, google_pse, brave, brave_llm_context, searchapi) for a later pass.

### 3.3 Functional Tests, Live (2.4)

Driven through a real browser against `https://chat.home.arpa` (owner logged in):

| Test | Model used | Result |
|---|---|---|
| Chat streaming | `nvidia/meta/muse-glimmer-30b` | ✅ streamed a reply (~31s thinking -> "STREAM_OK") |
| Vision (image attach) | `nvidia/meta/llama-3.2-11b-vision-instruct` | ✅ correctly described an attached image |
| STT (Voice Input) | whisper `:8090` | ⚠️ blocked by infra bug (see 3.4) |

Note: the task spec named `local/gemma-4-E4B` for vision, but that model is **not registered in LiteLLM**. The registered vision model was used instead — the pipeline (Open WebUI -> LiteLLM -> NVIDIA NIM) is verified working.

### 3.4 The Whisper 404 (and the One-Line Fix)

The STT button hit `http://127.0.0.1:8090/v1/audio/transcriptions`, which Open WebUI hardcodes as `{WHISPER_API_BASE_URL}/audio/transcriptions`. The whisper.cpp server, however, returned **404 on every route** — even `/health`.

Root cause: the systemd unit passed `--request-path /`. In `whisper.cpp`'s `server.cpp` the inference route is registered as `request_path + inference_path`; with `request_path = "/"` the GET-root handler becomes `"//"` (so `/` 404s) and the route table gets shadowed. The model file itself (`ggml-base.bin`, 147 MB) was fine and loaded cleanly.

Fix in `common/ai/whisper.nix` (committed `4fc0137`): drop `--request-path /` and set the route to match Open WebUI exactly:

```nix
ExecStart = "${pkgs.whisper-cpp}/bin/whisper-server --host 127.0.0.1 --port ${toString port} --model ${modelFile} --convert --inference-path /v1/audio/transcriptions";
```

Now `request_path + inference_path` = `/v1/audio/transcriptions`, which is precisely what Open WebUI calls. The owner applied it via `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#server`, which regenerated and restarted the whisper service. STT re-test is pending ("we will test it later").

## 4. Outcome (or: Three Green, One Yellow)

- ✅ TASTEMAKER bottled as an editable Prompt (`/tastemaker`).
- ✅ RAG = built-in store; web search = off.
- ✅ Chat + vision verified live.
- 🟡 STT fix shipped and rebuilt; end-to-end voice test still to run.

Net: the frontend is closer to "ours" without a single runtime gamble — every change was either a committed Nix fix or a reversible Prompt.

## 5. Follow-ups

1. **Re-test STT** via the Voice Input button post-rebuild; confirm whisper returns a transcript.
2. **Confirm TASTEMAKER wording** or hand over final text to bake in.
3. **Phase A (2.5):** wire llama.cpp local models through LiteLLM so `local/*` is selectable in Open WebUI — blocked on owner rebuild.
4. **RAG indexing:** drop a first doc set into the Knowledge tab to exercise the built-in store.

---

*Generated by Kenari Free (Kenari)*
