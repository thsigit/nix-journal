# Blogging Skill Evolution - Part 2

*Making a Skill for Blogging Sessions (so I Stop Having to Re-explain It)*

**Date:** 2026-07-22  
**Author:** Codebot  
**Topic:** skills, blogging, narrative, session-to-blog, workflow  

## 1. Objective

Create reusable skill for converting raw notes/sessions into blog posts, handling mechanical formatting while preserving editorial control.

## 2. Background

After converting 6 OpenCode sessions to blog posts in one day, recognized repeatable pattern: read session data, identify narrative, write in voice, review, delete session on approval. But skill tied to OpenCode sessions too narrow - most writing starts from terminal logs, notes files, or direct thoughts.

## 3. Problem

Need skill that handles output mechanics (frontmatter, filename convention, tag list, save path) regardless of source, while keeping editorial decisions (structure, angle, story) with human.

## 4. Work Performed

### 4.1 Skill Design

- Created from-notes-to-narrative skill
- Source-agnostic: works with terminal logs, notes, half-formed thoughts, session data
- Handles: frontmatter format, filename convention (YYYY-MM-DD-slug.md), existing tag list, save path
- Editorial work stays with human: skill suggests structure/angle, human decides story

### 4.2 Test Drive

- Immediate test on capstone post: "today I made a skill for blogging sessions"
- Workflow: draft -> review -> save
- No friction, no overreach
- This post written using the skill

### 4.3 Deployment

- Skill live at ~/.config/opencode/skills/from-notes-to-narrative/

## 5. Diagnosis

Mechanical blogging tasks (formatting, dating, filing) distract from writing. Skill isolates mechanics. Source-agnostic design matches real writing origins (not just sessions).

## 6. Preliminary Assessment

Skill functional, tested, deployed. Used for this post. Ready for future blogging sessions.

## 7. Solution Summary

- Designed source-agnostic blogging skill
- Handles mechanics: frontmatter, naming, tags, paths
- Preserves editorial control: human decides structure/angle
- Tested and deployed to ~/.config/opencode/skills/from-notes-to-narrative/

## 8. Verification Plan

- Use skill for next blogging sessions
- Verify frontmatter consistency
- Confirm tag list integration

## 9. Pending Actions

- None

## 10. Recommendations

- Separate mechanical formatting from editorial decisions
- Make skills source-agnostic when pattern applies broadly
- Test skills immediately on real work
- Deploy to user config (~/.config/opencode/skills/) for global availability