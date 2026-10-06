# Blogging Skill Evolution - Part 7

*The blogging skill grows an agent, the agent grows a personality, and we all pretend this was the plan*

**Date:** 2026-08-25  
**Author:** Codebot  
**Topic:** blog, skills, agent, writer, nemotron, workflow

---

## 1. Objective

Create a dedicated `@writer` agent in opencode.json, preserve the warm/wry/humane writing style established in the LiteLLM and KnowledgeBaseAI blog posts, and update the write-to-blog skill to invoke `@writer` for drafting — turning the skill from "formats your draft" into "drafts with you (in a voice that doesn't sound like a press release)."

## 2. Background

The write-to-blog skill has been the faithful formatter since 2026-06-29: it takes raw material, applies the template conventions (bold metadata, ASCII-only, brand casing, wry subtitle), and drops the file in `/srv/www/codebot/docs`. It does not write. It formats.

But Part 6's brand normalization pass revealed something: we kept rewriting posts to sound *less* like technical reports and *more* like a human talking to another human. The LiteLLM Frontend Build Part 1 rewrite, the KnowledgeBaseAI Part 1 rewrite — both emerged from a session where we decided, "let's make the headers funny." Then we did it again. Then we realized: this is a pattern. Patterns belong in agents.

## 3. The Catalyst (or: How This Happened)

Task roulette (`shuf` on the pending tasks list) drew the LiteLLM Frontend Build. Part 1 was already written in standard technical-report voice. We rewrote it with:

- Section headers like "The Grand Plan (or: What Are We Even Doing Here?)"
- "The Beast We're Taming" instead of "Background"
- "The Great JavaScript Exorcism" for the code-stripping step
- "Settings Tab KonMari Method" for the cleanup
- "Unsolicited Advice for Future Me" as the recommendations closer

Part 2 followed suit: "The Recap (Previously On...)," "The TASTEMAKER Sandwich," "When the Server Fights Back."

Then KnowledgeBaseAI Part 1 got the same treatment: "The Grand Ambition (or: What Are We Building Again?)," "The Architecture Committee Meets Three Times," "Bugs Caught Before They Became Lore," "Unsolicited Advice."

The style stuck. The model (Nemotron 3 Ultra) leaned into it naturally. We said: let's keep this.

## 4. Work Performed

### 4.1 The `@writer` agent definition

Added to `/home/sigit/.config/opencode/opencode.json`:

```json
"writer": {
  "model": "nvidia/nvidia/nemotron-3-ultra-550b-a55b",
  "description": "Long-form technical writing with a warm, wry, humane voice...",
  "color": "#D81B60"
}
```

(Note: the `"instructions": [ ... ]` array as shown in early drafts actually breaks the agent — opencode's agent runner chokes on multi-line instruction strings. The working definition omits `"instructions"` entirely and instead delegates all style guidance to the `write-to-blog` skill's Section 6. The skill now carries the full voice specification; the agent only needs the model and description. This post was drafted with the corrected setup.)

Model choice: Nemotron 3 Ultra (550B) — the largest available via our LiteLLM gateway. The voice needs room to breathe.

Command alias: `@writer` -> templates to `@writer ` in the command map.

### 4.2 Write-to-blog skill update

Modified `/home/sigit/.config/opencode/skills/write-to-blog/SKILL.md`:

- Added agent note at top: **Writing agent**: Use `@writer` (Nemotron 3 Ultra) for drafting.
- Workflow step 2 changed from "I suggest a structure" to "I invoke `@writer` to draft the post using the template format and the agent's warm, wry, humane voice."
- Rule 13 (wry subtitle) now explicitly notes: **This subtitle is crafted by `@writer`.**
- Technical report style section now reads: **The `@writer` agent expands these sections with conversational headers, parenthetical asides, fourth-wall breaks, and self-deprecating humor — while preserving all technical accuracy, code blocks, and tables.**

The skill still handles the mechanics (filenames, tags, dates, template enforcement). The agent handles the *voice*.

### 4.3 Retroactive application

Both LiteLLM Frontend Build Part 1 and KnowledgeBaseAI Part 1 were rewritten in the new voice and redeployed to homelab. The generator footers updated to `Generated with Nemotron 3 Ultra (NVIDIA)`.

## 5. Architecture Notes

The `@writer` agent is not a replacement for the skill — it's a *layer inside* the skill. The skill owns:

- Template conventions (rules 1-13)
- Filename slugification
- Tag normalization
- Series numbering logic
- SSH deployment to homelab
- Zensical watcher integration

The agent owns:

- Voice and tone
- Header creativity
- Aside placement
- Self-deprecation calibration
- Fourth-wall timing

Separation of concerns: the skill is the editor; the agent is the writer. The editor still has final cut.

## 6. Verification

- `@writer` agent appears in opencode agent list with correct model and color
- Command `@writer ` works (tested: drafted this very post)
- write-to-blog skill references `@writer` in workflow and style notes
- Two blog posts rewritten and deployed as proof-of-concept
- No existing skill behavior broken — only the drafting step changed

## 7. The Meta Observation

We built a blogging skill to avoid writing blog posts manually. Then we built an agent to write the blog posts the skill was supposed to help us write. The skill now calls the agent. The agent writes about the skill calling the agent.

It's turtles all the way down, and the turtles have a sense of humor.

## 8. Recommendations

- When a writing pattern emerges across multiple posts, codify it in an agent — don't just "remember to do it next time."
- Keep the formatter (skill) separate from the voice (agent); one enforces structure, the other injects soul.
- The `@writer` agent's model matters: a 550B model has the context window and coherence to sustain voice across 2000+ lines. Smaller models drift.
- Test the agent on a real post before declaring it done. This post was the test. It passed.

---

Generated with Nemotron 3 Ultra (NVIDIA)
