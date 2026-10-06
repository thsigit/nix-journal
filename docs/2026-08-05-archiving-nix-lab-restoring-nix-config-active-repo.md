# Archiving Nix Lab And Restoring Nix Config As The Active Repo

**Date:** 2026-08-05  
**Author:** Codebot  
**Topic:** homelab, NixOS, migration, maintenance, refactor, workflow, OpenCode, skills  

---

## 1. Objective

Resolve repository path mismatch: active config moved from /srv/repo/nix-lab to /srv/repo/nix-config, but agent skill, memory, and startup context still referenced old path.

## 2. Background

User ran SSH homelab "cd /srv/repo/nix-lab && cat README.md" -- worked but repo was archived. Real working repo at /srv/repo/nix-config. Three layers needed update: agent skill, Mem0 memory, startup context.

## 3. Problem

Stale path in skill, memory, and CONTEXT.md would silently target wrong repo every session.

## 4. Work Performed

### 4.1 Updating the Skill
ssh-homelab skill provides instruction: when user says "go to homelab", prefix remote commands with SSH homelab "cd /srv/repo/nix-config && <command>". Skill file had four references to nix-lab needing replacement with nix-config:
- Description
- Working directory instruction
- SSH template
- Notes section

### 4.2 Updating Memory and Startup Context
Mem0 memory updated: "Active homelab repository is /srv/repo/nix-config; previous /srv/repo/nix-lab is archived and no longer active."

Startup context file (CONTEXT.md) updated to point required startup action at correct paths:
- /srv/repo/nix-config/README.md
- /srv/repo/nix-config/AGENTS.md
- Session files at /srv/repo/nix-config/sessions/
- .md files in /srv/repo/nix-config/

## 5. Diagnosis

Skills are code -- when infrastructure moves, skills need same updates as config files. Startup context loads first -- wrong repo means agent works on archived files before user notices. Mem0 remembers -- stale facts propagate quietly. "Go to homelab" command is a contract -- skill, memory, startup context must honor with same truth.

## 6. Preliminary Assessment

All three layers updated. Future sessions will target correct repo.

## 7. Solution Summary

Skill, memory, and CONTEXT.md updated from nix-lab to nix-config. Contract honored.

## 8. Verification Plan

Start new session. Verify "go to homelab" targets nix-config. Check memory retrieval.

## 9. Pending Actions

None.

## 10. Recommendations

Treat skills as code requiring updates on infrastructure changes. Audit startup context after repo migrations. Update Mem0 when canonical paths change.
