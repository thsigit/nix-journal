# A Proxy That Remembers What Kaggle Forgets (or: Making an Ephemeral Endpoint Look Fixed)

**Date:** 2026-11-10  
**Author:** Codebot  
**Topic:** kaggle, llm, proxy, fastapi, cloudflare-tunnel, opencode, local-network

---

## 1. Objective

Turn the ephemeral Kaggle LLM endpoint (which changes URL each session and requires reconfiguring every agent) into a fixed local address. The plan: create a minimal B3 notebook for faster cold starts using existing datasets, debug the Kaggle runtime path until the server and tunnel come up, and run a local WSL proxy at `kaggle.home.arpa:8087` with a web UI to set/clear the current trycloudflare target on demand.

## 2. Background

The 2026-11-09 report established a working Kaggle fallback with model and CUDA wheel cached in datasets (v23/v24) and an ad-hoc Cloudflare quick tunnel. The remaining friction was operational: every new session produced a different `trycloudflare.com` URL, forcing manual updates to OpenCode/LiteLLM configurations. The goal was to eliminate that churn with a local fixed proxy.

## 3. Problem

- **Reconfiguration churn**: agents must be pointed at a new base URL each Kaggle session.
- **Notebook complexity**: v25 had tunnel/process tracking issues and an inference smoke test in Run All; a simpler flow was desired.
- **Runtime gotchas on Kaggle**: attached datasets mount under `/kaggle/input/`, not `/kaggle/working/`; the CUDA wheel needs `libcudart.so.12` from pip nvidia packages plus `LD_LIBRARY_PATH` adjustments; the Python server requires extra deps (`sse-starlette`, `fastapi`, `uvicorn`, etc.); `cloudflared` cannot be backgrounded with IPython shell `&` in that environment.
- **TLS/browser friction**: a local proxy is easiest as plain HTTP, which can confuse browsers that try to upgrade to HTTPS.

## 4. Work Performed

### 4.1 Simplified B3 notebook (local)
A new notebook `kaggle-llm-fallback-b3.ipynb` was created with a minimal Run All flow:
- **Bootstrap**: detect GGUF and wheel under `/kaggle/input` and `/kaggle/working` (recursive), fail fast if missing, install wheel from dataset, install server deps.
- **Server**: start `python -m llama_cpp.server` with GPU layers offloaded, poll `/v1/models` until ready, print model id.
- **Tunnel**: start `cloudflared` via `subprocess.Popen` (logging to file), parse the `trycloudflare.com` URL from logs.
- **Cleanup**: stop server and tunnel.

### 4.2 Kaggle runtime debugging
Working through the notebook on a live session:
1. **Paths**: updated bootstrap/server to search `/kaggle/input` recursively (datasets mounted as `.../datasets/owner/dataset/...`).
2. **Pip flags**: removed unsupported `-y` from `pip install`.
3. **CUDA runtime**: added pip nvidia lib paths (e.g. `.../nvidia/cuda_runtime/lib`) to `LD_LIBRARY_PATH` and passed `env=os.environ.copy()` to the server process so `libcudart.so.12` was found.
4. **Server deps**: installed `uvicorn`, `fastapi`, `sse-starlette`, `starlette-context`, `pydantic-settings`.
5. **Tunnel**: replaced shell-background `!cloudflared ... &` with `subprocess.Popen` logging to `/kaggle/working/cloudflared.log` and regex-parsed the public URL.

The endpoint came up and external `curl` returned the model list from the ephemeral URL.

### 4.3 Local WSL proxy
A local reverse proxy was built to provide a fixed address:
- **Service**: `~/.local/bin/kaggle-proxy.py` (FastAPI + uvicorn + httpx), bound to `127.0.0.1:8087`. UI at `/` with set/clear form, `/_status`, and streaming reverse proxy for all other paths to the configured target.
- **Normalization**: target URL normalized (strip `/v1`/`/v1/models` suffixes, store base).
- **Dependencies**: installed `fastapi`, `uvicorn`, `httpx`, `python-multipart` (user-level).
- **Name resolution**: added `127.0.0.1 kaggle.home.arpa` to WSL `/etc/hosts` (Windows hosts updated separately).
- **Verification**: from Windows, `curl http://127.0.0.1:8087/v1/models` returned the proxied model list successfully. Browsing to HTTP worked for API; opening via `https://` caused TLS issues as expected since the proxy serves plain HTTP.

## 5. Diagnosis

- **Kaggle layout differs from assumptions**: attached datasets live under `/kaggle/input`, so path discovery must be recursive and robust.
- **Environment differs**: Kaggle's image has CUDA 13.0 system libs but the wheel needed CUDA 12 runtime from pip nvidia packages; `LD_LIBRARY_PATH` must be adjusted in-process.
- **IPython subprocess constraints**: backgrounding with `&` in shell magics is not supported; use `subprocess.Popen`.
- **Proxy simplicity wins**: a tiny local proxy is sufficient to decouple agents from ephemeral tunnel URLs - streaming support is essential for chat completions.

## 6. Solution Summary

- **B3 notebook** created locally with dataset-first bootstrap, proper server start, subprocess-based tunnel, and cleanup.
- **Kaggle issues debugged and fixed** iteratively until the endpoint and external tunnel were reachable.
- **Local proxy deployed** on WSL at `127.0.0.1:8087` (and `kaggle.home.arpa:8087`) with web UI to set/clear the ephemeral target; agents can be pointed to this fixed base URL once.
- **End-to-end verified**: Windows curl to the local proxy returned the proxied `/v1/models` response.

## 7. Verification

| Item | Result | Evidence |
|---|---|---|
| B3 notebook structure | OK | Dataset discovery, server polling, subprocess tunnel, cleanup implemented |
| Kaggle dataset paths/wheel/CUDA/libs | OK | Found GGUF/wheel under `/kaggle/input`; `llama_cpp` loaded after `LD_LIBRARY_PATH` fix; server deps installed |
| Cloudflared tunnel (subprocess) | OK | Parsed `trycloudflare.com` URL from log, external `/v1/models` accessible |
| Local proxy startup/UI/API | OK | FastAPI server running, set/clear/status endpoints functional, HTML UI served |
| Proxy end-to-end from Windows | OK | `curl http://127.0.0.1:8087/v1/models` returned model list through proxy |

## 8. Pending Actions

- **Browser TLS**: either use HTTP explicitly or add local TLS to the proxy if some clients require HTTPS.
- **Agent integration**: configure OpenCode/LiteLLM once to `http://kaggle.home.arpa:8087/v1` using the proxied model id.
- **Robustness**: consider auto-detecting model id from `/v1/models` in the proxy UI, and better error surfacing when upstream is down.
- **Persistence**: optional systemd user service for the proxy to start on login.

## 9. Recommendations

- **Keep it simple**: the B3 approach (datasets + subprocesses + local proxy) is practical for ad-hoc use without over-automating an ephemeral platform.
- **Debug systematically**: when moving between Kaggle/local environments, watch for path layout differences (`/kaggle/input` vs local), library paths, and process management constraints.
- **One-time config wins**: a local fixed proxy eliminates per-session agent reconfiguration and is easy to toggle.
- **Stay honest about ephemerality**: treat the Kaggle endpoint and tunnel as session-bound; the proxy just makes them easier to swap in/out.

Generated with Iceman Free by OpenCode
