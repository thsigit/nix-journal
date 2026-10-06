# The mem0 Fleet Sync (or: We Stopped Pretending Polling Is Architecture)

**Date:** 2026-09-28  
**Author:** Codebot  
**Topic:** opencode, mem0, fleet sync, plugin

---

## 1. Objective
Stop polling, start publishing. Replace timer based mem0 sync with event driven publishing on session.end, keep task sync semantic, and prove the sync tools actually detect divergence instead of lying about it.

## 2. Background
The OpenCode v2 hub runs on three hosts - Windows native, DebianWSL, FedoraWSL - with a homelab archive. Mem0 lives under ~/.opencode/mem0 on each peer and a bare repo C:\Users\SIGIT\git\opencode-mem0.git. Tasks use sync-tasks.sh with a manual semantic trigger via task-triage and session-close. Mem0 had no reliable trigger and a sync script that could claim converged while still behind.

## 3. Problem
- No mem0 trigger. Users had to remember to sync.
- sync-tasks.sh and sync-mem0.sh suffered false success on 9p stale refs; verify_converged was missing from tasks.
- Plugin count was documented as 4 while we were actually heading to 5.
- Stale gitignore entries pointed at deleted homelab remotes.
- Umbrella mirrors and bundles were out of date after the changes.

## 4. Work Performed
### 4.1 Script fixes and creation
Created scripts/sync-mem0.sh and scripts/sync-mem0.ps1 mirroring sync-tasks contract with auto-commit, fetch, ff-only push, exit codes 0/1/2, lock, mid-merge refusal. Ported verify_converged into sync-tasks.sh.

### 4.2 Fleet sync plugin
Created plugins/fleet-sync/index.ts, package.json, tsconfig.json. Hooks session.end only - not session.idle. Shells out to ~/.opencode/bin/sync-mem0.* non-blocking, deduped per session.

### 4.3 Skills updated
Updated skills/session-close/SKILL.md to publish mem0 after session_done. Updated skills/task-triage/SKILL.md to document mem0 store and event trigger. Synced bundled copies under plugins/opencode-task-manager/skills.

### 4.4 Invariant and docs
Bumped 4-plugin invariant to 5 in skills/sync-opencode/SKILL.md, README.md, scripts/bootstrap-wsl.sh, skills/wsl-reset/SKILL.md. Fixed .gitignore stale remote block and added mem0/ dist/ ignores.

### 4.5 Deploy
Windows: plugin files installed, 5-plugin check passes. DebianWSL and FedoraWSL: plugins/fleet-sync installed, ~/.opencode/bin/sync-mem0.sh present, 5-plugin invariant confirmed.

### 4.6 Verification run
Verified verify_converged self-heals a stale host. End-to-end mem0 publish: Debian wrote unpublished memory -> published to 2fbbf66 -> Windows pulled cleanly. Harness test published a fresh memory fleet-wide. Test memories removed, mem0 back to 6 files.

### 4.7 Repo commit and mirror
Hub committed 11a2c56 fleet-sync: event-driven mem0 publishing, verify-converged fix, 5-plugin invariant. Bundled to homelab and fetched into /srv/repo/opencode-v2/config.git -> HEAD 11a2c56. Bundle stored at /srv/repo/archives/opencode-v2-hub-2026-09-28.bundle.

## 5. Diagnosis
False convergence was caused by missing remote check and 9p staleness. The fix is to compare local HEAD with git ls-remote and retry fetch. No timer needed; session.end is a solid boundary.

## 6. Preliminary Assessment
Sync tools now tell the truth. Mem0 publishes automatically on session close with a belt-and-braces second call from session-close skill. No polling.

## 7. Solution Summary
Event driven mem0 publishing via fleet-sync plugin on session.end plus verify_converged in both sync scripts. Plugin count documented as 5. Umbrella mirror refreshed.

## 8. Verification Plan
- Confirm mem0 HEAD matches remote on all three hosts after a session end.
- Ensure plugin fires once per session and duplicates are suppressed.
- Re-run harness with a fresh memory and verify no unpublished files remain.

## 9. Pending Actions
- Pull mem0 removal to DebianWSL and FedoraWSL; ensure HEAD 88a50ec everywhere.
- Refresh umbrella mirrors for tasks.git and mem0.git to homelab.
- Implement --force-reset in restore-umbrella.sh if needed later.

## 10. Recommendations
Keep session.end as the sole mem0 trigger. Do not reintroduce timers. Keep verify_converged in both scripts. Treat config and umbrella mirrors as explicit manual steps.

Generated with meta/muse-glimmer-30b by Meta
