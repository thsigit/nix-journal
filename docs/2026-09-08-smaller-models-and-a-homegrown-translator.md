# Smaller Models, One Real Translator (and a Download That Needed a Rescue)

**Date:** 2026-09-08  
**Author:** Codebot  
**Topic:** llama.cpp, nix, litellm, huggingface, models, translation

---

## 1. Objective (or: What Are We Even Doing Here?)

The homelab llama.cpp router was a tidy, pruned zoo: three chat models (`tinyllama`, `qwen3`, `qwen2.5-coder`), one embedding model (`mxbai-embed-large`), and one vision model (`gemma-4-E4B`). All of them admitted to the model-preset club through `services.llama-cpp.modelsPreset` and their proxy twins under `local/*` in LiteLLM.

This session's brief (task file `2026-09-06-add-smaller-models.md`) was to make the box friendlier:

1. Add a small, fast general-purpose chat model that did not feel like `tinyllama` watching the clock.
2. Give the homelab a real translation model for Indonesian, since "translate this" is the kind of request a multilingual house gets daily.

Two models in. One model out (spoiler: the user's heart belonged to Sailor2). Four commits, one inadvertently self-destructing shell, and a download that started at "maybe forty minutes" and ended at three.

## 2. Background (or: The Zoo and Its Constraints)

Hardware of record: a `Toshiba Portege R30-C`, 15 Gi of RAM, CPU-only inference. Every model runs through llama.cpp build b9190 (nixpkgs package, `llama.cpp` release dated 2026-05-16), one process per model, loaded on demand by the router. Inference speed is measured in single digits of tokens per second, and RAM is the real landlord.

Two configs live in parallel and MUST stay identical (the static-config contract from `2026-09-02`):

- **Live config**: `/srv/appdata/litellm/config.yaml` -- admin-edited, never re-rendered on rebuild.
- **Committed seed**: `/srv/repo/nix-lab/common/ai/litellm/config.yaml`.

Presets before this session (5):

| alias | file | role |
|---|---|---|
| `tinyllama` | `tinyllama/tinyllama.gguf` | fast, weak general chat |
| `qwen2.5-coder` | `qwen2.5-coder/qwen2.5-coder.gguf` | code |
| `qwen3` | `qwen3/qwen3.gguf` | multilingual general chat/reasoning |
| `mxbai-embed-large` | `mxbai-embed-large/mxbai-embed-large.gguf` | embeddings |
| `gemma-4-E4B` | `gemma-4-E4B/gemma-4-E4B-it-OBLITERATED-Q4_K_M.gguf` | vision (mmproj) |

## 3. Problem (or: What We Actually Wanted)

1. **A fast-but-competent general chat tier.** `tinyllama` is a 1.1B fossil; `qwen3` (4B) is good but slow on this CPU. The previous big pruning pass had already suggested `qwen2.5-1.5b` for "fast multilingual chat (better than tinyllama for Indonesian)".
2. **A translation model for llama.cpp.** This turned out to be a research question. Seq2seq translation families (NLLB-200, M2M-100, MADLAD-400, mT5) are architecturally dead on llama.cpp -- encoder-decoder support was dropped years ago. Decoder-only multilingual LLMs are the only game in town, and the bar for "runs here" is: supports arch on build b9190 and fits a 15 Gi box that already peaks around 11.4 Gi.

## 4. Work Performed

### 4.1 A Fast General-Purpose Buddy: qwen2.5-1.5b

From the Ollama-library candidate sweep, `qwen2.5-1.5b-instruct` won the fast-generalist slot. Download (Q4_K_M, 1.1 GiB):

- URL: `https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf`
- `sha256` `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`
- Landed at `/srv/ai/models/qwen2.5-1.5b/qwen2.5-1.5b.gguf` with a sibling `qwen2.5-1.5b-cpp.yaml` (family `qwen2`, `Q4_K_M`, ChatML template, matching `model_blob`).

Standalone round-trip on a temp port (same binary the router uses): reply `"ok"`, about 4 tok/s. Good enough to warrant a preset:

```nix
"qwen2.5-1.5b" = {
  model = "${defaults.ai.models}/qwen2.5-1.5b/qwen2.5-1.5b.gguf";
  alias = "qwen2.5-1.5b";
  ctx-size = "4096";
  temp = "0.7";
  top-p = "0.9";
  jinja = "on";
};
```

Plus a `local/qwen2.5-1.5b` entry in both LiteLLM configs, with `disable_background_health_check: true` (per the just-established convention from `40c131e`). Nix eval: 6 presets, clean.

### 4.2 The Download That Forgot to Download

The first pull of the next model (Sailor2, but we will get there) used a single `curl` through the Hugging Face xet CDN. Two minutes in, the file had grown by about 18 MiB. A quick sanity check on the homelab's actual WAN speed (8 MiB from Cloudflare in 1.44 s, ~5.8 MiB/s) revealed the culprit: **xet throttles single connections**. The estimate was ~45 minutes for 704 MiB. No thank you.

The official plan: kill it, split the file into 8 byte ranges, fire 8 parallel `curl -r` requests (each one re-resolves a fresh signed xet URL), concatenate in order, and verify total bytes. The unofficial plan included a `pkill -f` whose own command line contained the very pattern it was searching for.

Narrator: it was not the pattern's day.

The `pkill -f "curl.*sailor2"` regex matched the shell running the downloader script, because the script mentioned the same regex. The whole remote command died with "(no output)" and zero bytes of parallel magic. Lesson burned in: never `pkill -f` a string you also type, and kill by recorded PID (or via a `/proc` scan that excludes yourself). Order restored, the 8-range download ran: ~4.5 MiB/s aggregate, 704 MiB in about 3 minutes. `curl` exit codes all zero, final size exactly `738628320`.

### 4.3 Translation, the Hard Way

Survey before picking a model:

- Seq2seq (NLLB/M2M/MADLAD/mT5): unsupported on llama.cpp. Out.
- Decoder-only multilingual LLMs: viable. Shortlist: Qwen3 GGUF (already have the 4B), `translategemma` (needed a newer llama.cpp than the old overlay; that overlay is gone now), Aya Expanse, and **Sailor2** (Sea AI Lab, Apache-2.0).

Sailor2 won on fit: built on the **Qwen2.5 architecture** -- the same arch `qwen2.5-coder` already runs on b9190, so compatibility is a near-certainty -- and continuously pre-trained on 500B tokens to serve 15 languages including Indonesian, Javanese, Sundanese, Malay, Thai, Vietnamese. It is a translation/RAG machine for exactly this household. Sizes: 1B, 8B (L-8B), 20B. The 8B Q4 (~5 Gi) would blow the RAM budget alongside a loaded vision model; the **1B** is the responsible citizen.

User decision: **Sailor2-1B-Chat Q4_K_M**.

### 4.4 Enter Sailor2, the SEA Specialist

- URL: `https://huggingface.co/itlwas/Sailor2-1B-Chat-Q4_K_M-GGUF/resolve/main/sailor2-1b-chat-q4_k_m.gguf`
- 738,628,320 bytes; `sha256` `550823b1586ed4b4d1286d4b02c7818e64c475c1b1183b1774ecbaf5de611794`
- Landed in `/srv/ai/models/sailor2-1b/` (GGUF + `sailor2-1b-cpp.yaml`, family `qwen2`, `type 1B`, matching `model_blob`).

Standalone load on temp port 8094 (build b9190): vocab `151936` (Qwen2.5 tokenizer), `n_params` `988,064,640` (~1.0B), chat template loaded, server listening. Translation round-trip with an explicit translator system prompt returned:

> `Perpecahan Majapahit sebagai kerajaan sejarah terus diperdebatkan.`

at ~1.9 tok/s generation. The temp server was stopped and production confirmed untouched (`llama-cpp` and `litellm` active, `:8080/health` ok).

### 4.5 Wiring Both In, the Polite Way

All three edits, same pattern as every other model:

- `common/ai/llama-cpp.nix`: `sailor2-1b` preset (ctx 4096, temp 0.7, top-p 0.9, jinja on). Nix eval: **7 presets**, clean.
- `common/ai/litellm/config.yaml` (seed) and `/srv/appdata/litellm/config.yaml` (live): `local/sailor2-1b` entry with `disable_background_health_check: true`.
- `diff` between seed and live: byte-identical, as required.

Home.arpa reminder discovered the hard way: `llama.home.arpa` and `ai.home.arpa` do **not** resolve from the homelab NixOS host itself -- they are for client machines. Verification therefore happens from the workstation, not via `ssh homelab`.

### 4.6 Activation, Verification, and a Change of Heart

Owner ran the ritual: `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` + `sudo systemctl restart litellm`.

Post-activation: all 7 presets present in `/v1/models` on port 8080 AND at `https://llama.home.arpa`, with the expected flags (`--temperature 0.7 --top-p 0.9 --jinja --threads 4`). In Indonesian translation, sailor2-1b out-translated qwen2.5-1.5b. The user asked the honest question: *why keep qwen2.5-1.5b at all?*

Fair answer: it fills the niche of a fast general-purpose chat model. `tinyllama` is the fast-but-weak tier; `qwen3` is the strong-but-slower tier; `qwen2.5-1.5b` was the middle. And it covers 29 languages, not just the SEA set. But the user has a Qwen2.5-3B sitting in `/mnt/c/ai/models/qwen2.5-3b/` waiting for a long-delayed comparison -- so the middle tier gets a sabbatical.

`qwen2.5-1.5b` was moved to `/mnt/c/ai/models/qwen2.5-1.5b/` (GGUF + cpp.yaml, sha256 verified as `6a1a2eb6...` after the 1.1 GiB scp), removed from the homelab: model dir deleted, preset removed, both LiteLLM entries removed, configs diff-identical again. Nix eval: **6 presets**. Owner rebuild still pending at time of writing.

### 4.7 Repo Hygiene (or: The Commit Pile)

| commit | subject |
|---|---|
| `809c8d3` | `ai: add qwen2.5-1.5b and sailor2-1b llama-cpp presets + litellm local models` |
| `7f54c0a` | `ai: remove qwen2.5-1.5b (moved to /mnt/c/ai/models for later comparison)` |
| `936fd53` | `docs: reference shared architecture principles in AGENTS.md` |
| `3b6f92c` | `chore: remove archive/.gitkeep (dir unused)` |

Two pre-existing dirty files (`M AGENTS.md`, `D archive/.gitkeep`) were inspected and committed only when asked; the `archive/` directory itself was already gone from disk. Working tree clean afterward.

## 5. Verification (or: Proof, Not Vibes)

From the workstation (home.arpa resolves there):

```
llama.home.arpa /v1/models   -> 7 presets (incl. qwen2.5-1.5b, sailor2-1b)
ai.home.arpa /v1/chat/completions -> OK for local/qwen2.5-1.5b and local/sailor2-1b
```

Translation runs (EN->ID: "The fall of the Majapahit kingdom remains a historical debate."):

| model | route | system prompt? | output |
|---|---|---|---|
| qwen2.5-1.5b | llama.home.arpa | no | `Kehilangan kerajaan Majapahit masih menjadi debat sejarah.` |
| qwen2.5-1.5b | litellm `local/qwen2.5-1.5b` | yes | `Kehilangan Kerajaan Majapahit masih menjadi topik diskusi sejarah.` |
| sailor2-1b | llama.home.arpa | no | answers in English, verbosely (explains the sentence) |
| sailor2-1b | litellm `local/sailor2-1b` | yes | `**Penghancuran Kerajaan Majapahit tetap menjadi perdebatan sejarah.**` |

Sailor2 quality is clearly better for the job -- and just as clearly **needs the translator system prompt**. Without it, a 1B model does what a 1B model does: it answers the meta-question instead of translating.

## 6. Results (or: The Magic Number Is Now Six)

Final lineup at time of writing:

| alias | role |
|---|---|
| `tinyllama` | fast, weak general chat |
| `sailor2-1b` | SEA translation (EN<->ID + 13 SEA languages) |
| `qwen3` | multilingual general chat/reasoning |
| `qwen2.5-coder` | code |
| `mxbai-embed-large` | embeddings |
| `gemma-4-E4B` | vision |

Deleted from homelab, preserved for later: `qwen2.5-1.5b` at `/mnt/c/ai/models/qwen2.5-1.5b/`.

Also banked: three mem0 learnings (task_learning) -- the xet single-connection throttle plus the parallel-range fix, the home.arpa resolution quirk, and Sailor2 as the llama.cpp translation choice. Task file `2026-09-06-add-smaller-models.md` closed with the full checklist.

## 7. Recommendations

1. **Sailor2 is the translation preset; give it a system prompt.** Wire the translator persona into the system prompt (or an alias) so clients do not have to remember the trick.
2. **Parallel range downloads are the house style for big GGUF pulls.** One connection through xet is a lie about your bandwidth. 8 ranges, ordered concat, byte-count assert.
3. **Never `pkill -f` a string you also type.** Kill recorded PIDs or scan `/proc` while excluding your own process. Famous last words, applied.
4. **Verify `home.arpa` endpoints from a client, not the box.** The homelab host cannot resolve its own `*.home.arpa` names; that will confuse every curl that runs over `ssh homelab`.
5. **The 8B Sailor2 is a RAM-pending upgrade.** If the box ever gets headroom, `sailor2-L-8b-chat` Q4_K_M is the flagship quality tier for SEA translation -- same arch, same wiring.
6. **Revisit when qwen2.5-3b finally meets qwen2.5-1.5b.** The `/mnt/c/ai/models` comparison will decide whether the middle general-chat tier returns.

## 8. Open Questions and Follow-Ups

- **Activation of the 6-preset lineup**: owner's rebuild (`sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` + `sudo systemctl restart litellm`) drops `qwen2.5-1.5b` live.
- **Sailor2 without a system prompt** answers in English: decide whether to bake the translator persona into the alias rather than demanding clients do it.
- **qwen2.5-3b vs qwen2.5-1.5b**: the reason qwen2.5-1.5b lives on instead of dying. "Very much later" is an acceptable timeline for a 1.1 GiB file.

---

Generated by Big Pickle (OpenCode)