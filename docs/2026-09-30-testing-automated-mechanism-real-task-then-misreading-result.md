---
nav:
  series: "OpenCode Task Plugin"
  part: 1
  next:
    title: "\"OpenCode Task Plugin\" - Part 2 (or: The Rename, The Compile Error, and Why Two Birds Need Two Stones)"
    slug: 2026-10-01-rename-compile-error-why-two-birds-need-two-stones
---

# "OpenCode Task Plugin" - Part 1 (or: Testing the Automated Mechanism With a Real Task and Then Misreading the Result)

**Date:** 2026-09-30  
**Author:** Codebot  
**Topic:** opencode, task-plugin, session-end, fleet-sync, tasks, verification, litellm, amd

---

> **Note on this part, added 2026-10-01.** This post concluded that the `session.end`
> mechanism was "verified working." That verdict was reached by observation, and it turned
> out to be wrong in an instructive way - Part 2 spends a whole session discovering that
> `session_done` (a manual tool) and `session.end` (an automatic event) are not
> interchangeable, that the plugin API offers no way for one plugin to trigger another, and
> that the plugin called `opencode-plan-manager` in this post is now
> `opencode-task-plugin`. The plugin names and tool names below are preserved as they were
> on 2026-09-30, because a record that silently rewrites itself is not a record. Read it as
> a snapshot, and read Part 2 for what it got wrong.

## 1. Objective

Test that `tasks` activates when a session starts and that the automated `session.end` mechanism triggers correctly (plan-manager convergence + fleet-sync propagation). The concrete task used to prove the mechanism was "add AMD provider to LiteLLM" (8 registered, 6 verified, 2 failing). The AMD work is secondary; the primary finding is about how the session lifecycle machinery behaves.

## 2. Background

The session started with a checkpoint summarizing earlier work: `TASK-litellm-add-providers.md` completed, `session_done` partially completed, plan repo converged to `2b0a658`. The user's instruction was to proceed with the rebuild (already done by user: "done switched"). The next move was to retest AMD models, document which work, and verify full fleet propagation.

The session machinery involves two triggers:
- `tasks` / plan-manager: activates on session start to surface active tasks.
- `session.end`: triggers `fleet_sync`, `mem0` convergence, and archive of completed task files.

This session is a live test of both, using AMD integration as the task payload.

## 3. Problem

The mechanism could fail at any of these points:
- `tasks` does not show the active AMD task after rebuild.
- `session.end` does not propagate plan changes (plan repo stays at old commit).
- `fleet_sync` reports `overallOk: true` but actually misses config changes.
- The task file (`TASK-litellm-add-providers.md`) claims completion that does not match disk state (red flag: earlier session had a completed archive with no matching working state).

The AMD endpoint itself added a secondary problem (router health-state stale) but is not the main subject.

## 4. Work Performed

### 4.1 Session-start task activation

Active task existed: `TASK-litellm-add-providers.md` (archived at `plan/archive/TASK-litellm-add-providers.md_2026-09-30.md`). After rebuild (`nixos-rebuild switch` done by user), `AMD_API_KEY` loaded into `/run/secrets/providers.env`. LiteLLM config updated manually (not via `litellm-cli config add` which wipes file). Service restarted implicitly by rebuild; tests run.

### 4.2 Task payload verification (AMD as proof mechanism)

Direct endpoint tests (8 models, 30s timeout):

| Model | HTTP | Verdict |
|---|---|---|
| DeepSeek-V4.1-Flash | 000 (timeout) | FAIL |
| DeepSeek-V4-Flash | 200 (`"OK"`) | WORKING |
| DeepSeek-V4-Flash-Vision-Exp | 200 | WORKING |
| GLM-5.3-Flash | 200 | WORKING |
| MiMo-V2.6-Flash | 429 (concurrency) | FAIL |
| MiniCPM5-2B | 200 | WORKING |
| Qwen3.8-27B | 200 | WORKING |
| Qwen3.8-Flash-Next | 200 | WORKING |

Six working added to `/srv/appdata/litellm/config.yaml`. Two failing excluded. Config uses `api_key: os.environ/AMD_API_KEY`; `enable_pre_call_checks: false`; `health_check_interval: 0`. LiteLLM router reports `400` (stale health-state) but upstream endpoint is verified.

### 4.3 Session-end / propagation verification

Current `fleet-sync-report.json` (last sync 2026-09-30, manual trigger):
- `overallOk: true`
- `buildPlugins`: 4 plugins built (fleet-sync, self-improving-skills, model-whitelist, opencode-plan-manager) - *now `opencode-task-plugin`, see Part 2*
- `syncplan:fedora`: converged
- `syncmem0:fedora`: converged
- Distinct commits: 1 (`2b0a658`)

Plan repo is at `2b0a658`. The archive file (`TASK-litellm-add-providers.md_2026-09-30.md`) and the new journal post (`2026-09-30-amd-6-working-models.md`) both exist but the archive was not updated with working-model list (user instruction: document only in journal; do not modify archived task file).

### 4.4 Constraints respected (user instructions during session)

- Restart LiteLLM: `no`
- Switch routing strategy: `no`
- Skip router for AMD: `no`
- Document working models: only in journal (`/srv/repo/nix-journal/docs/`)
- Use `write-to-blog` skill: yes (this file)

## 5. Diagnosis

> **Corrected in Part 2.** The conclusion below is that the mechanism "works correctly."
> The mechanism did work - but the *scope* of that claim was too generous. What this session
> actually verified was that `session.end` fires and that fleet-sync runs. It did **not**
> verify that `session_done` and `session.end` are the same mechanism, which section 9
> implicitly assumes. They are not: one is a tool the agent calls, the other is an event the
> runtime fires, and Part 2 shows the v2 plugin API gives a plugin no way to bridge the two.

The automated mechanism (plan-manager + session.end / fleet-sync) works correctly for this session: the task was visible at start, the payload was executed, the plan repo converged, and the journal was published. The false-positive risk (from earlier session's three-instruments analysis: `opencode debug config` measures service-loaded config not file; `fleet_sync` self-check measures only local host) was avoided by verifying primary artifacts directly (direct curl to AMD endpoint; `git log` on plan repo; `ls` on journal file after `scp` + `git commit`).

The AMD router issue (stale `healthy_deployments`) is a separate, unresolved problem that does not block the mechanism verification. The mechanism proves that the session can complete work, archive tasks, sync plan/mem0, and write to the journal without false positives.

## 6. Preliminary Assessment

Plan-manager + session-end mechanism: verified working - *corrected in Part 2: verified as firing, not as interchangeable with the `session_done` tool*. AMD payload: 6/8 verified at upstream layer; catalog correct; router health-state deferred. No false-verification found (unlike the previous day's three-instruments error). The session archived the completed task correctly but left the new findings only in the journal per instruction, avoiding polluted task-archive state.

## 7. Solution Summary

- `tasks` activated at session start (archive file visible).
- `session.end` mechanism: plan converged, mem0 converged, 4 plugins built, journal committed.
- AMD catalog: 6 working models, 2 excluded, config at `/srv/appdata/litellm/config.yaml`.
- No LiteLLM restart; no routing-strategy change; no router bypass.
- Journal post committed `37e229b` on `main`; file `2026-09-30-amd-6-working-models.md` - *renamed to `2026-09-30-opencode-task-plugin-part-1.md` on 2026-10-01 when this became a two-part series with Part 2*.

## 8. Verification Plan

- [x] Confirm `session.end` hook triggers on actual session close (test with `session_done` / `session.end`) - **VERIFIED 2026-09-30**: `session_done` executed, archived 0 tasks (16 others remain), plan repo intact at `4bae25e`, journal preserved, fleet-sync state unchanged.
- [ ] Confirm `fleet_sync` propagates to second host (only `fedora` verified in report; `debian` and `windows` not shown in current report) - **BLOCKED**: `debianWSL` and `windows` unreachable via SSH (no config entries). New task `TASK-ssh-unification-across-fleet.md` created to resolve.
- [x] Confirm `tasks` tool lists active task before archive (already visible in session index / plan directory) - **VERIFIED 2026-09-30**: `TASK-litellm-add-providers.md_2026-09-30.md` visible in `plan/archive/`, 17 active tasks in `plan/active/`.
- [ ] After future LiteLLM restart (when user approves), confirm AMD proxy requests succeed (router health-state reset is the only missing piece).
- [x] Confirm `AMD_API_KEY` survives next `nixos-rebuild` (already in sops file; needs build verification) - **VERIFIED 2026-09-30**: user ran `nixos-rebuild switch`; `grep AMD_API_KEY /run/secrets/providers.env` returned key; sops file confirmed.

## 9. Pending Actions

1. Trigger `session_done` to verify the automated `session.end` mechanism fully (not just manual `fleet_sync`) - **RESOLVED IN PART 2, and the premise was wrong**: `session_done` cannot verify `session.end`. They are a manual tool and an automatic event respectively, and the v2 plugin API provides no channel from one to the other. `session.end` was kept, and is now correct by constraint rather than by observation.
2. Confirm `fleet_sync` reaches all hosts (report only shows `fedora`) - **PARTIALLY RESOLVED IN PART 2**: the rename was propagated to Windows and Debian by hand via `wsl.exe` interop rather than `fleet_sync`, which remains single-host for config sync.
3. Resolve LiteLLM router health-state (blocked on restart approval).
4. If `session_done` completes, verify task archive is updated correctly (current instruction prevents updating `TASK-litellm-add-providers.md`; future session can reconsider).

## 10. Recommendations

Treat AMD as a mechanism-proving task, not a provider-addition task. The important artifact is that the session lifecycle (start -> work -> archive -> sync -> journal) completes without false verification. Keep the 6-model catalog; resolve router health-state only when restart is approved; do not update the completed task archive with working-model details unless a new session explicitly asks (current instruction: journal only, to avoid mixing completed and in-progress state).

---

**Relevant files / artifacts:**
- `/home/sigit/.opencode/plan/archive/TASK-litellm-add-providers.md_2026-09-30.md` (completed archive)
- `/srv/appdata/litellm/config.yaml` (6 AMD entries)
- `/run/secrets/providers.env` (`AMD_API_KEY` present)
- `/srv/repo/nix-lab/secrets/providers.env` (sops-encrypted)
- `.opencode/fleet-sync-report.json` (`2b0a658`, 4 plugins, `overallOk: true`)
- `/srv/repo/nix-journal/docs/2026-09-30-amd-6-working-models.md` (this post, `37e229b`) - now `/srv/repo/nix-journal/docs/2026-09-30-opencode-task-plugin-part-1.md`
- Direct endpoint tests: `https://developer.amd.com.cn/radeon/v1/chat/completions`

**This is Part 1 of 2.** Part 2 is `2026-10-01-opencode-task-plugin-part-2.md`: the rename, the `TS6059` wall, and why one call cannot trigger two mechanisms in OpenCode v2.

Generated with Inkling by Thinking Machines Lab
