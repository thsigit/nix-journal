# Session Notes Lean Stack And Failover

*Auditing the Provider State, Building the Failover Layer*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** Hermes Agent, Ollama, failover, WSL2, session-notes  

## 1. Objective

Working notebook documenting provider state audit, model pulls, testing, cleanup, default setting, quick commands, tooling creation, and smoke tests for the 06-29 session.

## 2. Background

Hermes Agent running on WSL2 with `ollama-launch` provider. Active model: `minimax-m3:cloud`. 11 models configured. Hardware: ~6GB free, no GPU.

## 3. Problem

Need lean model stack within CPU constraints with automated cloud failover for quota exhaustion scenarios.

## 4. Work Performed

### 4.1 Provider State Audit

- Active provider: `ollama-launch` (`http://127.0.0.1:11434/v1`)
- Active model: `minimax-m3:cloud`
- 11 models in `~/.hermes/config.yaml`

### 4.2 Model Pulls (CPU-Only, 16GB RAM)

Hardware: WSL2 7.8GB allocated, ~6GB free, no GPU.

Pulled three models:

| Model            | Size   | Role            |
| ---------------- | ------ | --------------- |
| qwen2.5:3b       | 1.9 GB | General purpose |
| deepseek-r1:1.5b | 1.1 GB | Reasoning       |
| starcoder2:3b    | 1.7 GB | Code-focused    |

All registered in config.

### 4.3 Model Testing

| Model            | Result                              | Time                  | Assessment            |
| ---------------- | ----------------------------------- | --------------------- | --------------------- |
| qwen2.5:3b       | Correct JSON + prose                | ~16s, 11.38 tok/s     | Reliable              |
| starcoder2:3b    | Failed mixed prompt, timeout strict | 10.31s / 120s timeout | Unreliable            |
| deepseek-r1:1.5b | Fast, unreliable strict JSON        | ~42s verbose          | Good for explanations |

### 4.4 Cleanup

Removed from config and disk:

- `qwen2.5-coder:7b` (4.7 GB)
- `translategemma:4b` (3.3 GB)
- `qwen3-vl:4b-instruct` (~3 GB)
- `gemma3n:latest` (~7 GB, not on disk)

### 4.5 Default Setting

- `model.provider = ollama-launch`
- `model.default = qwen2.5:3b`

### 4.6 Quick Commands

- `plain` -> `hermes chat -m deepseek-r1:1.5b -q`
- `structured` -> `hermes chat -m qwen2.5:3b -q`
- `failover` -> `/home/sigit/.hermes/scripts/cloud_failover.sh`

### 4.7 Tooling Created

- `cloud_failover.sh`: provider|model pairs in order, env vars, `~/.hermes/.env`, Hermes Agent profile, exponential backoff, logs to `~/.hermes/logs/cloud_failover.log`
- `cloud_providers_health.sh`: manual health checks, logs to `~/.hermes/logs/cloud_providers_health.log`
- `README.md`: documentation for both

### 4.8 Smoke Tests

- `cloud_failover.sh`: succeeded vs `openrouter/openrouter/auto`
- `cloud_providers_health.sh`: OpenRouter timeout (12s), openai/anthropic OK (~2s)

### 4.9 Key Decisions

- `qwen2.5:3b` for structured/code/JSON (reliable)
- `deepseek-r1:1.5b` for plain-text explanations (fast, unreliable strict formats)
- `starcoder2:3b` deferred
- Cloud failover priority: OpenRouter -> openai -> anthropic

### 4.10 Files Modified/Created

- `~/.hermes/config.yaml`
- `~/.hermes/scripts/cloud_failover.sh`
- `~/.hermes/scripts/cloud_providers_health.sh`
- `~/.hermes/scripts/README.md`
- `~/.hermes/logs/cloud_failover.log`
- `~/.hermes/logs/cloud_providers_health.log`

## 5. Diagnosis

Lean stack fits hardware. Routing semantics clear. Failover functional. `starcoder2:3b` needs more testing.

## 6. Preliminary Assessment

Configuration complete and verified. Ready for production use with documented routing rules.

## 7. Solution Summary

- 3 local models (4.7GB) replacing 11
- Task routing via quick commands
- Cloud failover with backoff and logging
- Health check tooling
- 11GB disk freed

## 8. Verification Plan

- Retry `starcoder2:3b` controlled code-only
- Cron/systemd timer for health checks
- Log rotation
- WSL2 memory cap increase via `.wslconfig`
- Side-by-side validation tests

## 9. Pending Actions

- `starcoder2:3b` evaluation
- Automate health checks
- Log rotation
- WSL2 memory increase
- Validation tests

## 10. Recommendations

- Profile models on target hardware before committing
- Define routing rules before adding models
- Implement failover for production cloud dependencies
- Keep quick command names semantic
- Document failover priority in config comments
