# Openclaw Dementia And Config Backups

*When OpenClaw Forgot Its Models*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** openclaw, Hermes Agent, env-vars, config-backups, Gemini  

## 1. Objective

Diagnose OpenClaw's inability to reach configured models and establish configuration backup practices for Hermes Agent equivalent to OpenClaw's JSON config.

## 2. Background

OpenClaw "temporary dementia": cannot find route to working models. Previous solution for Gemini API key sharing: shell exports (`GOOGLE_API_KEY`, `OPENAI_BASE_URL=generativelanguage.googleapis.com/v1beta/openai/`). User confirmed variables set correctly.

## 3. Problem

Environment variables set but OpenClaw TUI returns `run error: LLM request failed` on simple "hello" after model selection. Not connection refused or bad key - generic failure suggesting stale path, hardcoded endpoint, or missing config file credential.

## 4. Work Performed

### 4.1 Environment Verification

Confirmed `GOOGLE_API_KEY` and `OPENAI_BASE_URL` set correctly. Not the issue.

### 4.2 Model List and Selection

`openclaw models list`: `gemini`, `ollama cloud`, `ollama local`. Set active model to known-good entries. TUI launches. "hello" -> `run error: LLM request failed`.

### 4.3 Config File Restoration

User had old `openclaw.json` backup from early days. Restored it. OpenClaw "dementia lifted." Required provider URLs, default endpoints, last-known-good model lived in JSON, not environment variables.

### 4.4 Hermes Agent Backup Creation

Hermes Agent equivalent of `openclaw.json`: two files:

- `~/.hermes/config.yaml` (settings, model prefs, tools)
- `~/.hermes/auth.json` (API keys, encrypted)

Created `~/.hermes/backups/` and copied both with timestamp.

## 5. Diagnosis

Environment variables are necessary but insufficient. OpenClaw's own configuration file holds routing state (provider URLs, endpoints, model selection). When that file goes stale or missing, environment variables alone cannot restore function. Hermes Agent has the same vulnerability: `config.yaml` and `auth.json` are the source of truth.

## 6. Preliminary Assessment

OpenClaw restored via config backup. Hermes Agent backups now exist. Root cause: tool-internal config drift, not environment.

## 7. Solution Summary

- OpenClaw: restored `openclaw.json` backup -> functional
- Hermes Agent: created timestamped backups of `config.yaml` and `auth.json`
- Lesson: tool config files > environment variables for routing state

## 8. Verification Plan

- Verify OpenClaw stability after config restore
- Schedule periodic Hermes Agent config backups
- Test Hermes Agent backup restoration procedure

## 9. Pending Actions

- Automate periodic Hermes Agent config backups
- Document restore procedure for both tools

## 10. Recommendations

- When agent can't reach models, `echo ` is only first move. Real answer often in tool's own config files.
- Back up tool config files (not just env) regularly
- Timestamp backups for point-in-time recovery
- Treat `config.yaml` + `auth.json` as Hermes Agent's "brain" - back them up together
