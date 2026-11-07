---
nav:
  series: "OpenCode Task Plugin"
  part: 6
  prev:
    title: "Merging Skills into Tools and GitHub Mirror"
    slug: 2026-10-19-opencode-task-plugin-merge-skills-tools-github-mirror
---
# Testing and Git Convention Setup for opencode-task-plugin

**Date:** 2026-10-24
**Author:** Codebot
**Topic:** testing, git-convention, workflow

---

## 1. Objective

Establish a reliable testing and git convention workflow for the `opencode-task-plugin` repository, ensuring that local development, homelab staging, and GitHub stable release paths are consistently validated. This report documents the git conventions, testing patterns, and verification steps used across the `dev → homelab → GitHub main` workflow.

## 2. Background

The `opencode-task-plugin` uses a three-path workflow:
- **Local WSL** (`~/.config/opencode/plugins/opencode-task-plugin/`) — active development
- **Homelab staging** (`/srv/repo/opencode-task-plugin` on NixOS) — dev mirror with `dev` branch
- **GitHub stable** (`https://github.com/thsigit/opencode-task-plugin`) — `main` branch as release

Each path has its own git branch state, and this report ensures they remain consistent through defined conventions and testing steps.

## 3. Git Conventions

### 3.1 Branch Naming

| Branch | Purpose | Typical Commit |
|---|---|---|
| `main` | Stable release, tracks GitHub | `cb6b12b` (merged from `github/main`) |
| `dev` | In-progress development, tested on homelab | `b9ed0c9` (merged from `github/main` + local commits) |

### 3.2 Remote Naming

| Remote | URL | Purpose |
|---|---|---|
| `github` | `git@github.com:thsigit/opencode-task-plugin.git` | Stable release mirror |
| `homelab` | `ssh://sigit@homelab/srv/repo/opencode-task-plugin.git` | Bare repo mirror (receive-only) |
| `origin` | (not configured) | Not used — `github` and `homelab` are explicit |

### 3.3 Workflow Commands

| Action | Command | Description |
|---|---|---|
| Push dev to homelab | `git push homelab dev` | Stage changes for testing on homelab |
| Push main to GitHub | `git push github main` | Publish stable release |
| Fetch latest from GitHub | `git fetch github main` | Update local main tracking |
| Verify branch state | `git log --oneline -3` | Check recent commits |
| List all branches | `git branch -a` | View local and remote branches |

### 3.4 Conventions Enforced

- **One source of truth for `main`**: Only `git push github main` updates the GitHub stable release.
- **`dev` is the integration branch**: All new features are developed on `dev`, tested on homelab, then merged to `main`.
- **No direct commits to `main`** from local WSL — always go through `dev` first.
- **Branch tracking**: Local `dev` tracks `homelab/dev`; local `main` tracks `github/main`.

## 4. Testing Patterns

### 4.1 Local Testing (WSL Host)

Before pushing to homelab, verify the local plugin works:

```bash
# Ensure we're on dev branch
git checkout dev

# Build the plugin (TypeScript compile)
npm run build

# Run task tools to verify they load
opencode task_new "test task"
opencode tasks
opencode task_verify
```

**Expected**: `npm run build` completes without errors; `task` and `tasks` list tools without failures.

### 4.2 Homelab Staging Test

After pushing to homelab, verify the dev branch is functional:

```bash
# On homelab
ssh homelab "cd /srv/repo/opencode-task-plugin"
# Confirm dev branch is checked out and at expected commit
git log --oneline -3
# Verify the plugin directory has expected files
ls -la dist/ index.ts task-manager.ts
```

**Expected**: `dev` branch at `b9ed0c9`, `dist/` and `.ts` files present.

### 4.3 Git State Verification

Three key checks to confirm workflow consistency:

| Check | Command | Pass Criteria |
|---|---|---|
| Local dev matches homelab dev | `git rev-parse dev` on both WSL and homelab | Same commit hash (`b9ed0c9`) |
| Local main matches GitHub main | `git rev-parse main` on WSL vs `git rev-parse github/main` | Same commit hash (`cb6b12b`) |
| Bare repo dev updated | `git rev-parse dev` on `/srv/repo/opencode-task-plugin.git` | Same as homelab full clone (`b9ed0c9`) |

### 4.4 Common Failure Points

| Issue | Symptom | Fix |
|---|---|---|
| `dev` branch stale | `git push homelab dev` rejects with non-fast-forward | `git pull homelab dev` then re-commit |
| `main` out of sync | `git push github main` fails | `git fetch github main` then `git merge dev` |
| Bare repo not updated | `/srv/repo/opencode-task-plugin.git` `dev` old | Push from full clone: `git push homelab dev` |
| Host key changes | SSH prompts for host key verification | Update `known_hosts` or use `StrictHostKeyChecking=no` |

## 5. Verification Checklist

Run these checks after any workflow step to confirm consistency:

### 5.1 Local WSL Checks

- [ ] `git branch` shows `* dev` or `* main`
- [ ] `git log --oneline -1 dev` shows expected commit
- [ ] `git log --oneline -1 main` shows `cb6b12b` or newer
- [ ] `npm run build` succeeds (if `.ts` files changed)
- [ ] `git status` shows clean working tree (no uncommitted changes)

### 5.2 Homelab Full Clone Checks

- [ ] `git branch` shows `* dev` (after checkout) or `* main`
- [ ] `git rev-parse dev` matches local WSL `dev` commit
- [ ] `git rev-parse main` matches `cb6b12b` (or latest from GitHub)
- [ ] `ls dist/` contains compiled files (`dist/index.js`, `dist/task-manager.js`, etc.)

### 5.3 Bare Repo Checks

- [ ] `git branch` shows `dev` and `main`
- [ ] `git rev-parse dev` matches homelab full clone `dev`
- [ ] `git rev-parse main` reflects latest `github/main` push

### 5.4 End-to-End Workflow Test

```bash
# 1. Local: make a small change, commit on dev
git checkout dev
# (make change)
git add .
git commit -m "chore: test workflow update"
git push homelab dev

# 2. Homelab: verify dev updated
ssh homelab "cd /srv/repo/opencode-task-plugin && git log --oneline -1 dev"

# 3. Local: merge to main and push to GitHub
git checkout main
git merge dev
git push github main

# 4. Verify GitHub mirror
ssh homelab "cd /srv/repo/opencode-task-plugin.git && git log --oneline -1 main"
```

**Expected**: Step 2 shows updated commit; Step 4 shows same commit on GitHub mirror.

## 6. Convention Rationale

- `dev → homelab → main → GitHub` provides a safety net: changes are first tested on the homelab staging mirror before going public.
- **Explicit remotes** (`github`, `homelab`) avoid ambiguity that `origin` would introduce.
- **Bare repo** (`opencode-task-plugin.git`) is the authoritative mirror for homelab; the full clone (`opencode-task-plugin`) is for active work.
- **No `origin`** — using named remotes makes the workflow explicit and prevents accidental pushes.

## 7. Pending / Future Actions

- [ ] Add `CHANGELOG.md` to the plugin repo following the same convention as the nix-journal series.
- [ ] Document the `configureSync(true)` opt-in pattern for remote sync in the plugin's README.
- [ ] Create a `verify-git-workflow` script that automates the checklist in §5.
- [ ] When the separate OpenCode install happens on debianWSL, verify the `task`/`verify` tools function from the fresh instance.

## 8. Recommendations

- **Always run `git fetch github main`** before starting work on `dev` to ensure you have the latest stable base.
- **Never push directly to `github main`** from a `dev` branch without merging first — use `git checkout main && git merge dev && git push github main`.
- **After any `git push homelab dev`, run the homelab verification checklist** (§5.2) before proceeding.
- **Keep the bare repo `dev` branch** in sync by pushing after each local `dev` commit: `git push homelab dev`.

Generated with Nemotron 3 Ultra by NVIDIA
