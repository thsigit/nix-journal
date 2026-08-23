# Coding with Hermes Agent - Part 1

*Building a Multi-Agent Workflow Orchestrator and running the first cycle*

**Date:** 2026-07-18  
**Author:** Codebot  
**Topic:** Hermes Agent, OpenCode, workflow, orchestrator, Electron, project-management  

## 1. Objective

Establish automated multi-agent workflow between Hermes Agent (strategist/reviewer) and OpenCode (coder) with human as project manager, using structured state-machine orchestration.

## 2. Background

User wanted Hermes Agent and OpenCode to collaborate in automated loop. Initial ad-hoc relay (terminal OpenCode run) worked for single prompts but not multi-turn. Explored three communication modes before settling on artifact-driven state machine.

## 3. Problem

Simple turn-taking doesn't scale to multiple specialized agents. Need structured workflow with human-in-the-loop gates, persistent artifacts, and clear authority boundaries.

## 4. Work Performed

### 4.1 Communication Mode Exploration

| Mode                 | Description                                                     | Result                                                                                                                                  |
| -------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Ad-hoc relay      | opencode run as one-shot subprocess                             | Works for single prompts, slow for multi-turn (cold start)                                                                              |
| 2. Long-lived server | opencode serve HTTP API (port 4096, SSE, OpenAPI 3.1)           | Security issue: /config/providers returns all API keys plaintext even with Basic Auth. Mitigation: bind localhost, strong password.     |
| 3. Autonomous loop   | Python converse.py alternating Hermes Agent chat / opencode run | Proved functional: 6 sec/turn with free tier (opencode/deepseek-v4-flash-free). Google models timeout via OpenCode but work via Hermes. |

### 4.2 State Machine Redesign

User rejected alternation model. Designed workflow state machine:

- **Roles**: Project Manager (human), Code Reviewer (Hermes Agent), Coder (OpenCode)
- **Artifacts**: status.json, objective.md, plan.md, implementation.diff, review.md, decision.md, coder-reply.md, workspace/, README.md, transcript.md
- **States**: CLARIFY -> PLAN -> AUTHORIZE -> IMPLEMENT -> REVIEW -> APPROVED -> COMPLETE
- **Authority**: OpenCode never receives task without explicit PM authorization. Control returns to human between agent actions.

### 4.3 Orchestrator Implementation

workflow.py CLI with step-advance pattern:

```bash
python3 workflow.py --init session/todoist-wrapper --objective "Create Electron app for Todoist"
python3 workflow.py --advance session/todoist-wrapper  # -> PLAN
python3 workflow.py --approve session/todoist-wrapper  # -> IMPLEMENT
python3 workflow.py --advance session/todoist-wrapper  # -> REVIEW
```

Coder step: opencode run returns conversational text. Script extracts markdown code blocks with filenames, writes to workspace/. Cleaning functions strip Hermes Agent CLI overhead and OpenCode ANSI/headers.

### 4.4 First Cycle: Todoist Electron Wrapper

Objective: Minimal Electron wrapper for Todoist.com (1200x800, frameless, custom title bar, UA spoofing).

**Successes:**

- Thorough plan: security (contextBridge, no nodeIntegration), error handling, UA spoofing
- Clean code: main.js, preload.js (draggable title bar overlay), package.json (Electron v33)
- Full cycle ~8 minutes, zero manual intervention post-approval
- Git initialized at session root (artifacts) and workspace/ (code diffs)

**Failures Fixed:**

- Deep nesting: OpenCode prefixed workspace/ -> workspace/workspace/main.js. Fixed by stripping prefixes.
- Verdict parsing: instruction examples (VERDICT: APPROVED) leaked into output. Fixed by filtering instruction lines.
- Stray node_modules: 271MB under skill scripts from test run.
- Session state sync: do_approve saved AUTHORIZE before IMPLEMENT. If OpenCode hung, state stuck. Fixed by deferring save.

### 4.5 Code Quality Standards (Reviewer Prompt)

8-point standard: descriptive names, error handling required, no hardcoded secrets, input safety, demo boundary, cross-platform fallbacks, well-known dependencies, comments on non-obvious logic.

## 5. Diagnosis

Opencode run is conversational, not file-writing - requires markdown block extraction. Google models route poorly through OpenCode (timeouts) but work via Hermes. Free tier (opencode/deepseek-v4-flash-free) responds in 6-10 sec. State machines scale better than turn-taking for 3+ agents. Artifact cleaning critical - prompt instructions leak into output.

## 6. Preliminary Assessment

Orchestrator functional with crash-safe state machine. First cycle produced working Electron app. Artifact-driven approach provides complete audit trail.

## 7. Solution Summary

- Designed 3-role, 7-state workflow with artifact gates
- Implemented workflow.py with step-advance CLI
- Extracted code from conversational OpenCode output via markdown blocks
- Completed first cycle: Todoist Electron wrapper (COMPLETE with decision.md override)
- Documented 8-point code quality standard
- Skill at ~/.hermes/skills/software-development/project-manager-assistant/ (v0.3)

## 8. Verification Plan

- Test recovery from OpenCode timeout
- Add knowledge/RAG agent
- Fix stray scripts/workspace/ directory

## 9. Pending Actions

- Fix scripts/workspace/ stray directory cleanup
- Add error recovery for OpenCode timeout
- Make --advance for AUTHORIZE flow automatically into IMPLEMENT
- Add knowledge/RAG agent

## 10. Recommendations

- Use OpenCode free tier for programmatic calls (reliable, fast)
- Avoid Google models via OpenCode (routing timeouts)
- Aggressively strip prompt instructions from agent outputs
- State machine > turn-taking for multi-agent workflows
- Artifact-driven design enables audit and recovery