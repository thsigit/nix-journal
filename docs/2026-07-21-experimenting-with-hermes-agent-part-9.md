# Experimenting with Hermes Agent - Part 9

*Thirteen turns to a working editor*

**Date:** 2026-07-21  
**Author:** Codebot  
**Topic:** text-editor, iteration, code-review, syntax-highlighting, prototyping  

## 1. Objective

Build single-file browser text editor: load file, edit, save back. Syntax highlighting (3+ languages), line numbers, dark theme. No build tools.

## 2. Background

Straightforward project that took 13 workflow turns and 3 revision cycles across multiple sessions.

## 3. Problem

Repeated revision cycles for same bug classes. Coder produced logic bugs then completeness bugs. Reviews caught issues not visible at runtime initially.

## 4. Work Performed

### 4.1 Round 1: Plan
- Detailed plan: textarea-over-pre highlighting, VS Code palette, Ctrl+S/Ctrl+O shortcuts, tab-to-spaces
- Architecture: HTML structure, CSS layout, regex highlighters (JavaScript, Python, HTML)
- Estimate: 500-600 lines
- PM approved

### 4.2 Round 2: Build
- Coder produced editor.html (410 lines, full structure)
- Looked complete, sent to review

### 4.3 Round 3: Rejection 1
- Critical bug: escapeHtml() before regex matching
- All ", <, > already ", <, > when highlighter runs
- String highlighting non-functional, HTML tags/attributes broken
- Double-escaping in token replacement callback
- Verdict: REVISION REQUESTED

### 4.4 Round 4: Fix Attempt 1
- Coder produced new editor.html

### 4.5 Round 5: Rejection 2
- Second attempt smaller (272 lines, minified CSS)
- Worse: no event listeners wired (openBtn, saveBtn, langSelect, fileInput, textarea)
- Static HTML page, no keyboard shortcuts, no tab insertion
- Diff truncated mid-expression at openBtn.addEventListener('click'
- Verdict: REVISION REQUESTED

### 4.6 Root Cause Analysis
- First implementation: logic bug (highlighting order)
- Second: completeness bug (half file missing)
- Reviews caught subtle issues (escapeHtml ordering) and completeness (truncation)

### 4.7 Final Resolution
- Additional cycles outside these sessions eventually shipped working version
- Lesson: 13-turn edit-a-thon for "simple" single HTML file

## 5. Diagnosis

EscapeHtml before tokenization breaks all delimiter-based highlighting. Output truncation loses event wiring. Reviews essential - caught issues invisible at first glance. Minified/compact code correlates with missing functionality.

## 6. Preliminary Assessment

Final version shipped separately. 13 turns for nominally simple project. Reviews most valuable component.

## 7. Solution Summary

- Plan: solid architecture, textarea-over-pre technique
- Build 1: logic bug (escape order)
- Build 2: completeness bug (truncated, no events)
- Reviews caught both bug classes
- Eventually resolved in follow-up cycles

## 8. Verification Plan

- Test final editor.html in browser
- Verify syntax highlighting for JS, Python, HTML
- Confirm file load/edit/save, line numbers, dark theme
- Test keyboard shortcuts

## 9. Pending Actions

- None (resolved in follow-up)

## 10. Recommendations

- Tokenize before escaping for delimiter-based highlighting
- Monitor Coder output for truncation (buffer limits)
- Reviews catch subtle logic bugs and completeness gaps
- Compact/minified output often indicates missing functionality
- Simple projects can require many cycles when quality gates work