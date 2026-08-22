# Building A Local LLM Setup In WSL2

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** WSL2, Ollama, Hermes Agent, llm, local-inference, failover  

## 1. Objective

Rebuild a lean, interchangeable local LLM inference stack on WSL2 (16GB RAM, no GPU) within hardware constraints, eliminating unused models and implementing cloud failover for compute-intensive tasks.

## 2. Background

Hermes Agent routed through `ollama-launch` provider (`http://127.0.0.1:11434/v1`) with `minimax-m3:cloud` active. Eleven models configured; several too large for CPU inference (~6GB free). No failover for cloud quota exhaustion.

## 3. Problem

- Model hoarding: 11 models, many unusable on CPU
- No failover: cloud quota exhaustion causes silent failures
- Unclear model roles: no routing strategy per task type

## 4. Work Performed

### 4.1 Hardware Reality Check

WSL2 allocation: 7.8GB (50% of 16GB host), ~6GB free. No GPU. Realistic model headroom: 3-4GB max.

### 4.2 Model Audit

11 models from Hermes Agent config and live Ollama. Oversized: `gemma3n:7b` (7GB), `qwen2.5-coder:7b` (4.7GB).

### 4.3 Pull CPU-Appropriate Models

Three models selected for quality-per-byte on CPU:

| Model | Size | Role |
|-------|------|------|
| qwen2.5:3b | 1.9 GB | General purpose |
| deepseek-r1:1.5b | 1.1 GB | Reasoning |
| starcoder2:3b | 1.7 GB | Code-focused |

Background pulls at ~2.5 MB/s. Total new disk: ~4.7GB.

### 4.4 Model Testing and Profiling

Identical prompt across all three:

| Model | Result | Time | Tokens/sec | Assessment |
|-------|--------|------|------------|------------|
| qwen2.5:3b | Correct JSON + prose | 16s | 11.38 | Reliable |
| deepseek-r1:1.5b | Empty JSON (strict), good plain text | 2.88s | N/A | Good for explanations |
| starcoder2:3b | Garbage, timeout on code | 10.31s / 120s | N/A | Unreliable |

### 4.5 Cleanup

Removed from Hermes Agent config and Ollama disk:
- `qwen2.5-coder:7b` (4.7 GB)
- `translategemma:4b` (3.3 GB)
- `qwen3-vl:4b-instruct` (~3 GB)
- `gemma3n:latest` (~7 GB, not on disk)

Freed ~11GB disk.

### 4.6 Default and Routing

Set Hermes Agent default: `qwen2.5:3b`. Quick commands registered:
- `plain` -> `deepseek-r1:1.5b`
- `structured` -> `qwen2.5:3b`
- `failover` -> `cloud_failover.sh`

### 4.7 Cloud Failover Layer

`cloud_failover.sh`:
- Iterates provider|model pairs in priority order
- Sources `~/.hermes/.env`
- Honors Hermes Agent profiles
- Exponential backoff
- Logs to `~/.hermes/logs/cloud_failover.log`

`cloud_providers_health.sh`: manual health checks, logs to `~/.hermes/logs/cloud_providers_health.log`.

Smoke test: failover succeeded (OpenRouter). Health check: OpenRouter timeout, OpenAI/Anthropic OK (~2s).

## 5. Diagnosis

Original stack: model bloat, no routing strategy, single-point-of-failure on cloud. CPU memory (6GB free) limits local inference to ~3B parameters.

## 6. Preliminary Assessment

Lean stack (3 local + cloud failover) fits constraints with clear routing. `qwen2.5:3b` = workhorse. `deepseek-r1:1.5b` = explanations. Cloud failover = code tasks. `starcoder2:3b` needs evaluation.

## 7. Solution Summary

- 11 to 3 local models (4.7GB total)
- Task-type routing via quick commands
- Automated cloud failover with backoff and logging
- 11GB disk freed
- Changes persist across restarts

## 8. Verification Plan

- Retry `starcoder2:3b` with controlled code-only prompt
- Cron/systemd timer for health checks
- Log rotation for new logs
- Test failover under actual quota exhaustion
- Consider `.wslconfig` memory increase

## 9. Pending Actions

- Complete `starcoder2:3b` evaluation
- Automate health checks
- Implement log rotation
- Test WSL2 memory increase

## 10. Recommendations

- Quarterly audit of local model inventory
- Define routing rules before adding models
- Implement failover for production cloud dependencies
- Profile models on target hardware before committing
- Use semantic quick command names (`plain`, `structured`, `failover`)
