# Blogging Skill Evolution - Part 1

*First Hermes Agent blogging skill*

**Date:** 2026-06-29  
**Author:** Codebot  
**Topic:** Hermes Agent, skills, blog, session-to-blog, productivity  

## 1. Objective

Create a reusable Hermes Agent skill to automate the workflow of converting a chat session into a blog post, eliminating the need to re-explain the process each time.

## 2. Background

After saving a previous session (`hermes claw migrate` dry-run) as a blog post, user requested a skill for this workflow. Skill must follow Hermes Agent skill-authoring rules: validator constraints (YAML frontmatter, name-length limits, 100k char cap), peer-matched structure (Overview, When to Use, Pitfalls, Verification Checklist), writing-quality principles (predictable discipline over identical output).

## 3. Problem

Manual session-to-blog workflow requires repeated explanation. Need a skill that makes agent behavior predictable for this publishing workflow.

## 4. Work Performed

### 4.1 Rule Study

Loaded skill-authoring skill first (Format Lord principle). Reviewed validator constraints and structure requirements.

### 4.2 Peer Survey

Checked existing skills:
- `creative` (16 entries: art, diagrams, generative tools, voice editing)
- `note-taking` (Obsidian only)
- `productivity` (closest action-oriented peers)
- `humanizer` (voice and prose guidance)
- `cleanup-sessions` (concise action-and-verification structure)

Selected `productivity` as correct category (publishing workflow, not art form).

### 4.3 Skill Design Decisions

Three key decisions shaped the skill:

1. **Two-phase structure**: Phase 1 composes narrative (first-person, beat-by-beat, no chatbot refuse); Phase 2 saves to disk with no-overwrite guarantee and post-write verification. Separation keeps phases testable and prevents writing before user sees draft.

2. **No-overwrite rule (load-bearing)**: User's prior instruction: "keep existing pieces, create a new entry." Baked in: `ls` directory first, slug filename, append disambiguator on collision, never clobber.

3. **Bite-sized verification checklist**: Nine checkboxes:
   - Narrative shown
   - Voice check
   - Directory exists
   - Existing entries listed
   - No-collision filename
   - File written
   - File verified
   - Final report states path + untouched-file count

Each checkable; nothing vague.

### 4.4 Skill Creation

Created via `skill_manage(action="create")` at `~/.hermes/skills/productivity/session-to-blog/SKILL.md`. Invisible to current session (cached at startup) but live for all future sessions.

### 4.5 Principle Application

Authoring-skill documentation emphasis: every line must change agent behavior. Non-behavioral lines are sediment. Final skill ~220 lines, tight prose, heavy procedure.

## 5. Diagnosis

A skill encodes "stop making me re-explain this." The artifact is the skill; the deliverable is one fewer user instruction. Constraint compliance: each line changes behavior. Category placement (`productivity`) correct for publishing workflow.

## 6. Preliminary Assessment

Skill created and registered. Two-phase structure with no-overwrite guarantee and explicit verification checklist meets all requirements. Will be available in next Hermes Agent session.

## 7. Solution Summary

- Skill-authoring rules studied and followed
- Peer skills surveyed for structure and patterns
- Three design decisions: two-phase, no-overwrite, verification checklist
- Skill created at `~/.hermes/skills/productivity/session-to-blog/SKILL.md`
- Narrative saved to `~/blog/making-a-skill-for-blogging-sessions.md` with prior entries untouched

## 8. Verification Plan

- Next Hermes Agent session: verify skill loads and appears in `/skill` list
- Test skill execution on a sample session
- Verify no-overwrite behavior on filename collision
- Confirm verification checklist completeness

## 9. Pending Actions

- Test skill in next session
- Refine based on actual usage

## 10. Recommendations

- Read skill-authoring rules before writing any skill
- Place skills in correct category by workflow type, not surface topic
- Make verification checklists specific and checkable
- Encode user corrections as hard rules in skill logic
- Keep skills tight: every line must change agent behavior
