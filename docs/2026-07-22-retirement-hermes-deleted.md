# Experimenting with Hermes Agent - Part 10 (FINAL)

*Retirement: ~/.hermes deleted*

**Date:** 2026-07-22  
**Author:** Codebot  
**Topic:** Hermes Agent, Ollama, cleanup, config, narrative  

## 1. Objective

Investigate Hermes Agent retirement residue and clean up bidirectional stale configuration between Hermes Agent and Ollama. Widen bash history limit.

## 2. Background

Query about Hermes Agent deletion led to discovery that Hermes Agent effectively retired but left residue: ~/.hermes/ config/skills/empty database, and Ollama config still referencing Hermes Agent integrations.

## 3. Problem

Two tools pointing at each other with stale config: Hermes Agent configured for Ollama provider (3 models), Ollama config had hermes/hermes-desktop integrations marked onboarded. Ollama launch Hermes Agent failed (interactive terminal demand, then gateway status check, exit status 127 - missing binary).

## 4. Work Performed

### 4.1 Investigation
- Searched for ollama-launch references: only in ~/.hermes/config.yaml
- Hermes Agent config: Ollama provider with minimax-m3:cloud, ornith:latest, nemotron-3-super:cloud
- Tried Ollama launch Hermes Agent: failed (interactive terminal, then exit 127)
- Found ~/.ollama/config.json with:
  - integrations.hermes: onboarded: true
  - integrations.hermes-desktop: onboarded: true
  - last_selection: "hermes"

### 4.2 Cleanup (with user approval)
- Deleted ~/.hermes/ entirely (config, skills, empty database)
- Edited ~/.ollama/config.json: stripped Hermes Agent and hermes-desktop blocks, dropped last_selection
- Remaining integrations: claude, cline, codex, copilot, openclaw, OpenCode, pi, qwen

### 4.3 Shell History Widening
- Baseline: /etc/profile defaults HISTSIZE=1000, no user override
- Added to ~/.bashrc: HISTSIZE=20000, HISTFILESIZE=20000
- Personal shell now remembers 20,000 commands

## 5. Diagnosis

Retiring tool requires cleaning both directions. Integration present but failing (missing binary) pinpoints stale reference. Small QoL changes (history limit) improve daily workflow.

## 6. Preliminary Assessment

Hermes Agent fully removed. Ollama config clean (8 integrations, no Hermes Agent). Bash history 20x increased.

## 7. Solution Summary

- Deleted ~/.hermes/ completely
- Removed hermes/hermes-desktop from ~/.ollama/config.json
- Set HISTSIZE=20000, HISTFILESIZE=20000 in ~/.bashrc

## 8. Verification Plan

- Verify Ollama launch no longer shows Hermes Agent
- Confirm ~/.hermes/ gone
- Test bash history retention

## 9. Pending Actions

- None

## 10. Recommendations

- Clean up both directions when retiring integrated tools
- "Appears but fails" is strong diagnostic for stale integrations
- Small config changes (history) compound daily value