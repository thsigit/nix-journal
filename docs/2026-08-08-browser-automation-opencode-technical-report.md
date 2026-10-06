# "Testing Browser-Use in WSL2: Browser Automation for OpenCode" - Technical Report

**Date:** 2026-08-08  
**Author:** Codebot  
**Topic:** browser-use, OpenCode, WSL2, browser automation, skill  

---

## 1. Objective

Install, configure, and validate browser-use (a Python-based browser automation tool using Chrome DevTools Protocol) on WSL2, register it as an OpenCode skill, test end-to-end ChatGPT automation in English and Indonesian, and create reliable OpenCode agents for ChatGPT interaction.

## 2. Background

browser-use provides browser automation via CDP (Chrome DevTools Protocol). It ships with an OpenCode skill for seamless integration. The target environment is WSL2 on Windows, with Google Chrome running on the Windows host. The OpenCode configuration lives at `~/.config/opencode/opencode.json`.

## 3. Problem

The primary obstacle was the WSL2 networking boundary: Chrome on Windows binds its CDP endpoint to `127.0.0.1` on the Windows loopback interface. WSL2 cannot reach Windows localhost directly - the WSL2 gateway IP (`172.23.x.x`) is rejected by Chrome's loopback binding. Initial attempts to bridge this gap failed:

| Attempt | Method | Result |
|---------|--------|--------|
| 1 | `socat` port forwarding WSL2 -> Windows host IP | Chrome rejected non-localhost connections |
| 2 | `netsh interface portproxy` | Requires elevated privileges, not portable |
| 3 | `--remote-debugging-address=0.0.0.0` Chrome flag | Ignored by Chrome |

A secondary issue: browser-use's API changed from earlier versions, causing `navigate()` and `get_page_content()` calls to fail until the new API was discovered.

## 4. Work Performed

### 4.1 Install browser-use and Dependencies

Installed Python 3.12 explicitly via `uv` (uv defaults to older Python versions for tool installs), then installed browser-use:

```bash
uv python install 3.12
uv tool install browser-use --python 3.12
```

The install pulled 100+ packages including `browser-harness`, `browser-use-sdk`, and CDP bindings.

### 4.2 Register the OpenCode Skill

Ran the skill installer:

```bash
browser-use skill install
```

This wrote `SKILL.md` to multiple agent skill directories:
- `~/.config/opencode/skills/browser-use/SKILL.md`
- `~/.agents/skills/browser-use/SKILL.md`
- `~/.claude/skills/browser-use/SKILL.md`

The skill became available in OpenCode immediately after restart.

### 4.3 Resolve the WSL2 Networking Issue

Instead of connecting to an external Chrome instance, browser-use launches and manages its own Chrome process:

1. The daemon detects no running Chrome with CDP enabled.
2. Launches Chrome with `--remote-debugging-port` and opens `chrome://inspect/#remote-debugging`.
2. User ticks "Allow remote debugging" in the Chrome UI (one-time manual step per Chrome profile).
3. Daemon connects on retry.

This approach keeps the daemon and Chrome in the same network namespace, sidestepping the WSL-Windows CDP connectivity problem entirely.

### 4.4 Validate Core Automation Pipeline

Tested basic navigation and page inspection:

```python
browser-use <<'PY'
goto_url("https://example.com")
print(page_info())
PY
```

Output confirmed working:
```
{'url': 'https://example.com/', 'title': 'Example Domain', 'w': 1520, 'h': 720}
```

### 4.5 Test ChatGPT Interaction (English)

Navigated to `chatgpt.com`, completed manual login, then automated a query:

```python
browser-use <<'PY'
fill_input('textarea, [contenteditable="true"]', 'why the sky is blue?')
press_key('Enter')
PY
```

ChatGPT responded with a correct Rayleigh scattering explanation - end-to-end pipeline validated.

### 4.6 Test ChatGPT Interaction (Indonesian)

Verified non-English input handling:

```python
browser-use <<'PY'
fill_input('textarea, [contenteditable="true"]', 'apa bedanya cara kerja mesin injeksi dan mesin karburator?')
press_key('Enter')
PY
```

ChatGPT returned a detailed comparison table with ASCII diagrams - confirmed browser-use handles Indonesian prompts and long-form responses without special configuration.

### 4.7 API Migration: Old vs New

Discovered and documented the API changes:

| Old API (deprecated) | New API (current) |
|----------------------|-------------------|
| `navigate(url)` | `goto_url(url)` |
| `get_page_content()` | `js("document.body.innerText")` |
| `click(selector)` | `click_at_xy(x, y)` with coordinates from `js()` |

Additional gotchas:
- JS variable redeclaration in multi-statement scripts -> wrap in IIFE: `(() => { ... })()`
- Task agent sometimes returns empty results -> call browser-use directly in bash as fallback
- `page_info()` helper returns clean dict with `url`, `title`, `w`, `h` - useful for debugging

### 4.8 Create @chatgpt Agent (First Attempt)

Added a custom OpenCode agent:

```json
"chatgpt": {
  "description": "Browser automation agent that talks to ChatGPT via browser-use skill",
  "color": "#10A37F",
  "instructions": "You are a browser automation agent. Use the browser-use skill to interact with chatgpt.com..."
}
```

Issue: hardcoded `model: "nvidia/nemotron-mini-4b-instruct"` was sometimes unavailable. Fixed by removing the `model` field so the agent inherits the session's current model.

### 4.9 Analyze ChatGPT Session URL Structure

Discovered ChatGPT's session management pattern:

| Action | URL Pattern |
|--------|-------------|
| New chat | `https://chatgpt.com/` |
| Follow-up | `https://chatgpt.com/c/{uuid}` |

The "New chat" button has `data-testid="create-new-chat-button"` and navigates to `https://chatgpt.com/`.

### 4.10 Create Sub-Commands for Explicit Intent

Split the single agent into two commands to prevent context confusion:

| Command | Action | URL Pattern |
|---------|--------|-------------|
| `@chatgpt-new` | Navigate to `chatgpt.com/` first | `https://chatgpt.com/` |
| `@chatgpt-ask` | Stay on current page, type in input | `https://chatgpt.com/c/...` |

```json
"chatgpt-new": {
  "template": "@chatgpt-new ",
  "description": "Start NEW ChatGPT session and ask question"
},
"chatgpt-ask": {
  "template": "@chatgpt-ask ",
  "description": "Ask follow-up in existing ChatGPT chat"
}
```

### 4.11 Validate Sub-Command Behavior

| Test | Command | Expected | Result |
|------|---------|----------|--------|
| 1 | `@chatgpt-new apa itu Bitcoin?` | New session, fresh answer | Pass - full Bitcoin explanation |
| 2 | `@chatgpt-ask bagaimana cara membeli Bitcoin?` | Follow-up in same chat | Pass - contextual buying guide |
| 3 | `@chatgpt-new apa itu ethereum?` | New session, fresh answer | Pass - Ethereum vs Bitcoin comparison |

## 5. Diagnosis

The WSL2 networking failure was a classic network-namespace mismatch. browser-use's architecture (daemon + managed Chrome) is the correct solution - it avoids cross-namespace CDP connections entirely. The API migration issues stem from browser-use's rapid development cycle; the new API (`goto_url`, `js()`, `click_at_xy`) is more explicit and composable.

The @chatgpt agent design revealed a deeper principle: OpenCode agents are model configurations with advisory instructions, not execution pipelines. The model can (and does) ignore tool-usage instructions. The sub-command split (`@chatgpt-new` vs `@chatgpt-ask`) works because the template forces the model to emit the correct action sequence before browser-use is invoked.

## 6. Preliminary Assessment

All objectives met:
- browser-use installed and functional on WSL2
- OpenCode skill registered and auto-loaded
- ChatGPT automation working for English and Indonesian prompts
- Sub-commands provide reliable new-chat vs follow-up separation
- Health check (`browser-use doctor`) reports all green

The remaining risk is browser-use API stability - the project is pre-1.0 and breaking changes are expected.

## 7. Solution Summary

| Change | Description |
|--------|-------------|
| Install Python 3.12 explicitly | `uv python install 3.12` + `uv tool install browser-use --python 3.12` |
| Let browser-use manage Chrome | Daemon launches Chrome with CDP; user consents once via `chrome://inspect` |
| Register OpenCode skill | `browser-use skill install` writes to all agent directories |
| Migrate to new API | `goto_url()`, `js()`, `click_at_xy(x,y)` instead of deprecated methods |
| Split @chatgpt into sub-commands | `@chatgpt-new` (fresh session) vs `@chatgpt-ask` (follow-up) |
| Remove hardcoded model from agent | Agent inherits session model; avoids availability issues |

## 8. Verification Plan

1. Restart OpenCode; confirm `browser-use` skill loads without config changes.
2. Run `@chatgpt-new "test prompt"` - verify fresh ChatGPT session and response extraction.
3. Run `@chatgpt-ask "follow-up"` - verify context is preserved.
4. Test Indonesian prompt - verify non-English handling.
5. Run `browser-use doctor` - confirm daemon and browser connection healthy.
6. Monitor for browser-use updates; re-test after any version bump.

## 9. Pending Actions

- Watch browser-use release notes for breaking API changes.
- If browser-use adds native session-management helpers, refactor the sub-commands to use them.
- Consider a `chatgpt-extract` sub-command to pull full chat history via `js()` for long conversations.

## 10. Recommendations

1. **Let browser-use manage its own Chrome.** Don't fight WSL2 networking; the daemon + managed Chrome model is the intended architecture.
2. **Pin Python 3.12 explicitly.** `uv tool install --python 3.12` is mandatory; uv's default Python version is too old for browser-use's dependencies.
3. **One-time Chrome consent is unavoidable.** The `chrome://inspect/#remote-debugging` "Allow remote debugging" checkbox must be clicked once per Chrome profile.
4. **Use the new API (`goto_url`, `js()`, `click_at_xy`).** The old `navigate()`, `get_page_content()`, `click()` are removed.
5. **Split agents by intent, not by capability.** The `@chatgpt-new` / `@chatgpt-ask` pattern makes the URL navigation explicit and prevents context loss.
6. **Remove hardcoded `model` fields from agents.** Inherit the session model to avoid availability issues across environments.
7. **Call browser-use directly from bash when the Task agent returns empty.** The task agent's browser state may not transfer; direct CLI invocation is the reliable fallback.
8. **Indonesian (and other languages) work natively.** No locale or encoding configuration needed.
9. **Extract long responses in chunks.** Use `js("document.body.innerText.slice(0, 5000)")` to avoid truncation.
10. **`browser-use skill install` is global.** It writes to OpenCode, claude, codex, copilot, cursor, and Gemini skill directories - one install covers all.
