# Three Sync Domains Fixed by Hand — and the Unified Fleet-Sync Plan They Revealed

**Date:** 2026-09-29
**Author:** Codebot
**Topic:** opencode, plugins, skills, tasks, fleet-sync, sync-opencode, parity

---

## 1. Objective

Document a session in which three fleet-sync domains — OpenCode **plugins**, **skills**, and **tasks/plan** — were repaired manually across the three-host fleet (Windows hub + FedoraWSL + DebianWSL), and from that work derive a single unified `fleet-sync` skill that should have automated all of it. The session closed by writing a formal plan (`TASK-unified-fleet-sync-skill.md`) to replace the now-fragmented `sync-opencode` (skill) and `fleet-sync` (plugin) with one mechanism.

## 2. Background

The fleet runs OpenCode v2 with a Windows-native hub at `C:\Users\SIGIT\.config\opencode` acting as the canonical source of truth. Two WSL distros (FedoraWSL, DebianWSL) receive config via rsync/copy — never symlinks. Three independent data stores each have their own convergence mechanism:

- **Config** (`opencode.json`, `plugins/`, `skills/`, `package.json`): covered by the `sync-opencode` *skill* (docs only — it describes rsync rules but is not a running process).
- **Tasks/Plan** (`~/.opencode/plan/`): a separate git repo with three working trees + one bare peer (`C:\Users\SIGIT\git\opencode-tasks.git`). Historically synced by `sync-tasks.sh`, now by the `fleet-sync` *plugin*'s git logic.
- **Mem0** (`~/.config/opencode/...`): a second git peer (`opencode-mem0.git`).

Two plugins load at startup and had been failing:
- **`fleet-sync`** — a real TS plugin that publishes mem0 on `session.end`.
- **`sync-opencode`** — a *skill* (not a plugin), so it never "ran"; it only documented intent.

The session opened with the user's report: *"2 plugins failed. fix it."*

## 3. Problem

The fleet had silently drifted in three ways, none of which any existing automation had caught or corrected:

1. **Plugins never built.** Four of five plugins are TypeScript with `main: dist/index.js`, but no `dist/` existed. The `tsconfig.json` files declared `"lib": ["ES2022"]` only, so `console` and `AbortController` failed typechecking. Worse, each plugin's `package.json` duplicated `@opencode/plugin` as a local dependency, and one plugin (`opencode-plan-manager`) carried a 98-package `node_modules` — violating the root-only install convention.
2. **Skills diverged.** The Windows hub had an extra `task-claim-audit/` skill and a *newer* `session-close` SKILL.md that Fedora/Debian lacked. A separate left-over (my own earlier mistaken Windows-side `npm install`) had scattered stray `node_modules` into three plugin dirs.
3. **Tasks/plan never converged.** Each host had committed to its local plan git repo but never pushed/pulled the bare peer. Windows held six task files from that day's work the distros never received; the distros held three follow-up tasks Windows never received; Debian still showed `distro-identity-overlay` as active after it had been archived.

The root cause in every case: the sync machinery was **fragmented and partly non-executing**. `sync-opencode` was a doc, not a process; `fleet-sync` only did mem0; plugin-building and skills-parity were not covered at all.

## 4. Work Performed

### 4.1 Plugin repair (root-level build)

| Step | Action |
|------|--------|
| **4.1.1** | Corrected course: worked on the **Fedora** side (`~/.config/opencode`), not the Windows hub, per the user's identity-overlay convention. |
| **4.1.2** | Edited root `package.json` to add `typescript` as a dependency (root install only). |
| **4.1.3** | Set `"lib": ["ES2022", "DOM"]` in all four TS plugins' `tsconfig.json` (console/AbortController need DOM). |
| **4.1.4** | Stripped `@opencode/plugin` from each plugin's `package.json` `dependencies` → `{}`; resolved from root. |
| **4.1.5** | Removed the duplicated 98-package `node_modules` from `opencode-plan-manager`. |
| **4.1.6** | `npm install` **once at root** → `typescript` + `@opencode/plugin` present, 98 stray packages pruned. |
| **4.1.7** | Built all four TS plugins with root `tsc` → `dist/index.js` present on every plugin; zero stray `node_modules`. |

### 4.2 Skills parity (rsync hub → distros)

| Step | Action |
|------|--------|
| **4.2.1** | Inventoried all three skill dirs. Found Fedora == Debian for every active skill; hub differed in exactly one (`session-close`, hub was newer). |
| **4.2.2** | Pushed hub's newer `session-close` → Fedora + Debian (rsync, no symlinks). |
| **4.2.3** | Promoted hub-only `task-claim-audit` → Fedora + Debian (it was orphaned on the hub). |
| **4.2.4** | Cleaned stray `node_modules` left by the earlier mistaken Windows-side install. |
| **4.2.5** | Verified: 24 active skills byte-identical across all three hosts; `archive/` (15) identical; `sync-excludes.txt`/`README.md` identical. |

### 4.3 Tasks/plan git convergence (3 peers → bare)

| Step | Action |
|------|--------|
| **4.3.1** | Identified all three plan dirs as git repos sharing bare peer `opencode-tasks.git`. |
| **4.3.2** | Archived the four already-resolved Windows task files (`opencode-plugin-load-404`, `overlay-gws-dead-path`, `cloudflare-whitelist-stale`, `inspect-sync-opencode`) — they described work already done this session. |
| **4.3.3** | Committed Fedora's `distro-identity-overlay` archive; pushed to peer. |
| **4.3.4** | Pulled on Fedora — non-fast-forward → merged (not rebased). Resolved two minor conflicts: `.gitignore` took the Windows superset; the archive file kept the cleaner tail. |
| **4.3.5** | Fixed a merge artifact: git had wrongly archived the three distro-only follow-up tasks (`nixos-opencode-v2-flake-upgrade`, `opencode-v2-overlay-and-guard-followups`, `v2-fleet-parity-and-whitelist-followups`); restored them to `active/`. |
| **4.3.6** | Pushed merged HEAD to peer; pulled on Windows (after fixing its remote path to `/mnt/c/...` and removing leftover untracked copies) and Debian (after discarding its stale local `.gitignore`). |
| **4.3.7** | Final archive pass on the four resolved tasks; re-pushed; pulled on Windows + Debian. |

### 4.4 Final convergence state

All three hosts at the same git commit (`ceae4db`) with **19 identical active tasks**. Two open carry-overs from the session's work are now visible fleet-wide: `distro-gws-credentials-missing` (gws broken on both distros — needs OAuth fix) and `opencode-provider-whitelist-decision` (`provider.opencode` still undecided).

### 4.5 The unified plan

Closed by writing `TASK-unified-fleet-sync-skill.md` to `~/.opencode/plan/active/`, committed and pushed to the plan peer. It specifies one TS `fleet-sync` plugin absorbing:
- `syncConfig()` ← `sync-opencode` rules (hub→distro rsync, exclude `node_modules`/`dist`/`.git`, 5-plugin + package.json invariants)
- `syncTasks()` + `syncMem0()` ← existing `fleet-sync` git logic
- **new** `buildPlugins()` (root `npm install` → `tsc` from root)
- **new** `syncSkills()` (source rsync + archive git merge)

Triggers: `session.end` + `task.archived` + manual `opencode plugin fleet-sync [--dry-run]`. User decisions baked in: authored on the working distro then dogfood-propagated; TypeScript; `wsl.exe` calls blocking with 60s timeout (flag+skip+continue, last-wins); conflicts flagged with options rather than auto-resolved; no rollback; dry-run mode exposed.

## 5. Key Findings

- **The sync gap was a git-sync gap, not a file-copy gap.** The plan data store had full git infrastructure (3 peers + bare) but nobody pushed/pulled. The fix was `git merge` + `git push` + `git pull`, not rsync.
- **`sync-opencode` was documentation, not automation.** Its rules (hub-is-truth, exclude `node_modules`, 5-plugin invariant) were sound but unenforced. The plugin-build and skills-parity gaps it implied were simply never implemented.
- **The `tsconfig` `lib` omission was a one-line class of bug.** Every TS plugin failed the same way; the fix (`"lib": ["ES2022", "DOM"]`) is now part of the plugin contract.
- **Root-only install is load-bearing.** Plugins must not carry `@opencode/plugin` or `typescript` as local deps; they resolve from the hub root. Duplicated `node_modules` breaks parity assertions.
- **Archive promotions are task operations.** Moving a skill to `skills/archive/` is a git event, not an rsync event — it must flow through the plan peer, not the config rsync.

## 6. Lessons for the Unified Skill

1. **One invocation, four stores.** Config, skills, tasks, mem0 (and now plugins) are one consistency operation. Fragmenting them produced exactly the drift we repaired by hand.
2. **Build is part of sync.** A plugin with no `dist/` is a failed plugin. `buildPlugins()` must run before any parity check asserts `dist/` exists.
3. **Last-wins, no undo.** Fleet convergence should never roll back. If a step partially applies, flag it; the next sync reconciles. This matches the user's explicit "no undo" decision.
4. **Conflict surfacing over conflict resolution.** When the same task is edited on two hosts, flag + offer options (hub / local / both / defer) rather than silently picking one.
5. **Dogfood the sync.** The unified skill, once built on the working distro, should propagate itself to hub + peers via the very mechanism it implements.

## 7. Open Items Carried Forward

- **`distro-gws-credentials-missing`** — gws is non-functional on both WSL distros (OAuth `credentials.json` missing; `tokens.json` rewriting without refresh). Needs a real `tools/call` verification, not `tools/list`.
- **`opencode-provider-whitelist-decision`** — `provider.opencode` remains unfiltered; new free models (`longcat-2.5-preview-free`, `space-bunny-free`) appeared silently.
- **Implement `TASK-unified-fleet-sync-skill`** — the plan is written; execution is the next session's work.
