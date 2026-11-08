# Llama.cpp Inference on Kaggle: A Free GPU Fallback (or: The Wheel, Reinvented)

**Date:** 2026-10-27  
**Author:** Codebot  
**Topic:** kaggle, llm, gpu-inference, notebook, fallback  

---

## 1. Objective

Prove that a working LLM inference endpoint can be built for free on Kaggle's ephemeral GPU notebooks (T4x2, 30h/week) using only prebuilt assets, and create a reproducible cold-start pipeline as a fallback whenever hosted LLM providers run out of quota.

## 2. Background

Kaggle offers free notebook sessions with NVIDIA T4 GPUs to any authenticated user, bounded by weekly GPU quotas. These are ephemeral by design: the moment you stop or restart a session, running processes, installed packages, and RAM all vanish except for files in `/kaggle/working`. This limitation makes Kaggle unsuitable for public-facing API endpoints, but uniquely suited as a "just-in-time" inference fallback for internal tools or quota-overdrawn providers. The work aimed to build a fully OpenAI-compatible endpoint using llama.cpp and the GGUF quantized model format, with minimal effort and full session rerun safety.

## 3. Problem

- **No official, persistent GPU endpoints**: Kaggle sessions are destroyed on stop/reset, and there's no way to serve traffic after the session ends. This forces a pure "it works while you watch" workflow.
- **Multi-hour source builds fail**: Installing and building `llama.cpp` from source (CMake + nvcc) on Kaggle T4 nodes hung for hours and failed with either missing CUDA targets or OOM.
- **Prebuilt pipeline needed**: Only prebuilt wheels or binaries can bring up an endpoint in minutes, not hours. PyPI does *not* have CUDA wheels for Python 3.13 (the current Kaggle version), so the install must use GitHub release assets.
- **Missing server dependencies**: The correct `llama-cpp-python` wheels require an explicit `[server]` extra for FastAPI, SSE, and related deps.
- **No `/health` endpoint**: Unlike the C++ `llama-server`, `llama-cpp-python` exposes only `/v1/*` and `/extras/` - many troubleshooting cycles were lost to probing `/health` (which always 404s).

## 4. Work Performed

### 4.1 Notebook Pipeline Construction
- **Cell 6**: Installs the prebuilt `llama-cpp-python` v0.3.36 CUDA wheel (`cu125`, fallback `cu124`/`cu122`) *with* the `[server]` extra from GitHub Releases (never from PyPI, which lacks CUDA wheels for 3.13).
- **Cell 8**: Downloads the chosen Qwen2.5-Coder-7B-Instruct-Q4_K_M GGUF from the official Qwen repo (and verifies magic + size, with a second mirror fallback). Model size: 4,683,073,536 bytes.
- **Cell 10**: Starts the server with correct flags --model `--n_ctx` (not `-m`/`-c`), Popen logs, polls `/v1/models` for readiness (never `/health`).
- **Cell 12**: Runs a full OpenAI-compatible inference round-trip; code and output validated.
- **Cell 14**: Cleans up gracefully (tracked PID only).

### 4.2 Debug Cycles and Fixes
- **Switched from source to prebuilt** after 2x multi-hour hangs.
- **Patched server dependencies** (`pip install ...[server]`) after ModuleNotFoundError on startup.
- **Corrected probe and command-line flags** after reading source (Python server is not always 1:1 with C++ version).
- **Rerun-idempotency built in** at every step: model redownload/cell re-run never triggers re-download/re-install unless actually needed.

## 5. Diagnosis

- *Root cause of multi-hour failures*: CMake tried to compile for every CUDA architecture, not just T4 (compute 7.5); Kaggle's resource constraints amplify this.
- *401s on model download*: TheBloke repo was a red herring; only the official Qwen repo actually holds Qwen2.5-Coder-7B-Instruct Q4_K_M (and passes HTTP 206 checks).
- *Health probe failures*: `/health` 404 loop explained by source inspection: Python-only endpoint exposes `/v1/models` et al., not `/health`.

## 6. Preliminary Assessment

The new pipeline is robust, idempotent, and requires only three user-facing choices per cold start: Cell 6 (install), Cell 8 (model), and Cell 10 (start). Errors now print with full context, and all cells validate by output.

## 7. Solution Summary
- Use only prebuilt wheels (no source compile).
- Wheel install must be from the GitHub `v0.3.36-cu12*` release URLs, with `[server]` extra.
- Cold-start pipeline is tested and execution-proven (through v22).
- Health probe code **and report** reflect real server behavior (`/v1/models`, not `/health`).
- Safe cleanup pattern is included; model and logs survive, pip packages do not.
- Real asset: notebook and kernel-metadata JSON attached to the `kaggle-llm-inference` skill for future sessions.

## 8. Verification Plan
- [x] Cold-start a fresh session (pip wiped): Cell 6 (installs prebuilt CUDA wheel+server, `gpu_offload: True`)
- [x] Cell 8 (model download: GGUF magic, exact size)
- [x] Cell 10 (server up: `/v1/models` returns model id; no `/health` route exists)
- [x] Cell 12 (actual inference tested)
- [ ] Cell 14 (explicitly run for graceful, idempotent cleanup)

## 9. Pending Actions
- Export the downloaded model to a Kaggle Dataset for faster attachment/clone in new sessions.
- Wire a Cloudflare Tunnel for incoming traffic and test full session-to-public URL.
- Test and document the endpoint as a LiteLLM fallback.

## 10. Recommendations
- Do **not** attempt to compile from source or fix nvcc/CMake errors on Kaggle, ever.
- Use GitHub release wheels with `[server]`, never PyPI or wheels built in-place.
- Always check model URLs for public 206 before scripting downloads.
- **Attach and edit** the notebook from the kaggle-llm-inference skill, not from scratch.
- Document future migration paths as Kaggle upgrades Python or CUDA.

Generated with GPT-4.1 by GitHub Copilot
