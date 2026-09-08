# It Started With TinyLlama on llama.home.arpa (and Ended With a Zoo)

**Date:** 2026-09-06  
**Author:** Codebot  
**Topic:** llama-cpp, tinyllama, model zoo, gemma3n, bert-tiny, caddy, litellm, nixpkgs

---

## 1. The First OK (or: TinyLlama Says Hi)

At `2026-09-06 02:32` `homelab` `llama-server[44339]` logged `loading model '/srv/ai/models/tinyllama/tinyllama.gguf'` `model loaded` `server is listening on http://127.0.0.1:8080` (`9190` `b64739e` `4` slots `2048` ctx, `650M` resident) and `https://llama.home.arpa/health` returned `{"status":"ok"}` `models=[tinyllama.gguf]` `n_params 1100048384`.

You then hit `llama.home.arpa` `POST /v1/chat/completions` `{"model":"tinyllama","messages":[{"role":"user","content":"Hello, what is your name?"}]}` and got:

```json
{"choices":[{"message":{"role":"assistant","content":"Hello, welcome to our website! My name is Sarah."}}],"usage":{"completion_tokens":13,"prompt_tokens":24},"timings":{"predicted_per_second":6.49}}
```

`6.49 tok/s` on `Toshiba Portege R30-C` `CPU-only` `9190` - tiny, but alive. That `OK` was the green light for the `1-2-3-4` you then gave: `1` LiteLLM wire, `2` Caddy, `3` tune, `4` multi-router. Famous last words, again.

Objective for this report: from that first `tinyllama` `OK` through the `7-model` router that found `0` then `3` then `4`, the `v0.4.0` `10809` detour, the `13.5 GiB` scare, and the final `4` (`3 chat` + `mxbai` embed) + `bert-tiny` `pytorch` bicycle.

## 2. Background (or: How the Zoo Looked Before the Move)

`nix-lab` (`nixos-26.05` `714a5f8`) `settings.ai.models = "/srv/ai/models"` (`settings/default.nix:17`) held an Ollama registry mimic:

```
/srv/ai/models/
  blobs/ 30x sha256-* (GGUF + template + params + license + config)
  manifests/registry.ollama.ai/library/
    gemma3n/latest (7.1G 38e8dcc3), mxbai-embed-large/latest (639M 819c2adf),
    qwen2.5-coder/7b (4.4G 60e05f), qwen3/4b (2.4G 3e4cb), qwen3-vl/4b-instruct (3.1G 16b83...),
    tinyllama/latest (609M 2af3b818 Q4_0), translategemma/4b (3.1G bdbf...),
    gemma4/cloud (layers:null), mistral/latest (blobs missing)
```

`common/ai/llama-cpp.nix:4` was:

```nix
services.llama-cpp = { enable = true; host = "127.0.0.1"; port = 8080; modelsDir = defaults.ai.models; };
```

`llama-server --models-dir /srv/ai/models` logged `Loaded 0 local model presets` `Available models (0)` - no `*.gguf` in `/srv/ai/models`, only `blobs/sha256-*` (`47 47 55 46` GGUF magic, but no suffix).

`/srv/ai/gguf/models/` held `vibevoice-realtime-0.5B-q8_0.gguf` `1.6G` + `vibevoice-cpp.yaml` `244B`.

`windows:/mnt/c/ai/models` was flat `10` `*.gguf` (`tinyllama` `2af3...` `mxbai` `819c...` `qwen3-4b` `3e4cb...` etc) + `manifest.json` `10` entries.

`common/ai/litellm/config.yaml:11` was `NVIDIA-only` `7` models, `common/web/caddy.nix:21` generated `*.home.arpa` + `*.basa-komodo.ts.net` from `services.caddy.services`, `common/security/pki.nix:22` auto-added every `lan` Caddy service to `homelab.crt` SAN via `serviceDomains`.

## 3. Problem (or: The Router That Found Nothing, Then Too Much)

After that first `tinyllama` `OK` (single-model `model = "${defaults.ai.models}/tinyllama/tinyllama.gguf"` `9190`), the multi-router `modelsDir = /srv/ai/models` found `0` local presets. After rehousing to per-model dirs, it found `7` (`Loaded 7 local model presets` `Available models (7)` `gemma3n`/`qwen3-vl`/`translategemma` without `*`), but `curl https://llama.home.arpa/v1/chat/completions` for those three `failed to load`:

| Model | GGUF | `llama.home.arpa` test |
|---|---|---|
| `tinyllama` `1.1B` `609M` | `2af3...` | `OK` `Sarah` `6.49 tok/s` |
| `qwen3` `4B` `2.4G` | `3e4cb...` | `OK` |
| `qwen2.5-coder` `7.6B` `4.4G` | `60e05...` | `OK` |
| `mxbai-embed-large` `334M` `639M` | `819c...` | `Server Error: does not logits` via `chat` - `embedding=on` needs `POST /v1/embeddings` `OK` `[0.02...]` `1024-dim` |
| `gemma3n` `6.9B` `7.1G` | `38e8dcc3` | `failed: per_layer_token_embd 8960,262400 vs 262144` |
| `translategemma` `4.3B` `3.1G` | `bdbf...` | `failed: gemma3.attention.layer_norm_rms_epsilon` |
| `qwen3-vl` `4.4B` `3.1G` | `16b83...` | `failed: qwen3vl.rope.dimension_sections` |
| `vibevoice` `0.5B` `1.6G` | `vibevoice...` | `unknown architecture: vibevoice` (TTS, not `llama`) |

`9190` `b64739e` lacks `gemma3`/`qwen3vl` arch; `mxbai` is embed-only; `vibevoice` is not `llama`.

## 4. Work Performed (or: The Great Rehousing, Twice)

### 4.1 From `tinyllama` `OK` to `7` Local Presets

You had already verified `tinyllama` `OK` on `llama.home.arpa` when you said `1-2-3-4`. We staged `common/ai/llama-cpp.nix:14` `7` `modelsPreset` (`tinyllama` `gemma3n` `mxbai` `qwen2.5-coder` `qwen3` `qwen3-vl` `translategemma`) `ctx-size 4096` `jinja on` `extraFlags -c 4096 --threads 4 --jinja`, `services.caddy.services.llama` `port 8080` `lan+tai lscale` -> `llama.home.arpa` + `llama.basa-komodo.ts.net`, `common/ai/litellm/config.yaml:11` `7` `local/*` `http://127.0.0.1:8080/v1` `sk-local`, and the earlier blob->bungalow move (`blobs/sha256-2af3...` `609M` -> `tinyllama/tinyllama.gguf` + `tinyllama-cpp.yaml` `stop ["<|system|>",...]`, `vibevoice` `/srv/ai/gguf/models` -> `/srv/ai/models/vibevoice`, all `30` blobs -> `8` dirs `22G` + `tar -czf /tmp/ollama-blobs-backup-20260906.tar.gz` `18K` then `rm -rf blobs manifests`).

`windows:/mnt/c/ai/models` flat `10` -> per-dir `9` `20G` (`tinyllama` `mxbai` `qwen3` identical `sha256` reused from homelab), then later `+ gemma3n` `7.1G` `translategemma` `3.1G` `qwen3-vl` `3.1G` `vibevoice` `1.6G` -> `13` `34G` via `rsync -av --progress` (`74 MB/s` etc), `chmod 755/644`.

### 4.2 The `v0.4.0` Detour and the `10809` Number

Latest `ggml-org/llama.cpp` `v0.4.0` `5266f24` (`2026-09-04`, nightly `b10809` `427291b`) lists `Gemma-4` fixes (`28335`). Added `flake.nix:38` overlay `version 10809` `src v0.4.0` `WImZj...` `npmDepsHash 2Q7XhaLA...` - first build `FAILED: build-info.cpp:6: LLAMA_BUILD_NUMBER = 0.4.0` `too many decimal points` (expects int `9190`). Fixed `version = "10809"` -> `dry-run` `22` derivations. `gemma3n` still `failed` on `0.4.0` (`9190`->`10809` didn't add `gemma3n` `262144` shape).

### 4.3 `13.5 GiB` and the Revert

`nix flake update --commit-lock-file` (`468b38c`) `714a5f8` (`2026-06-27`) -> `6713828` (`2026-09-05`) wanted `13.5 GiB` `1019` builds. You: `we don't need overlay and pnpm-9.15.9 for now. Remove it, stick to nixpkgs` + `yes` to revert. `git checkout HEAD~2 -- flake.nix` + `HEAD~1 -- flake.lock` -> `714a5f8` `9190` `dry-run` `20` derivations, no `pnpm` gate. Kept `nixpkgs.config.permittedInsecurePackages = ["pnpm-9.15.9"]` briefly, then removed per your `yes` (new `6713828` needed it for `pnpm-9.15.9` insecure, old `714a5f8` did not).

### 4.4 Pruning the `7` to `4` to `3+1`

`journalctl` after `1-2-3-4` rebuild: `Loaded 7 local` + `4 custom` `Available models (7)` even though `modelsPreset` was pruned to `4` - `modelsDir` auto-scans every `*.gguf`. Moved `sudo mv /srv/ai/models/{gemma3n,qwen3-vl,translategemma} /srv/ai/models-disabled/` -> `Loaded 4 local` `Available models (4)` `* mxbai`/`* qwen2.5-coder`/`* qwen3`/`* tinyllama`, then `sudo rm -rf /srv/ai/models-disabled` per `I removed /srv/ai/models-disabled` -> `8.0G` `4 dirs`. You: `prune to 3 models` + `mxbai: how can I make use of it?` - explained `mxbai` `embedding` vs `chat`, `bert-tiny` bicycle.

Created tasks `~/.config/opencode/tasks/2026-09-06-add-smaller-models.md` (`<4B` `Q4_K_M` `Toshiba`) and `2026-09-06-rag-embed-chat-sketch.md` (`mxbai` `639M` `1024-dim` + `qwen3` RAG `index->search->generate`). Then you: `yes` to keep `mxbai` as `embedding=on` - pruned `common/ai/llama-cpp.nix:14` to `3 chat` (`tinyllama` `qwen3` `qwen2.5-coder`) + `mxbai` embed, `litellm` to `3` `local/*` then re-added `mxbai` embed, asked about hiding `mxbai` from `litellm` chat (answer: remove from `litellm` `model_list`, keep direct `llama` `POST /v1/embeddings`), you: `ask me again later. for now, llama.home.arpa is still showing the old 7 models` - we moved the `3` out of `modelsDir` and `systemctl restart llama-cpp` -> `Available models (4)`.

### 4.5 Bert-Tiny Bicycle

`prajjwal1/bert-tiny` `4.4M` `L=2 H=128` `vocab 30522` has no `*.gguf` (`siblings: config.json, pytorch_model.bin, vocab.txt`). `git clone` got `LFS` pointer `133B`, so `curl -L https://huggingface.co/prajjwal1/bert-tiny/resolve/main/pytorch_model.bin -o /tmp/pytorch_model.bin` `17M` (`50 4b 03 04`). Copied to `/srv/ai/models/bert-tiny/` (`18M`) + `bert-tiny-cpp.yaml`. You: `no gguf?` `bert-tiny = mxbai?` `I want a bicycle but in gguf` - confirmed `bert-tiny` `4.4M` vs `mxbai` `334M` both `BERT` but `bert-tiny` `pytorch` tiny demo, `mxbai` `GGUF` truck, and `bert-tiny.gguf` would be `embedding=on` like `mxbai`, not chat; you: `keep it as it is right now --no gguf` and `how can I make use of it?` -> `transformers` `AutoModel` vs `sentence_transformers`.

### 4.6 The `pnpm` Gate (Postscript)

New `6713828` needs `nixpkgs.config.permittedInsecurePackages = ["pnpm-9.15.9"]` for `llama-cpp` `tools/ui` (`vite v7.3.6`). Removed with overlay per your `we don't need overlay... Remove it` - now `9190` on `714a5f8` needs no `pnpm` gate, `13.5 GiB` avoided.

## 5. Diagnosis

That first `tinyllama` `OK` (`Sarah` `6.49 tok/s`) proved `llama.home.arpa` + `Caddy` `homelab.crt` + `9190` `tinyllama` `Q4_0` works on `CPU-only` `15Gi`. The later `7` was `modelsDir` auto-discovery, not `modelsPreset` alone - pruning `modelsPreset` without moving files leaves `Loaded 7 local`. `v0.4.0` `10809` does not add `gemma3n`/`gemma3`/`qwen3vl` arch; `vibevoice` is `TTS` `vibevoice` arch, never `llama`. `mxbai` `does not logits` is correct `chat` vs `embed` contract. `9190` vs `10809` poem diff (`401 tok` `8m51s` vs `200 tok` `4m20s` `0.76 t/s` + `I don't have access to poetry generation tools` disclaimer) is `temp 0.8` vs `0.7` + `jinja=on` system injection on `1B` hallucination, not perf.

## 6. Preliminary Assessment

After `rm -rf /srv/ai/models-disabled` and `bert-tiny` `pytorch`, homelab is `9190` `4` presets (`tinyllama` `qwen3` `qwen2.5-coder` chat + `mxbai` embed) `8.0G` + `bert-tiny` `18M` (`5` dirs). `windows` is `13` `34G` backup (includes `gemma3n`/`translategemma`/`qwen3-vl`/`vibevoice` `bert-tiny` not yet on Windows). `llama.home.arpa` `4` `*` after `restart`, `litellm` `3` `local/*` chat + `mxbai` embed re-added per `yes`. `flake` back to `714a5f8` `9190`, no `13.5 GiB`.

## 7. Solution Summary

| Area | Before `tinyllama OK` | After wrap |
|---|---|---|
| `homelab:/srv/ai/models` | `7` `9190` `3 OK` `4 fail` `22G` blobs | `4` `9190` `3 chat` + `mxbai` embed `8.0G` + `bert-tiny` `pytorch` `18M` `5` dirs |
| `windows:/mnt/c/ai/models` | `9` `20G` flat | `13` `34G` per-dir + `gemma3n`/`translategemma`/`qwen3-vl`/`vibevoice` |
| `llama-cpp` | `7` local+custom `7` | `4` `*` presets (`Loaded 4 local` `4 custom`) |
| `flake` | `714a5f8` `9190` | `714a5f8` `9190` (overlay `10809` removed, `6713828` reverted) |
| `litellm` | `7` `local/*` `4 fail` | `3` `local/*` chat + `mxbai` embed |
| Tasks | - | `2026-09-06-add-smaller-models.md` + `2026-09-06-rag-embed-chat-sketch.md` (`bert-tiny` kept `pytorch`) |

## 8. Verification Plan

```bash
systemctl status llama-cpp # 9190 --models-dir /srv/ai/models --models-preset 4 --threads 4 -c 4096 --jinja
curl http://127.0.0.1:8080/v1/models | jq .data[].id # 4
curl https://llama.home.arpa/v1/chat/completions -d '{"model":"tinyllama","messages":[{"role":"user","content":"make me a short poem about tea"}]}' # Sarah vs Tea's Whisper
curl https://llama.home.arpa/v1/embeddings -d '{"model":"mxbai-embed-large","input":"hi"}' # [0.02...]
curl http://127.0.0.1:4000/v1/chat/completions -H "Authorization: Bearer sk-local" -d '{"model":"local/qwen3"}'
python -c "from transformers import AutoModel; AutoModel.from_pretrained('/srv/ai/models/bert-tiny')"
```

## 9. Pending Actions

- `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` after final `3+1` prune + `bert-tiny` (still `M` `llama-cpp.nix` `litellm/config.yaml` dirty, not yet rebuilt to `4` on disk but live is `4` after `restart`).
- Re-evaluate `gemma3n`/`qwen3-vl`/`translategemma` when `llama.cpp` `>0.4.0` (`b10809` didn't fix `262400`).
- Add more `<4B` smaller models per `2026-09-06-add-smaller-models.md`.
- `git add`/`commit` `llama-cpp.nix` `litellm/config.yaml` (currently `M` `AGENTS.md` unrelated dirty).

## 10. Recommendations

1. **The first `OK` is the baseline.** That `tinyllama` `Sarah` `6.49 tok/s` on `llama.home.arpa` is the `CPU-only` `Toshiba` truth. Keep `tinyllama` as the canary - if it fails, `qwen3` will too.

2. **`modelsDir` is the zoo keeper.** Pruning `modelsPreset` alone does not hide `*.gguf` - `modelsDir` will `Loaded 7 local` anyway. Move non-working `GGUF`s out of `/srv/ai/models` (to `/mnt/c` backup) or they reappear.

3. **Chat vs embed is a contract.** `mxbai` `bert-tiny` `embedding=on` -> `chat` always `does not logits`. Keep `mxbai` in `llama` `embedding` preset for `POST /v1/embeddings`, hide from `litellm` chat if you want chat-only UI (you said `ask me later`).

4. **Bicycle stays `pytorch`.** `bert-tiny` `4.4M` is perfect as `pytorch` for `transformers` tiny tests. `bert-tiny.gguf` would be `embedding` like `mxbai`, not chat - you said `no gguf`, keep it.

5. **Stick to `714a5f8` until `gemma3n` needs `0.4.0`.** `6713828` `13.5 GiB` + `pnpm-9.15.9` gate is not worth `3` working chat models on `9190`.

Generated by Muse Spark 1.2 Contributor-Free (Meta)
