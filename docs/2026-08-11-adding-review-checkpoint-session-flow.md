# Editing the `goal` Command: Adding a Review Checkpoint to the Session Flow

**Date:** 2026-08-11  
**Author:** Codebot  
**Topic:** OpenCode, command, session, workflow, config  

---

## 1. Objective

Modify OpenCode's `goal` command so that the user can review the work before the session continues. Previously the command let the assistant declare a goal reached and immediately ask about continuing; the fix inserts a mandatory review checkpoint between "work looks done" and "what happens next."

## 2. Preface: How OpenCode Commands Work

OpenCode commands are the `/name` shortcuts typed in the chat interface. Each one is a plain markdown file that becomes a prompt when invoked. They live in command directories:

| Scope    | Path                                              |
| -------- | ------------------------------------------------- |
| Project  | `.opencode/command/<name>.md` or `.opencode/commands/<name>.md` |
| Global   | `~/.config/opencode/command/<name>.md` or `~/.config/opencode/commands/<name>.md` |

The loader scans for `**/*.md` inside those folders; both singular and plural directory names are accepted. The file is named after the command, so `/goal` maps to `goal.md`.

Commands are user-space. OpenCode ships with a set of built-in commands, but `goal` is not one of them - it is a user-defined command that the user created for their own session protocol. Commands are distinct from agents and skills: agents are personas with their own model, mode, and permissions, and skills are packaged instruction files for specialized workflows. A command is neither - it is simply a reusable prompt triggered with `/name`. That said, the three extension points share a key property: just as users can define their own agents (`.opencode/agent/<name>.md`) and skills (`.opencode/skill/<name>/SKILL.md`), users can create their own commands by dropping a markdown file into a command directory. The `goal` command is a direct example of that pattern - a small, user-authored file that encodes a personal workflow.

Each command file has optional YAML frontmatter and a required body:

```markdown
---
description: One sentence describing what the command does.
agent: build
---

(The prompt opencode runs when the command is invoked. $ARGUMENTS is replaced
with whatever the user typed after the command.)
```

Commonly used frontmatter fields are `description`, `agent`, `model`, `variant`, and `subtask`. Configuration is read once at startup, so after editing a command file you must quit and restart OpenCode for the change to take effect.

## 3. Background

The `goal` command encodes a session protocol: it forces the assistant to anchor every session to an explicit, reviewable goal instead of drifting. The original workflow had three steps:

1. Cite today's date.
2. Explicitly express the goal of the session.
3. When the goal is reached, ask whether to continue the session ("session bonus") or start a new goal/session.

The protocol lives at `~/.config/opencode/command/goal.md` (singular `command`, which OpenCode accepts alongside the plural form).

## 4. History

The command was created to enforce goal-oriented sessions. It worked well as a discipline tool, but its closing step conflated two very different events: *presenting the result* and *deciding what to do next*. Both were triggered at the same moment, by the assistant alone.

## 5. Symptoms

During a session that used the `goal` protocol, the assistant completed a task, declared the goal complete, and asked the session-bonus question immediately. The user pushed back:

> "I haven't reviewed the goal yet. Goal is not completed. You did well, but the pooled `pending_actions.txt` and `recommendations.txt` have lost their context."

Two problems surfaced:

- The goal was judged complete by the assistant, not confirmed by the user.
- Because the session-bonus question fired at the same time as the "done" declaration, the user was asked to make a continuation decision before reviewing what was actually delivered.

The user did want the outcome of the task (the two pooled files), but only after a fix - the files needed per-source context - not because the flow was wrong. This was exactly the failure mode the command was supposed to prevent: declaring completion without a review gate.

## 6. Work Performed

### 6.1 Locating the command

The command was not a skill; it lives in the OpenCode command directory. Global commands scan both `command/` and `commands/`, and on this machine the active file is `~/.config/opencode/command/goal.md`.

### 6.2 First revision (incomplete)

The first edit added a "review at any time" step and rewrote the closing step to ask the user to review what was accomplished before asking about continuing. The wording was still soft: it did not forbid the assistant from proceeding on its own judgment, so the gate was not enforceable.

### 6.3 Second revision (the fix)

The command was rewritten so the review is a hard checkpoint, not an optional courtesy:

```markdown
When I start a new session:
1. Cite today's date.
2. I must explicitly express the goal of this session, then confirm with the
   user that the goal is correct before starting work.
3. I can review my progress toward the goal at any time when asked.
4. When I believe the goal is reached, I must NOT declare it complete or ask
   about continuing. Instead, present a concise review summary of what was
   done and explicitly ask the user to review it. Do not proceed until the
   user confirms the goal is complete or says what to adjust.
5. Only after the user confirms the goal is complete, ask if they want to
   continue this session (call it "session bonus"), or if they want to start
   a new goal/session.
```

The two behavioral changes that matter:

- Step 2 gains an upfront confirmation, so the goal is agreed before any work.
- Step 4 forbids declaring completion and removes the session-bonus question from the completion moment. The assistant must present a summary and wait.

## 7. Diagnosis

The root cause was a missing state transition in the protocol: the command jumped from "work done" to "what next" with no user-confirmed state in between. The assistant's confidence in its own output was treated as sufficient evidence of completion, which bypassed the whole point of having an explicit goal in the first place. The fix inserts an explicit, blocking review state that only the user can advance past.

## 8. Mitigation Plan

- Adhere strictly to the revised command in all future sessions: never ask the session-bonus question before the user has reviewed and confirmed the goal.
- Treat the review summary in step 4 as mandatory output - a concise list of what was done, not just a question.
- If the user finds gaps during review, continue work under the same goal rather than starting a new one.

## 9. Verification Plan

- Trigger the command flow in a live session and confirm the assistant cites the date, states the goal, and waits for confirmation before working.
- After work appears complete, verify the assistant presents a review summary and does not ask about continuing until the user confirms.
- Restart OpenCode so the edited command file is loaded, since config is read once at startup.

## 10. Pending Actions

- None. The revision is complete and the file is saved at `~/.config/opencode/command/goal.md`.
- The change takes effect on the next OpenCode restart.

## 11. Recommendations

- Keep the review gate explicit - "I must NOT declare it complete" - because soft wording let the assistant skip the checkpoint in practice.
- Run a live test after the next restart to confirm the new flow behaves as specified.
- Consider applying the same review-before-continue discipline to custom agent prompts that produce multi-step deliverables.
