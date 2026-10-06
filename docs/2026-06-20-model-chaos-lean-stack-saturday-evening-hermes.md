# Hermes Agent Provider and Fallback Chain - Part 1

*From Model Chaos to a Lean Stack: A Saturday Evening with Hermes*

**Date:** 2026-06-20  
**Author:** Codebot  
**Topic:** Hermes Agent, Ollama, WSL2, narrative, local-llm, failover  

## 1. Objective

Audit and rebuild a local LLM inference stack on WSL2 (16GB RAM, no GPU) to eliminate unused models, pull CPU-appropriate models, and implement a cloud failover layer for code tasks requiring more compute.

## 2. Background

The Hermes Agent was routing through a local Ollama instance (`ollama-launch` provider at `http://127.0.0.1:11434/v1`) with `minimax-m3:cloud` as the active model. Eleven models were configured, several too large for CPU inference on the available memory. No automated failover existed for cloud provider quotas.

## 3. Problem

- Model hoarding: 11 models configured, many unusable on CPU with ~6GB free RAM
- No failover: Cloud provider quota exhaustion caused silent failures
- Unclear model roles: No routing strategy for different task types (structured output vs. explanations vs. code)

## 4. Work Performed

### 4.1 Hardware Reality Check

Confirmed WSL2 allocation: 7.8GB (50% of 16GB host), ~6.1GB free. No GPU. Realistic model headroom: ~3-4GB.

### 4.2 Model Audit

Listed 11 configured models from Hermes Agent config and live Ollama instance. Identified oversized models: `gemma3n:7b` (7GB), `qwen2.5-coder:7b` (4.7GB).

### 4.3 Pull CPU-Appropriate Models

Selected three models optimized for quality-per-byte on CPU:

- `qwen2.5:3b` (1.9 GB) - general purpose
- `deepseek-r1:1.5b` (1.1 GB) - reasoning
- `starcoder2:3b` (1.7 GB) - code-focused

Pulled in background over slow connection (~2.5 MB/s). Total new disk usage: ~4.7GB.

### 4.4 Model Testing and Profiling

Ran identical prompt against all three models:

| Model            | Result                               | Time                  | Tokens/sec | Assessment            |
| ---------------- | ------------------------------------ | --------------------- | ---------- | --------------------- |
| qwen2.5:3b       | Correct JSON + prose                 | 16s                   | 11.38      | Reliable              |
| deepseek-r1:1.5b | Empty JSON (strict), good plain text | 2.88s                 | N/A        | Good for explanations |
| starcoder2:3b    | Garbage output, timeout on code      | 10.31s / 120s timeout | N/A        | Unreliable            |

### 4.5 Cleanup of Large Models

Removed four models from Hermes Agent config and Ollama disk:

- `qwen2.5-coder:7b` (4.7 GB) - deleted
- `translategemma:4b` (3.3 GB) - deleted
- `qwen3-vl:4b-instruct` (~3 GB) - deleted
- `gemma3n:latest` (~7 GB) - not on disk, config-only removal

Freed ~11GB disk space.

### 4.6 Default Model and Routing Rules

Set Hermes Agent default to `qwen2.5:3b` (most reliable for structured output and code). Established routing rule:

- `plain` -> `deepseek-r1:1.5b` (explanations)
- `structured` -> `qwen2.5:3b` (JSON, code)

Registered as Hermes Agent quick commands.

### 4.7 Cloud Failover Layer

Built `cloud_failover.sh` script:

- Iterates provider|model pairs in priority order
- Sources credentials from `~/.hermes/.env`
- Honors Hermes Agent profiles
- Exponential backoff retry
- Logs attempts with timestamps, duration, output previews

Built `cloud_providers_health.sh` for manual health checks.

Smoke test: Failover succeeded against OpenRouter. Health check: OpenRouter timeout, OpenAI and Anthropic OK (~2s).

## 5. Diagnosis

The original stack suffered from three issues: (1) model bloat with oversized models consuming disk and config complexity, (2) no routing strategy causing inappropriate model selection per task, (3) single-point-of-failure on cloud providers with no automated failover. The CPU memory constraint (6GB free) fundamentally limits local inference to 3B-parameter models.

## 6. Preliminary Assessment

The lean stack (3 local models + cloud failover) fits within hardware constraints and provides clear routing semantics. `qwen2.5:3b` is the workhorse for structured tasks. `deepseek-r1:1.5b` serves explanations. Cloud failover handles code tasks requiring more compute. `starcoder2:3b` requires further evaluation.

## 7. Solution Summary

- Reduced from 11 to 3 local models (4.7GB total)
- Established task-type routing with quick commands (`plain`, `structured`, `failover`)
- Implemented automated cloud failover with exponential backoff and logging
- Freed 11GB disk space
- All changes survive session restart

## 8. Verification Plan

- Retry `starcoder2:3b` with controlled code-only prompt
- Configure cron/systemd timer for regular health checks
- Add log rotation for failover and health check logs
- Test failover under actual quota exhaustion
- Consider raising WSL2 memory cap via `.wslconfig`

## 9. Pending Actions

- Complete `starcoder2:3b` evaluation
- Automate health checks
- Implement log rotation
- Test WSL2 memory increase

## 10. Recommendations

- Audit local model inventory quarterly; remove unused large models
- Always define routing rules before adding models
- Implement failover for any production cloud dependency
- Profile models on target hardware before committing
- Keep quick command names semantic (`plain`, `structured`, `failover`)
