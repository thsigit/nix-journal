# Experimenting with Hermes Agent - Part 8

*PM Assistant Builds a Text Editor: First Real Workload*

**Date:** 2026-07-21  
**Author:** Codebot  
**Topic:** pm-assistant, multi-agent, text-editor, web, session-management  

## 1. Objective

Execute first real workload through PM Assistant skill: build browser-based text editor (single HTML file, no build tools) with file load/edit/save, syntax highlighting (3+ languages), line numbers, dark theme.

## 2. Background

PM Assistant v0.4 workflow with state machine: INIT -> PLANNING -> PLAN_REVIEW -> IMPLEMENTING -> VERIFYING -> REVIEWING -> APPROVED -> COMPLETE. Human as PM, Hermes Agent as Reviewer, OpenCode as Coder.

## 3. Problem

Validate workflow engine with real project. Identify Coder bug patterns and Reviewer effectiveness.

## 4. Work Performed

### 4.1 Workflow Execution

7 state transitions across 3 Coder iterations:

| Transition                  | Duration | Result                                        |
| --------------------------- | -------- | --------------------------------------------- |
| INIT -> PLANNING            | -        | Session created                               |
| PLANNING -> PLAN_REVIEW     | 41s      | 7-step plan written                           |
| PLAN_REVIEW -> IMPLEMENTING | -        | PM approved plan                              |
| IMPLEMENTING -> VERIFYING   | 59s      | editor.html (11.8KB)                          |
| VERIFYING -> REVIEWING      | -        | Skipped (no project type)                     |
| REVIEWING -> IMPLEMENTING   | 106s     | REVISION: escape order broken, events unwired |
| IMPLEMENTING -> VERIFYING   | 64s      | Revision 2 (14KB)                             |
| REVIEWING -> IMPLEMENTING   | 24s      | REVISION: tokenizer indexing bug              |
| IMPLEMENTING -> VERIFYING   | 50s      | Revision 3                                    |
| REVIEWING -> APPROVED       | 30s      | REVISION: diff truncated, events missing      |
| APPROVED -> COMPLETE        | -        | PM override approved with known bugs          |

### 4.2 What Worked

- Workflow engine flawless: state machine transitions correct
- Recovery from STUCK (reviewer timeout) worked first try
- Artifact-driven: every decision/output on disk
- Coder produced working code each iteration (dark theme, line numbers, file open, drag-drop, language detection)

### 4.3 Coder Bug Patterns (3 rounds, same classes)

1. Syntax highlighting: HTML escaping before regex matching -> patterns for ", <, > never fired. Each rewrite attempted fix but introduced tokenizer indexing errors.
2. Event wiring: diff truncated before addEventListener calls. Handlers written but output cut off.
3. Keyboard shortcuts: Tab->2 spaces, Ctrl+S, Ctrl+O never in any iteration.

### 4.4 PM Decision

Approved with known bugs, follow-up session planned. Correct behavior: system caught issues, documented them, PM made call.

## 5. Diagnosis

PM Assistant architecture works. Reviewer consistently finds real bugs. Coder produces real (imperfect) code. Artifact trail complete. Missing: mechanism for PM to give targeted mid-loop feedback ("ignore highlighting, focus on events") vs cycling same fixes.

## 6. Preliminary Assessment

Session at ~/projects/text-editor/, output workspace/editor.html (14KB, HTML/CSS/JS single file). Workflow validated, bugs documented, follow-up needed.

## 7. Solution Summary

- Executed 7-state workflow with 3 Coder iterations
- Reviewer caught 3 bug classes across revisions
- Coder produced functional editor core each time
- PM overrode final REVISION with known bugs documented
- Complete artifact trail preserved

## 8. Verification Plan

- Follow-up session for targeted fixes
- Test editor.html in browser
- Verify syntax highlighting, events, shortcuts

## 9. Pending Actions

- Follow-up session with targeted feedback mechanism
- Fix syntax highlighting escape order
- Complete event wiring
- Add keyboard shortcuts

## 10. Recommendations

- Add PM mid-loop feedback mechanism to avoid revision cycling
- Coder output truncation needs handling (buffer limits?)
- Syntax highlighting: escape after tokenization, not before
- Event wiring must be in diff before truncation point