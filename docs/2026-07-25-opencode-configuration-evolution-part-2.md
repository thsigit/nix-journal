# OpenCode Configuration Evolution - Part 2

*Persistent context vs fresh-start problem*

**Date:** 2026-07-25  
**Author:** Codebot  
**Topic:** OpenCode, config, session, skills, homelab, NixOS  

---

## 1. Objective

Solve the fresh start problem in OpenCode where every new session begins with blank context.

## 2. Background

Every new AI coding session requires re-explaining workdir, name, preferences. Agent forgets everything next session. Three-layer persistent context solution implemented.

## 3. Problem

No persistent memory across OpenCode sessions. Manual context re-establishment required each time.

## 4. Work Performed

### 4.1 Instructions Mechanism
OpenCode opencode.json supports instructions field pointing to markdown file. Loads as system context every session automatically.
```json
{
  "instructions": ["~/.config/opencode/CONTEXT.md"]
}
```
CONTEXT.md becomes agent persistent memory: user identity, workdir, project locations, preferences.

### 4.2 Username Field
Added "username": "sigit" to opencode.json. Injects user identity into system context before first message.

### 4.3 Custom Startup Skills
OpenCode skill system supports startup-context skill at ~/.config/opencode/skills/startup-context/SKILL.md. Skills load on-demand when task matches description, providing fallback when static CONTEXT.md insufficient.

### 4.4 Remote Context via SSH
CONTEXT.md includes startup action: SSH into homelab and read repository files at /srv/repo/nix-lab. AGENTS.md, README.md, session files become part of agent thinking space from first token.

## 5. Diagnosis

Fresh start problem solved by configuration, not magic. Three fields in opencode.json, one markdown file, one skill.

## 6. Preliminary Assessment

Configuration-based persistence works. Remote context loading eliminates manual context transfer.

## 7. Solution Summary

Three-layer persistence: instructions file, username field, startup skill. Remote SSH context loading for homelab repo.

## 8. Verification Plan

Start new OpenCode session. Verify context loads automatically. Test homelab repo access.

## 9. Pending Actions

Refine CONTEXT.md content. Test startup-context skill activation.

## 10. Recommendations

Use instructions field for static context. Use skills for dynamic/conditional context. Include remote repository access in startup actions.
