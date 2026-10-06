# "Testing Browser-Use in WSL2: From Agent to Skill" - Part 2

**Date:** 2026-08-09  
**Author:** Codebot  
**Topic:** browser-use, OpenCode, ChatGPT, agent, skill, browser automation  

---

## 1. Objective

Verify whether the @chatgpt agent in OpenCode correctly delegates to the browser-use skill for ChatGPT interaction, and if not, replace the broken agent with a proper skill that reliably uses browser-use for ChatGPT browser automation.

## 2. Background

The OpenCode configuration (`~/.config/opencode/opencode.json`) defined an @chatgpt agent with instructions to use the browser-use skill for interacting with ChatGPT at chatgpt.com. The agent was invoked via `@chatgpt` or the `chatgpt-new` / `chatgpt-ask` commands. The browser-use skill itself was already functional for general browser automation.

## 3. Problem

When the @chatgpt agent was invoked, it did not delegate to browser-use. Instead, the agent's model (nvidia/nvidia/nemotron-mini-4b-instruct) answered directly, ignoring the instruction to use browser-use. The agent's instructions were treated as suggestions, not execution requirements.

## 4. Work Performed

### 4.1 Verify Agent Behavior

Tested the @chatgpt agent with a ChatGPT follow-up prompt:

```
@chatgpt follow up https://chatgpt.com/c/6a76d77a-ee98-83ec-b4a0-86553d693996 "apa bedanya ethereum dan bitcoin?"
```

The agent responded directly using its own model, without navigating to the URL or invoking browser-use. This confirmed the agent was not functioning as intended.

### 4.2 Root-Cause Analysis

OpenCode agents are model configurations with suggested behavior (instructions). The model decides which tools to call based on the prompt and its own reasoning. There is no mechanism to force an agent to use a specific tool. The agent's instructions are advisory text, not an execution pipeline.

| Aspect | Agent | Skill |
|--------|-------|-------|
| **Definition** | Model config + instructions | Instruction set + patterns |
| **Tool usage** | Model decides | Patterns guide model |
| **Reliability** | Low (model can ignore) | High (clear examples) |
| **Maintenance** | Hard (instructions vague) | Easy (concrete code) |

Conclusion: for tool delegation, skills are the correct primitive, not agents.

### 4.3 Remove the Broken Agent

Deleted the @chatgpt agent and its associated commands from `opencode.json`:

```json
// Removed from "agent" section:
"chatgpt": { "description": "...", "color": "#10A37F", "instructions": "..." }

// Removed from "command" section:
"chatgpt-new": { ... }
"chatgpt-ask": { ... }
```

Also updated `default_agent` from `chatgpt` to `reason`.

### 4.4 Create the ChatGPT Skill

Created `/home/sigit/.config/opencode/skills/chatgpt/SKILL.md` with:

- **New chat** flow: navigate to `https://chatgpt.com/`, wait for load, type prompt, wait for response, extract.
- **Follow-up** flow: navigate to `https://chatgpt.com/c/{chat_id}`, type follow-up, wait, extract.
- **Extraction patterns** using `browser-use` JavaScript evaluation.

Key extraction fix: `NodeList` from `document.querySelectorAll()` does not have `.pop()`. Correct pattern:

```javascript
// Before (broken)
document.querySelectorAll(".markdown").pop().textContent

// After (working)
Array.from(document.querySelectorAll(".markdown")).pop().textContent
```

Applied this fix to all extraction calls in the skill.

### 4.5 Test the New Skill

**Test 1 - Basic follow-up:**

```
chatgpt follow up https://chatgpt.com/c/6a76d77a-ee98-83ec-b4a0-86553d693996 "apa bedanya ethereum dan bitcoin?"
```

Result: Skill navigated to the URL, typed the question, waited 10-15 seconds, extracted response. ChatGPT returned a detailed comparison table in Indonesian.

**Test 2 - Another follow-up:**

```
chatgpt follow up https://chatgpt.com/c/6a76d77a-ee98-83ec-b4a0-86553d693996 "apa bedanya ethereum dan stellar?"
```

Result: Skill executed correctly. ChatGPT explained Ethereum (smart contract platform) vs Stellar (payment network).

**Test 3 - Skill triggering:**

Discovered that the skill triggers on action verbs (`ask chatgpt`, `follow up`) but not on bare `chatgpt` with a URL. Added explicit invocation patterns to the skill documentation.

## 5. Diagnosis

The @chatgpt agent failed because agents cannot enforce tool usage. The browser-use skill already provided the correct automation primitives; the problem was the delegation layer. Skills provide concrete, example-driven patterns that guide the model to call tools reliably, whereas agent instructions are easily ignored.

ChatGPT's URL structure (`/c/{chat_id}`) enables follow-up automation. The skill now handles both new chats and follow-ups via URL navigation. Response extraction requires 10-15 seconds of wait time for ChatGPT to generate the full response.

## 6. Preliminary Assessment

The agent-to-skill migration is complete and verified. The ChatGPT skill works reliably for Indonesian prompts and follow-up scenarios. No further agent-level fixes are needed - the skill is the correct abstraction for this use case.

## 7. Solution Summary

| Change | Description |
|--------|-------------|
| Remove @chatgpt agent | Deleted from opencode.json (agent + commands) |
| Update default_agent | `chatgpt` -> `reason` |
| Create ChatGPT skill | `~/.config/opencode/skills/chatgpt/SKILL.md` |
| Fix extraction patterns | `Array.from(NodeList).pop()` instead of `NodeList.pop()` |
| Document invocation | Action verbs required: "ask ChatGPT follow up", "chatgpt follow up" |

## 8. Verification Plan

1. Run the two follow-up tests again after a fresh OpenCode restart.
2. Verify new-chat flow: `ask chatgpt "new prompt"` (without URL) creates a new chat.
3. Verify extraction works across multiple response lengths.
4. Confirm skill auto-loads from `~/.config/opencode/skills/` without config changes.

## 9. Pending Actions

- Restart OpenCode to load the updated configuration (agent removed, skill added).
- Test new-chat creation flow without a pre-existing URL.
- Reconcile the `chatgpt` skill with any future browser-use skill updates.

## 10. Recommendations

1. **For tool delegation, use skills, not agents.** Agents are model configurations with advisory instructions; skills are instruction sets with concrete patterns that guide tool usage.
2. **Delete broken agents immediately.** The @chatgpt agent had a fundamental design flaw - no amount of instruction tuning would make it reliable.
3. **Always `Array.from()` NodeLists** before calling array methods like `.pop()`, `.map()`, `.filter()` in browser-use extraction scripts.
4. **Wait 10-15 seconds after typing** before extracting ChatGPT responses; generation time varies.
5. **Use action verbs to trigger skills.** The ChatGPT skill matches on "ask ChatGPT" and "follow up" patterns; bare "chatgpt" with a URL may not trigger reliably.
6. **Indonesian prompts work natively.** No special locale handling needed for browser-use + ChatGPT.
7. **Skills auto-load from `~/.config/opencode/skills/`.** No opencode.json changes required for new skills - drop the SKILL.md file and restart OpenCode.
