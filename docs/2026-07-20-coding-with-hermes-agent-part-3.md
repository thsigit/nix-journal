# Coding with Hermes Agent - Part 3

*Crash-safe PM Assistant upgrade*

**Date:** 2026-07-20  
**Author:** Codebot  
**Topic:** Hermes Agent, pm-assistant, orchestration, recovery, retrospective  

## 1. Objective

Upgrade project-manager-assistant skill to v0.4 with crash-safe recovery, configurable agent roster, and automatic retrospect reporting.

## 2. Background

v0.3 was fragile: OpenCode crash left session corrupt (traceback on stdout, status.json possibly unwritten, half-written workspace files). Models hardcoded in workflow.py. No automatic project closure report.

## 3. Problem

Three fragility points: (1) no error recovery - crash = manual cleanup, (2) hardcoded models - no cheap swap when provider overloaded, (3) no project closure artifact - learning lost.

## 4. Work Performed

### 4.1 Failure Recovery
- Added try/except wrapper around action dispatch in main()
- On any exception: write failure.md (error, traceback tail, recovery command), pin state to STUCK in status.json
- --advance detects STUCK, prints recovery hint instead of crashing
- --recover command re-runs failing state with clean workspace:
  - IMPLEMENT: wipes workspace/ (shutil.rmtree), re-inits git, calls coder fresh
  - CLARIFY/REVIEW: re-calls reviewer with same inputs
  - Other states: prints "nothing to recover"
- No auto-retry, no state rewind - deliberate single-command recovery for "one project a day" workflow

### 4.2 Agent Roster Configuration
- Created agents.yaml at skill root with two slots: reviewer, coder
- Each defines: command template ({prompt}, {model} placeholders), default_model, optional extra_args
- Zero-dependency: ~30-line fallback parser for flat key:value format (uses PyYAML if available, silent fallback)
- Per-session override: drop agents.yaml in session directory for project-specific models
- Example: swap coder to google/gemini-2.5-pro for one project, keep opencode/deepseek-v4-flash-free for others

### 4.3 Retrospect Report
- On COMPLETE entry, workflow.py writes retrospect.md automatically (templated, no LLM cost)
- Time-per-state table from status.json history timestamps
- Optional --retrospect --llm calls reviewer for "Lessons learned" paragraph
- Rest of report templated

### 4.4 README.md Quick Reference
- Every --status prints quirks doc path
- Human-scannable 6-section reference: CLI quick-ref, mental model, recovery flow, agents.yaml gotchas, retrospect caveats, session directory anatomy
- Complements 350-line SKILL.md (model-facing)

## 5. Diagnosis

try/except boundary (15 lines) transformed error UX from "read code" to "run --recover". Zero-dependency YAML parser worth 30 lines for skill portability. Mental model documentation (three verbs: --advance, --approve/--reject, --recover) was hardest but most valuable.

## 6. Preliminary Assessment

v0.4 crash-safe, model-swappable, generates retrospect. Features deferred to v0.5: parallel sub-tasks, cross-project dependencies, configurable state-time CLI flag.

## 7. Solution Summary

- Added crash recovery: failure.md + STUCK state + --recover command
- Added agents.yaml with zero-dependency parser and per-session override
- Added automatic retrospect.md on COMPLETE (templated + optional LLM analysis)
- Added human-readable README.md referenced by --status
- v0.4 feature complete for "one project a day, crash Tuesday, recover Wednesday"

## 8. Verification Plan

- Test --recover on simulated IMPLEMENT crash
- Verify agents.yaml override in session directory
- Check retrospect.md generation on COMPLETE
- Confirm --status prints quirks path

## 9. Pending Actions

- v0.5 features when requested: parallel sub-tasks, cross-project dependencies, state-time CLI flag

## 10. Recommendations

- Minimal try/except wrapper transforms error UX dramatically
- Zero-dependency config parsing enables skill portability
- Document mental model (verbs) explicitly for user adoption
- Separate human-readable docs (README) from model-facing docs (SKILL.md)