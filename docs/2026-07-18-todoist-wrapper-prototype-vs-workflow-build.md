# Coding with Hermes Agent - Part 2

*Todoist wrapper: prototype vs workflow build*

**Date:** 2026-07-18  
**Author:** Codebot  
**Topic:** Electron, todoist, prototyping, pm-assistant, workflow  

## 1. Objective

Build desktop wrapper for Todoist.com (1200x800, frameless, custom icon) and compare standalone prototype vs PM Assistant workflow-driven build.

## 2. Background

Simple Electron app request. Two approaches tested in 15 minutes: direct code generation vs structured PM Assistant workflow.

## 3. Problem

Need to evaluate whether workflow overhead provides value for simple projects.

## 4. Work Performed

### 4.1 Standalone Prototype
- Direct code request
- Result: minimal project in /home/sigit/workspace/
- Files: main.js (loads URL), preload.js (stub), 256x256 red rounded-square icon (pure Python)
- Run: npm start -> frameless, exit via Alt+F4
- Gaps: No UA spoofing (Todoist blocks Electron default UA), no window controls, preload skeleton

### 4.2 PM Assistant Build
- Same objective through PM Assistant workflow
- Reviewer wrote 7-step plan first
- Coder built to plan
- Result: polished implementation
  - Custom Chrome 120 User-Agent (avoids Todoist anti-bot blocking)
  - Preload injects semi-transparent draggable title bar with close button (backdrop-filter: blur)
  - 512x512 icon with white "T" on red background (pure Python)
  - Proper IPC for close button

### 4.3 Comparison
| Aspect | Standalone | PM Assistant |
|--------|------------|--------------|
| Speed | Faster | Few minutes more |
| UA Spoofing | Missing | Included |
| Window Controls | Alt+F4 only | Draggable title bar + close button |
| Icon | 256x256 red square | 512x512 styled "T" |
| Preload | Skeleton | Functional with IPC |
| Planning | None | 7-step plan caught edge cases |

## 5. Diagnosis

Planning step forced consideration of "what does frameless mean for daily use?" - caught Todoist UA blocking and missing window controls. Standalone build shipped but was incomplete for real use.

## 6. Preliminary Assessment

PM Assistant build accepted as canonical. Both sessions cleaned up. Workflow-driven approach worth extra time for production use.

## 7. Solution Summary

- Built two Electron Todoist wrappers
- Standalone: minimal, fast, incomplete
- PM Assistant: planned, polished, complete
- Accepted PM Assistant version as canonical

## 8. Verification Plan

- Test PM Assistant wrapper daily usage
- Verify UA spoofing prevents Todoist blocking
- Confirm frameless UX with title bar controls

## 9. Pending Actions

- None

## 10. Recommendations

- For disposable prototypes: standalone approach acceptable
- For daily-use tools: workflow-driven build worth overhead
- Planning step catches real-world edge cases (UA blocking, UX gaps)
- Frameless requires explicit window controls, not just Alt+F4