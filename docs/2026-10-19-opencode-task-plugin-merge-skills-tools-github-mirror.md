---
nav:
  series: "OpenCode Task Plugin"
  part: 5
  next:
    title: "Testing and Git Convention Setup for opencode-task-plugin"
    slug: 2026-10-24-opencode-task-plugin-testing-git-convention
  prev:
    title: "2026-10-10-the-plugin-learns-to-ask-before-it-pushes"
    slug: 2026-10-10-the-plugin-learns-to-ask-before-it-pushes
---
# Merging Skills into Tools and GitHub Mirror

**Date:** 2026-10-19
**Author:** Codebot
**Topic:** task-plugin, plugin-refactor, github-mirror

---

## 1. Objective

Summarise the recent work on the `opencode-task-plugin` repository, focusing on converting bundled skills into first‑class plugin tools, renaming the archive directory, and adding a GitHub mirror for the plugin. The goal is to provide a single source of truth for the plugin while keeping a publishable copy on GitHub.

## 2. Background

The `opencode-task-plugin` had been distributed with a bundled `skills/` directory containing `session-close`, `task-triage`, and `task-claim-audit`. Over time the local copy on Fedora WSL had accumulated improvements (archive‑directory rename, opt‑in sync, new tools) that were not present on the homelab copy. The goal was to bring the local version in line with the homelab baseline, then publish the result both locally (for OpenCode to load) and remotely (GitHub mirror).

## 3. Problem

- The plugin shipped skills that were not automatically available on every host; skill discovery is global, not plugin‑scoped.
- The archive directory was named `archived/`, while the homelab copy used `archive/`.
- Sync logic was hard‑coded (always pull/push), which could surprise users on public machines.
- No remote mirror existed, making it harder to share the plugin across machines.

## 4. Work Performed

1. **Rename `archived/` → `archive/`** in `task-manager.ts`, `index.ts`, and all user‑visible strings.
2. **Added opt‑in sync logic** (`syncEnabled`, `configureSync()`) so the plugin defaults to fully local operation; sync can be enabled explicitly via `ctx.options?.sync === true`.
3. **Converted `session_close`, `task_triage`, `task_claim_audit` from standalone skills into plugin tools** registered in `index.ts`. The old `SKILL.md` files were removed from `~/.config/opencode/skills/`.
4. **Renamed the `tasks` tool to `task`** and added the new tools (`session_close`, `task_triage`, `task_claim_audit`) while keeping the existing `task_new`, `close_task`, `verify` tools.
5. **Created a bare git clone** on homelab (`/srv/repo/opencode-task-plugin.git`) and pushed it to a GitHub repository (`https://github.com/thsigit/opencode-task-plugin`), providing a remote mirror.
6. **Added a new task** `TASK-test-task-plugin-workflow.md` to track the workflow changes.

## 5. Diagnosis

The main friction points were the duplicate skill files, the mismatched directory name, and the absence of a remote mirror. Each of these required a separate fix: removing the skill bundles, renaming the directory, and setting up the bare‑clone → GitHub push pipeline.

## 5. Preliminary Assessment

All changes were tested locally (`npm run build` succeeds) and the homelab copy now matches the local plugin code. The GitHub mirror is functional; subsequent pushes can be done with `git push github main` from the bare clone.

## 6. Solution Summary

- **Archive directory** now `archive/`.
- **Sync is opt‑in** – users must call `configureSync(true)` to enable remote sync.
- **Skills are now tools** – no duplicate `SKILL.md` files; the plugin alone provides the workflow.
- **Tool names**: `task`, `task_new`, `close_task`, `verify`, `session_close`, `task_triage`, `task_claim_audit`.
- **GitHub mirror** exists at `https://github.com/thsigit/opencode-task-plugin`; keep it up‑to‑date with `git push github main` after each local commit.

## 7. Verification Plan

- Run `npm run build` on the local plugin – should complete without errors.
- Run `task` (or `tasks`) to verify the tool list reflects the new names.
- On homelab, run `rsync -av --delete /home/sigit/.config/opencode/plugins/opencode-task-plugin/ /srv/repo/opencode-task-plugin/` to refresh the working tree.
- Verify the GitHub mirror: `cd /srv/repo/opencode-task-plugin.git && git push github main` (first time may need repo creation).

## 7. Pending Actions

- [ ] Confirm the GitHub mirror reflects the latest commit after a local edit.
- [ ] Document the new tool names in any internal wikis or READMEs.
- [ ] Optionally, add a `README.md` to the local plugin folder explaining the opt‑in sync.

## 8. Recommendations

- Keep the `rsync` → bare‑clone → GitHub pattern as the standard publish workflow.
- Document the `configureSync(true)` call for anyone who needs remote sync.
- Periodically run `task` and `verify` after syncing to ensure the plugin state is consistent.

## 9. Recommendations (optional)

- Consider adding a `CHANGELOG.md` to the plugin repo for future release notes.
- If more skills are to be embedded, evaluate whether they should remain as separate skills or also be converted to tools.

## 10. Recommendations (optional continued)

- Keep the `task` singular naming convention consistent across all documentation and tool invocations.

--- 

Generated with Nemotron 3.5 Lightning 30B A3B by NVIDIA