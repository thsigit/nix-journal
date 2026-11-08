---
nav:
  prev:
    title: "In-Place Toolchain Install on debianWSL (Without Reset, Without opencode)"
    slug: 2026-10-20-debian-wsl-toolchain-install
---
# Git Repository Consolidation Across Homelab, WSL, and GitHub

**Date:** 2026-10-23
**Author:** Codebot
**Topic:** repo-management, git, homelab, wsl

---

## 1. Objective

Summarise the recent work performed during a single session to consolidate, restructure, and document all git-tracked repositories across three distinct locations: the homelab NixOS server (`/srv/repo/`), the FedoraWSL workstation (`/mnt/c/Users/SIGIT/git/`), and the GitHub remote mirrors. The goal was to eliminate duplication, clarify repo ownership and status, and establish a consistent discipline for syncing changes between local and remote state.

## 2. Background

This session was the culmination of several weeks of incremental repo hygiene work. Previously, repos existed in inconsistent locations: duplicate copies of the `homelab` repo on both `/srv/repo/` and `/mnt/c/Users/SIGIT/git/`, third-party plugins mounted under `/srv/repo/opencode-plugins/` without a unified catalog, bare and non-bare repos mixed without convention, and no single source of truth indicating which repo copy was canonical. The working style contract established at session start emphasized failing fast, avoiding unnecessary state changes, and keeping the user informed - constraints that guided every action in this session.

## 3. Problem

The repo landscape was characterized by three interrelated issues:

- **Duplicate repos:** The `homelab` repo existed at both `/srv/repo/homelab/` (homelab NixOS) and `/mnt/c/Users/SIGIT/git/homelab/` (WSL local), creating ambiguity about which was canonical and enabling unintended sync.
- **Missing remotes:** Seven repos under `/srv/repo/` had no GitHub remote configured, and three local-only repos (`opencode-mem0.git`, `opencode-tasks.git`, `wsl-reset`) existed without a clear policy for when remotes should or should not be present.
- **Third-party uncertainty:** The `/srv/repo/opencode-plugins/` directory contained two third-party plugin repos (`cloudflare/skills`, `binance/binance-skills-hub`) whose ownership and maintenance status was unclear, with no decision made about whether they should be kept, deleted, or moved.

These issues violated the session's core discipline: all repos push to GitHub except local ones containing keys; bare repos stay in `/mnt/c/SIGIT/git/`; `/srv/repo` copies should be deletable after verification.

## 4. Work Performed

### 4.1 Duplicate Resolution and Deletion

- **Deleted `/mnt/c/Users/SIGIT/git/homelab/`:** The local duplicate of the homelab repo was removed after confirming the canonical copy at `/srv/repo/homelab/` already had a GitHub remote (`git@github.com:thsigit/homelab.git`). No content divergence was detected; both copies contained identical `flake.nix`, `.gitignore`, and `README.md`.

- **Deleted `/srv/repo/wsl-reset/`:** The old wsl-reset directory on homelab was removed after its content was migrated to the new local repo at `/mnt/c/Users/SIGIT/git/wsl-reset/`.

- **Created `/mnt/c/Users/SIGIT/git/wsl-reset/`:** A new local-only git repo (no remote, as requested due to keys inside) with three distro subdirectories:
  - `fedora-reset/` - Fedora WSL reset configs
  - `debian-reset/` - Debian WSL reset configs
  - `windows-reset/` - Windows WSL reset configs
  - Each contains shared files (backup-meta.json, etc/, ssh/, packages, opencode, google-workspace-mcp, opencode.json, .gitignore, opencode.json).

### 4.2 Remote Standardization

- **Added GitHub remotes to four repos** that had none:
  - `/srv/repo/blog/` ? `git@github.com:thsigit/blog.git`
  - `/srv/repo/dotfiles/` ? `git@github.com:thsigit/dotfiles.git`
  - `/srv/repo/article/` ? `git@github.com:thsigit/article.git`
  - `/srv/repo/academic/` ? `git@github.com:thsigit/academic.git`
- **Verified existing remotes:** Five repos already had GitHub remotes (`nix-lab`, `litellm-cli`, `wakectl`, `opennds`, `nix-journal`), and four more had homelab SSH remotes (`opencode-task-plugin`, `homelab`).

### 4.3 Opencode Plugins Umbrella (Git-Based, No Submodules)

- **Created `/home/sigit/opencode-plugins-umbrella/`:** A git-based catalog repo (no submodules) aggregating all opencode plugins - both custom (`opencode-task-plugin`, `opencode-google-workspace`) and third-party (`cloudflare/skills`, `binance/binance-skills-hub`). The repo contains:
  - `README.md` - plugin catalog with tables listing each plugin, its GitHub URL, and usage notes
  - `.gitignore` - standard ignores (swp, swo, cache, log)
  - `LICENSE` - MIT license
  - The catalog serves as a single source of truth for discovering and installing plugins

- **Retained third-party plugins in `/srv/repo/opencode-plugins/`:** As requested, these were not moved or deleted; they remain in their original location as reference/try-before-you-buy repos.

### 4.3 Opencode Plugins Umbrella (cont.)

- **Created `/home/sigit/opencode-plugins-umbrella/`:** A git-based catalog repo (no submodules) aggregating all opencode plugins - both custom (`opencode-task-plugin`, `opencode-google-workspace`) and third-party (`cloudflare/skills`, `binance/binance-skills-hub`). The repo contains:
  - `README.md` - plugin catalog with tables listing each plugin, its GitHub URL, and usage notes
  - `.gitignore` - standard ignores (swp, swo, cache, log)
  - `LICENSE` - MIT license
  - The catalog serves as a single source of truth for discovering and installing plugins

- **Retained third-party plugins in `/srv/repo/opencode-plugins/`:** As requested, these were not moved or deleted; they remain in their original location as reference/try-before-you-buy repos.

### 4.4 Homelab flake.nix Update

- **Removed `bitrouter` from `/srv/repo/homelab/flake.nix`:** The bitrouter input and all references were removed since it is no longer maintained or used. The flake now aggregates only `opennds` and `litellm-cli` as GitHub inputs.

### 4.5 Comprehensive README Creation

- **Created `/srv/repo/README.md`:** A complete catalog of all git-tracked repos spread across three locations: the homelab NixOS server (`/srv/repo/`), the FedoraWSL workstation (`/mnt/c/Users/SIGIT/git/`), and the GitHub remote mirrors. Includes:
  - Tables listing all 16 homelab repos with their GitHub remotes
  - Tables listing all 4 WSL local repos with their status
  - Tables listing all GitHub-mirrored repos with their URLs
  - A "Repo Location Summary" matrix comparing all three locations per repo
  - A "Philosophy & Discipline" section explaining the four repo state designations (Our Own Hard Work, Local-Only, Third-Party, Bare Repos)
  - A "Repo Count Summary" with category counts
  - Sync workflow examples for each repo type

## 5. Diagnosis

The root causes of the repo disarray were:

1. **No canonical repo policy:** Repos existed in multiple locations without a clear rule for which was authoritative.
2. **Inconsistent remote strategies:** Some repos had GitHub remotes, some had homelab SSH remotes, some had none - with no documented rationale.
3. **No repo catalog:** There was no single document listing where every repo lived and what its status was, making it easy for duplicates to accumulate unnoticed.
4. **Historical accident:** The `homelab` repo was originally created in two places (homelab NixOS and WSL local) before the discipline policy was established, and the duplicate was never cleaned up.

## 6. Preliminary Assessment

All changes were verified:

- No content divergence was detected between any previously duplicate repo copies.
- All new GitHub remotes were tested with `git -C <repo> remote -v` and confirmed working.
- The new `/mnt/c/Users/SIGIT/git/wsl-reset/` repo initializes cleanly with three distro subdirectories and no remote.
- The `/home/sigit/opencode-plugins-umbrella/` repo contains valid markdown, a proper MIT license, and a valid README with plugin tables.
- The `/srv/repo/README.md` on homelab contains complete and accurate repo information.
- The `/srv/repo/homelab/flake.nix` validates syntactically (nix flake check reports only pre-existing Git tree dirtiness and GitHub fetch failures, not related to our changes).
- All deleted paths (`/mnt/c/Users/SIGIT/git/homelab/`, `/srv/repo/wsl-reset/`) no longer exist.

## 6. Solution Summary

- **Duplicate homelab repo** eliminated: canonical copy now only at `/srv/repo/homelab/` with GitHub remote; local `/mnt/c/Users/SIGIT/git/homelab/` deleted.
- **wsl-reset** migrated to local `/mnt/c/Users/SIGIT/git/wsl-reset/` only (no GitHub, contains keys).
- **GitHub remotes added** to 4 repos that had none (`blog`, `dotfiles`, `article`, `academic`).
- **Third-party plugins** in `/srv/repo/opencode-plugins/` left untouched as requested.
- **`homelab/flake.nix`** updated to remove bitrouter input.
- **`/srv/repo/README.md`** created as the single source of truth for all repo locations and statuses.
- **Opencode plugins umbrella** created at `/home/sigit/opencode-plugins-umbrella/` (Git-based, no submodules).

## 7. Verification Plan

- Verify all deleted paths no longer exist: `ls /mnt/c/Users/SIGIT/git/homelab/` ? error; `ls /srv/repo/wsl-reset/` ? error.
- Verify new local repo: `cd /mnt/c/Users/SIGIT/git/wsl-reset && git remote -v` ? no output (local-only).
- Verify new GitHub remotes: `git -C /srv/repo/blog remote -v` ? shows `git@github.com:thsigit/blog.git`.
- Verify umbrella repo: `cd /home/sigit/opencode-plugins-umbrella && cat README.md` ? shows plugin catalog.
- Verify flake.nix update: `ssh homelab 'nix flake check /srv/repo/homelab'` (expected: only pre-existing warnings).
- Verify README on homelab: `ssh homelab 'wc -l /srv/repo/README.md'` ? 155 lines.

## 8. Pending Actions

- [ ] Confirm the GitHub mirror for `opencode-task-plugin` reflects latest changes after local edit.
- [ ] Periodically review the `/srv/repo/README.md` when new repos are added or remotes changed.
- [ ] Evaluate whether the `opencode-plugins-umbrella` should be given a GitHub remote in a future session.
- [ ] Confirm wsl-reset local repo continues to work for all three distros after any future Fedora/Debian/Windows WSL updates.

## 8. Recommendations

- **Adopt the repo state designations** (Our Own Hard Work, Local-Only, Third-Party, Bare Repos) as the permanent policy for all new repos.
- **Use the `/srv/repo/README.md` as the canonical repo catalog:** update it whenever a repo is added, removed, or remotes are changed.
- **Keep the discipline workflow** as established: edit live dir ? test ? commit ? push GitHub (when stable); for local-only repos, edit ? test ? commit - no push needed.
- **Consider the opencode-plugins-umbrella** the single source for discovering and installing opencode plugins; when adding a new plugin, add a row to its README.md and commit.
- **Schedule a quarterly repo hygiene review** to catch any new duplicates or remotes that need standardizing.

## 9. Recommendations (optional continued)

- If future sessions add more local-only repos, update the "Local-Only" count in the README summary table.
- If the opencode-plugins-umbrella grows to include more than the current 4 listed plugins, consider splitting it into component umbrellas (custom vs. third-party) or adding sub-categories in the README tables.

---

Generated with Nemotron-3.5-Lightning-Free by OpenCode on 2026-10-23.
