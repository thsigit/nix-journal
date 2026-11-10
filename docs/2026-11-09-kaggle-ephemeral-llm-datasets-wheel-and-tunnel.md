---
nav:
  series: "Kaggle Ephemeral LLM"
  part: 1
  next:
    title: "A Proxy That Remembers What Kaggle Forgets (or: Making an Ephemeral Endpoint Look Fixed)"
    slug: 2026-11-10-a-proxy-that-remembers-what-kaggle-forgets
---

# Kaggle Ephemeral LLM: Datasets, Wheel Caching, and a Tunnel (or: Making the Free Fallback Less Painful)

**Date:** 2026-11-09  
**Author:** Codebot  
**Topic:** kaggle, llm, gpu-inference, llama-cpp-python, gguf, cloudflare-tunnel, datasets, opencode

---

## 1. Objective

Follow up on the 2026-10-27 Kaggle LLM inference report and turn the proven-but-friction-heavy v22 pipeline into a more practical ephemeral fallback: cache the model and CUDA wheel in Kaggle Datasets, verify the v22/v23 fixes in a real cold-start session, prove the ad-hoc Cloudflare quick tunnel path, and document what still hurts.

## 2. Background

The 2026-10-27 report (`2026-10-27-kaggle-llm-inference-endpoint.md`) established a working OpenAI-compatible endpoint on Kaggle's free T4 GPU notebooks using a prebuilt `llama-cpp-python` CUDA wheel, a Qwen2.5-Coder-7B-Instruct Q4_K_M GGUF, and a pure-Python notebook pipeline (kernel `thsigit/kaggle-llm-fallback-llama-cpp-server`). It also left explicit gaps: Cell 10's `/v1/models` readiness probe and Cell 14 cleanup were not executed end-to-end in that session, the 4.68 GB model was re-downloaded on cold starts, the 1.8 GB CUDA wheel was reinstalled every session because pip packages are wiped, and no public tunnel/LiteLLM wiring existed.

Kaggle constraints remain load-bearing: sessions are ephemeral, GPU quota is finite (confirmed 30.00 h/week on 2026-10-24, refresh 2026-10-31), `/kaggle/working` survives session restarts while site-packages do not, and Internet must be enabled for downloads/tunnels.

## 3. Problem

The v22 recipe worked, but practical reuse had four friction points:

1. **Unverified fixes.** The v22 readiness probe (`GET /v1/models`, not `/health`) and safe PID-only cleanup (Cell 14) had not been observed in a fresh cold-start pass.
2. **Model cold-start cost.** The GGUF (4,683,073,536 bytes) lived in `/kaggle/working` across restarts, but first-time/session-loss scenarios still meant a large download risk and no explicit attachable artifact.
3. **Wheel cold-start cost.** Every session wiped pip packages, forcing a ~1.8 GB CUDA wheel reinstall (`llama_cpp_python-0.3.36-py3-none-manylinux_2_35_x86_64.whl`, cu125) plus server dependencies.
4. **No usable remote access pattern.** The endpoint was reachable only inside the session (`127.0.0.1:8080`). The task required an ad-hoc exposure path and an explicit note that the URL dies with the session.

## 4. Work Performed

### 4.1 Cold-start verification (v22 behavior, 2026-11-09)

A fresh Kaggle session was used to verify the previously unobserved cells:

- **Cell 12 (inference):** `model id from /v1/models: Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf` -> `HTTP 200` -> valid generated `reverse_string` code. This confirmed the server/model path and the `/v1/models`-based readiness design end-to-end.
- **Cell 14 (cleanup):** `Graceful stop OK` / `Cleanup done. Model/repo/build/log preserved.` Safe tracked-PID cleanup verified.

Local tracking tasks were updated: `TASK-testing-kaggle.md` (cold-start verification) was completed and archived; `TASK-kaggle-free-gpu-llm-inference.md` was updated to reflect resolved blockers.

### 4.2 Model dataset caching (v23)

The GGUF was exported as a Kaggle Dataset and the notebook was updated to prefer attached datasets before downloading:

- Dataset: `thsigit/qwen2-5-coder-7b-instruct-q4-k-m-gguf` (https://www.kaggle.com/datasets/thsigit/qwen2-5-coder-7b-instruct-q4-k-m-gguf)
- `kernel-metadata.json`: added dataset to `dataset_sources`.
- **Cell 8:** checks `/kaggle/input/qwen2-5-coder-7b-instruct-q4-k-m-gguf/<gguf>` and glob fallbacks; validates magic bytes + exact size; sets `model_path`/`gguf` to the resolved path.
- **Cell 10:** resolves `model_path` from Cell 8/globals/dataset/local candidates.
- Kernel pushed as **v23**.

Live v23 verification showed:
```text
Using attached dataset model: /kaggle/input/qwen2-5-coder-7b-instruct-q4-k-m-gguf/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf 4683073536 bytes
Server ready after 20s (model loaded, GPU offload)
HTTP 200
```

### 4.3 CUDA wheel dataset caching (v24)

The 1.8 GB CUDA wheel reinstall remained the main cold-start penalty. The wheel was cached as a Kaggle Dataset and Cell 6 was updated to install from the local dataset path:

- Wheel: `llama_cpp_python-0.3.36-py3-none-manylinux_2_35_x86_64.whl` (cu125 release asset)
- Dataset: `thsigit/llama-cpp-python-0-3-36-cu125-wheel` (https://www.kaggle.com/datasets/thsigit/llama-cpp-python-0-3-36-cu125-wheel)
- `kernel-metadata.json`: now includes both datasets.
- **Cell 6:** probes for existing GPU-capable install; if missing, looks for a cached wheel under `/kaggle/input/llama-cpp-python-0-3-36-cu125-wheel/` (and glob fallbacks), installs from the local `.whl` with `pip install --no-cache-dir <wheel>`, then ensures server dependencies (`sse_starlette`, FastAPI, uvicorn, etc.) via the existing server probe/install path. Falls back to the original GitHub wheel download logic if the cached wheel is absent or unusable.
- Kernel pushed as **v24**.

Live v24 verification (Cell 6) showed:
```text
ModuleNotFoundError: No module named 'llama_cpp'
Installing from cached dataset wheel: /kaggle/input/llama-cpp-python-0-3-36-cu125-wheel/llama_cpp_python-0.3.36-py3-none-manylinux_2_35_x86_64.whl
pip returncode: 0
llama_cpp 0.3.36 | gpu_offload: True
Server dependencies missing - installing [server] extra now...
   ModuleNotFoundError: No module named 'sse_starlette'
pip returncode: 0
server deps OK
Prebuilt CUDA wheel + server deps ready -> python -m llama_cpp.server
```

This removed the 1.8 GB wheel download. Small server dependencies were still fetched (Internet on), which is acceptable compared with the wheel.

### 4.4 Ad-hoc Cloudflare quick tunnel (verified)

After the server was ready, an ad-hoc `cloudflared` quick tunnel exposed `http://127.0.0.1:8080` with no Cloudflare account required:

```text
PUBLIC URL (EPHEMERAL): https://purple-wrapped-manchester-periodic.trycloudflare.com
OpenAI-compatible base: https://purple-wrapped-manchester-periodic.trycloudflare.com/v1
```

External verification from the local host returned:
```json
{"object":"list","data":[{"id":"/kaggle/input/qwen2-5-coder-7b-instruct-q4-k-m-gguf/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf","object":"model","owned_by":"me","permissions":[]}]}
```

The URL is ephemeral by design and dies when the session/tunnel stops.

### 4.5 Bug check

The pushed v24 kernel was pulled with `kaggle kernels pull thsigit/kaggle-llm-fallback-llama-cpp-server` and inspected after a report of "redownloading LLM". Diagnostics in the live session showed both datasets attached and the GGUF present/valid at the expected path; a restart/run confirmed Cell 8 printed `Using attached dataset model`. No code bug was found in v24 for that symptom; the likely causes were stale cell state/session context rather than the pushed logic.

## 5. Diagnosis

- **Dataset caching works when inputs are explicit.** The key improvement was not "Kaggle remembers files" in general, but making Cell 6 and Cell 8 resolve known dataset mount paths, validate artifacts (magic bytes + exact size for the GGUF; import/GPU probe for the wheel), and fall back safely.
- **Ephemerality is still the main product constraint.** Pip packages vanish each session, quick-tunnel URLs change each session, and GPU quota is finite. Caching removes avoidable bandwidth/latency, not the ephemeral nature of the platform.
- **Server deps remain a small tail.** Installing the wheel from a dataset avoids the big download, but `llama-cpp-python` server extras are not fully satisfied by the wheel alone in this setup; the existing server probe correctly installs missing deps.
- **Apparent regressions can be session-state artifacts.** When a dataset is mounted and valid but behavior looks wrong, check the actual Input paths, file size/magic, and whether the notebook session is running the intended version.

## 6. Solution Summary

- Verified v22/v23 behavior in cold-start conditions: `/v1/models` readiness probe path and safe PID-only cleanup.
- Added model dataset attachment (v23) and verified no model re-download when attached.
- Added CUDA wheel dataset attachment (v24) and verified local wheel install with GPU offload, plus server-deps remediation.
- Added and tested an ad-hoc Cloudflare quick tunnel recipe (`trycloudflare.com`), with explicit ephemeral-URL warnings.
- Kept the end state ad-hoc/ephemeral; LiteLLM fallback wiring on `ai.home.arpa` remains deferred.

## 7. Verification

| Item | Result | Evidence |
|---|---|---|
| Cold-start readiness/cleanup | PASS | Cell 12 `HTTP 200` with valid generation; Cell 14 `Graceful stop OK`, model/repo/build/log preserved |
| v23 model dataset path | PASS | `Using attached dataset model: /kaggle/input/qwen2-5-coder-7b-instruct-q4-k-m-gguf/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf 4683073536 bytes`; server ready 20s; inference HTTP 200 |
| v24 wheel dataset install | PASS | `Installing from cached dataset wheel: /kaggle/input/llama-cpp-python-0-3-36-cu125-wheel/llama_cpp_python-0.3.36-py3-none-manylinux_2_35_x86_64.whl`; `llama_cpp 0.3.36 | gpu_offload: True`; `server deps OK` |
| Ad-hoc Cloudflare tunnel | PASS (ephemeral) | `trycloudflare.com` URL created; external `GET /v1/models` returned the model list |
| Pushed kernel inspection | PASS | `kaggle kernels pull` inspected v24; model/wheel dataset checks present in Cells 8/6; both datasets in metadata |

## 8. Pending Actions

- **Simplification discussion (next task):** discuss how to make this Kaggle setup simpler and more practical (discussion only, no build in that session), using this report as the baseline.
- **Server dependency caching (optional):** small `[server]` deps are still fetched; evaluate whether caching/pinning them is worth the complexity.
- **LiteLLM fallback wiring (deferred):** if needed later, design a safe way to register an ephemeral upstream on `ai.home.arpa` without pretending it is stable.
- **Operational hygiene:** always stop sessions after use; never factory-reset when preserving `/kaggle/working`; treat tunnel URLs as secrets-in-effect while active (publicly reachable).

## 9. Recommendations

- Keep the setup **ad-hoc and honest**: Kaggle is a free ephemeral compute fallback, not a service.
- Prefer **attached Kaggle Datasets** for large immutable artifacts (GGUF, CUDA wheel) and validate them before use.
- Keep **Cell 14 cleanup** and the "Stop session, never Factory reset" rule in the operator path.
- Use Cloudflare quick tunnels only for temporary access, and assume the URL will change every session.
- Before adding more automation, run the simplification discussion: the next win is likely UX/operability, not more moving parts.

Generated with Iceman Free by OpenCode
