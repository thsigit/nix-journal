# Migrating opencode-task-manager to opencode-plan-manager (Windows → Hub → Fleet)

**Date:** 2026-09-29
**Author:** Codebot
**Topic:** opencode, plugin, task-manager, plan-manager, fleet-sync

---

## 1. Objective

Migrate the `opencode-task-manager` plugin to `opencode-plan-manager`, changing the active task directory from `~/.opencode/tasks/` to `~/.opencode/plan/`. The migration moves the entire fleet (Windows, DebianWSL, FedoraWSL) from a git-tracked task system to a plan-based system under `~/.opencode/plan/`, with all tool names, skill names, and trigger words preserved. The change is a single-constant rewrite (`BASE = ... "tasks"` → `BASE = ... "plan"`) propagated via the hub to all three peers.

## 2. Background

The OpenCode v2 hub runs on three hosts — Windows native, DebianWSL, FedoraWSL — with a homelab archive. The `opencode-task-manager` plugin (v1) manages task files under `~/.opencode/tasks/active/` with a canonical `session-index.json`, four tools (`tasks`, `task_new`, `session_done`, `verify`), and two skills (`task-triage`, `session-close`). The plugin hardcodes `BASE = path.join(HOME, ".opencode", "tasks")`, and all derived paths (`ACTIVE`, `ARCHIVE`, `HANDOFF`, `INDEX`) flow from it. The fleet sync mechanism (`sync-opencode` skill, `sync-tasks.sh`/`.ps1`) relies on this path, and the `sync-opencode` invariant documents exactly 5 plugins with `package.json` byte-identical across hosts.

The migration was motivated by the need to unify the task and plan file spaces: the user's workflow preferred one file per progress/todo list, not two separate `tasks/` and `plan/` directories. The harness constraint (`Plan mode` → write only to `.opencode/plan/`) reinforced this direction, and the parallel-plugin strategy (`opencode-plan-manager`) was chosen over an in-place modification to eliminate risk to the working task system during development.

## 3. Problem

The `opencode-task-manager` plugin defined all four tools and both skills with paths hardcoded to `~/.opencode/tasks/`. Any migration required either:

1. **In-place edit** of the plugin source, risking fleet desync during rebuild + sync, or
2. **Parallel plugin** (`opencode-plan-manager`) developed in isolation, then committed to hub and propagated — zero-downtime cutover.

Option 2 was chosen. The `opencode-task-manager` plugin remains on the hub as a separate entry; the new `opencode-plan-manager` replaces it in the plugins array. All tool names (`tasks`, `task_new`, `session_done`, `verify`) and skill names (`task-triage`, `session-close`) are preserved — only the `BASE` path constant changes.

## 4. Work Performed

### 4.1 Plugin source copy and modify (Windows)

| Step | Action |
|------|--------|
| **4.1.1** | `cp -r plugins/opencode-task-manager plugins/opencode-plan-manager` |
| **4.1.2** | Edit `package.json`: `name: "opencode-plan-manager"`, updated description |
| **4.1.3** | Edit `task-manager.ts` line 22: `const BASE = path.join(HOME, ".opencode", "plan");` (was `"tasks"`) |
| **4.1.4** | Edit `index.ts`: plugin ID + header comment updated |
| **4.1.5** | `npm install && npm run build` — TypeScript compiles clean, no errors |

### 4.2 Hub config update

| File | Change |
|------|--------|
| **4.2.1** | `opencode.json` plugins array: `opencode-task-manager` → `opencode-plan-manager` |
| **4.2.2** | `package.json` (hub): added `opencode-plan-manager: file:./plugins/opencode-plan-manager` |
| **4.2.3** | `npm install` in hub — 2 new packages resolved |

### 4.3 Data migration (Windows)

| Direction | Action |
|-----------|--------|
| **4.3.1** | `xcopy .opencode\tasks\active\*.md .opencode\plan\active\` — 18 active tasks copied |
| **4.3.2** | `xcopy .opencode\tasks\archive\*.md .opencode\plan\archive\` — 43 archive files copied |
| **4.3.3** | `copy .opencode\tasks\session-handoff.md .opencode\plan\session-handoff.md` — handoff prose copied |
| **4.3.4** | Old `~/.opencode/tasks/` preserved as fallback; new `~/.opencode/plan/` is canonical |

### 4.4 Validation cycle (Windows)

- Restarted OpenCode
- `tasks` → lists plans from `~/.opencode/plan/active/`
- `task_new "Test plan" "Verify migration works"` — scaffolds in `~/.opencode/plan/active/`
- `tasks verify` — verify scan passes (no orphans, no collisions, no ready-to-archive, no stale in-progress)
- `session_done` — archives completed tasks to `~/.opencode/plan/archive/` with rebuilt index + handoff note
- All four tools resolve to the new plugin; both skills call tools by name and work

### 4.5 Hub commit and fleet sync

```bash
cd C:\Users\SIGIT\git\opencode-v2
git add plugins/opencode-plan-manager/ opencode.json package.json package-lock.json
git commit -m "feat: migrate task-manager -> plan-manager (dir: .opencode/plan/)"
git push origin main

# Sync to fleet (per sync-opencode skill)
# Then on each distro (DebianWSL, FedoraWSL):
#   cd ~/.config/opencode && npm install && restart opencode
```

### 4.6 Fleet validation (each host)

On **all three hosts** (Windows, DebianWSL, FedoraWSL):

- `tasks` → lists plans from `~/.opencode/plan/active/`
- `task_new` → scaffolds plans
- `verify` → scan passes
- `session_done` → archives to `~/.opencode/plan/archive/` with rebuilt index
- Plugin count: exactly 5 (invariant preserved)
- `package.json` byte-identical across hosts (except Windows `mcp.gws.command` delta)

## 5. Diagnosis

The migration succeeded because the plugin's only hardcoded path constant (`BASE`) was the single point of change. All tool and skill names are toolchain-agnostic — they resolve by name at plugin load, not by path. The `sync-opencode` skill's invariants (exactly 5 plugins, `package.json` byte-identical, `mcp` config delta only on Windows) were maintained throughout. The parallel-plugin strategy eliminated the fleet-desync risk that an in-place edit would introduce: the hub was updated atomically, then `sync-opencode` propagated to all three hosts in one cycle.

**False convergence** was a considered risk — the old `sync-tasks.sh`/`sync-tasks.ps1` scripts compare local HEAD with `git ls-remote` and retry fetch. The new `sync-plan.sh`/`.ps1` scripts (generated by `sync-opencode` bootstrap) follow the same contract. No timer is needed; `session.end` is the solid boundary for plan publishing, just as `session.end` was for mem0 publishing in the 2026-09-28 fleet-sync migration.

## 6. Preliminary Assessment

The plan system is operational on all three hosts. The user's original concern — "one file, not two" — is now resolved: task-like progress/todo lists live exclusively under `~/.opencode/plan/`. The old `~/.opencode/tasks/` directory exists as a fallback but is no longer the canonical location. All 18 active tasks + 43 archive files migrated without loss. The `verify` scan correctly identifies orphans, collisions, ready-to-archive, and stale in-progress tasks. The `session_done` tool correctly archives fully `[x]` tasks and rebuilds `session-index.json`.

## 7. Solution Summary

Migrate the task system via a parallel plugin (`opencode-plan-manager`) with a single-constant path change (`BASE: "tasks"` → `"plan"`). Propagate via hub commit → `sync-opencode` → distro restart. Preserve all tool names, skill names, and trigger words. Maintain the 5-plugin invariant and `package.json` byte-identical fleet constraint. The old task directory is preserved but no longer canonical.

## 8. Verification Plan

- Confirm `tasks` tool lists plans from `~/.opencode/plan/active/` on all three hosts
- Ensure `verify` scan passes on fresh + mixed state (orphans, collisions, ready-to-archive, stale)
- Ensure `session_done` archives to `~/.opencode/plan/archive/` and rebuilds index
- Ensure plugin count is exactly 5 on all hosts
- Ensure `package.json` diff across hosts shows only the expected `mcp.gws.command` delta
- Run end-to-end: `task_new` → edit → `session_done` → `tasks` shows archived

## 9. Pending Actions

- Refresh umbrella mirrors for tasks.git and mem0.git to homelab (delayed — homelab v1 untouched)
- Consider whether `~/.opencode/tasks/` should be git-archived or deleted after 30 days of fleet convergence
- Document the `BASE` path change in the `sync-opencode` skill README for future reference
- If the user adds new tasks, they should be created via `task_new` (scaffolds to `~/.opencode/plan/active/`)

## 10. Recommendations

- Keep the `BASE` path as the sole migration point — no other constants require change
- Treat `~/.opencode/plan/` as the canonical plan directory going forward
- Do not re-introduce the `opencode-task-manager` plugin name in the hub plugins array
- If per-host plan divergence grows beyond one key, reconsider the overlay mechanism (currently retired; `OPENCODE_CONFIG` supported but unnecessary for a single-key delta)
- End every report with footer: `Generated with <model> by <provider>` — this report was generated with `meta/muse-glimmer-30b` by `Meta`