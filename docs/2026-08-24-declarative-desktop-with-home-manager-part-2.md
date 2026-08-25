# Declarative Desktop with Home-Manager - Part 2

*Out-of-store symlinks: every GUI click is now an uncommitted change*

**Date:** 2026-08-24  
**Author:** Codebot  
**Topic:** NixOS, homelab, home-manager, dotfiles, Xfce, config

---

## 1. Objective

Make the `/srv/repo/dotfiles` repository the single source of truth for interactive user configuration on the workstation, using home-manager out-of-store symlinks so that GUI and application changes land directly in the repo working tree - versioned with git, and never reverted by a rebuild.

## 2. Background

Part 1 of this series (`2026-08-12-declarative-desktop-with-home-manager-part-1.md`) described bringing the workstation profile under home-manager management. That first iteration used two mechanisms that later proved limiting:

- **Force-copied store snapshots** - `xfce4-panel.xml`, four launcher `.desktop` files, autostart and mimeapps entries were copied into the nix-lab profile and deployed from the Nix store.
- **Declarative xfconf settings** - the wallpaper block in `xfconf.settings` re-applied `last-image` and `image-style` on every switch.

Both had the same flaw: the store copy is read-only and pinned at build time. Any change made through the Xfce GUI was either lost on the next rebuild or silently diverged from the declarative source. Meanwhile a separate `dotfiles` repository existed at `/srv/repo/dotfiles`, largely unused, holding shell rc files and scripts in a stow-style layout.

## 3. Design Decision

Three integration mechanisms were considered:

| Approach | Behavior | Verdict |
|---|---|---|
| Flake input (`path:/srv/repo/dotfiles`) | Resolves to a read-only store copy at eval time | Rejected: breaks write-through |
| Regular `home.file` sources | Copied into the store, linked from there | Rejected: same read-only problem |
| `mkOutOfStoreSymlink` | Symlink pointing at an absolute live path | Adopted |

With `config.lib.file.mkOutOfStoreSymlink "/srv/repo/dotfiles/.config/xfce4"`, home-manager creates a symlink chain that resolves to the live working tree. Consequences:

- xfconfd and applications write through the symlink into the repo.
- A rebuild never reverts anything; the repo simply holds the newest state.
- Config changes take effect without any rebuild.
- The cost is churn: every GUI change dirties `git status` until committed.

A flake input was explicitly tested against this requirement and rejected - it can only deliver a frozen store path, which defeats the entire purpose. The absolute-path design is permanent.

## 4. Work Performed

### 4.1 Repository Seeding

Content was migrated into `dotfiles` in three batches, each secret-scanned before commit:

- Batch 1 (`230854c`): full `.config/xfce4` tree, `.config/gh/config.yml`.
- Batch 2 (`f9b3ccc`): Thunar, gtk-3.0, mimeapps.list.
- Batch 3 (`c80b498`): wakectl keybindings, cudatext settings, Deskflow.conf.

`.gitignore` was hardened after discovering live secrets sitting untracked in the tree: the copyparty directory (certificates, salts, session database), the gh OAuth token file (`hosts.yml`), and the sops age key path.

### 4.2 Home-Manager Wiring

The workstation `home.nix` grew a single binding plus per-entry links:

```nix
dotfiles = "/srv/repo/dotfiles";

home.file = {
  ".config/xfce4".source = config.lib.file.mkOutOfStoreSymlink "${dotfiles}/.config/xfce4";
  # ... gh/config.yml, autostart, Thunar, gtk-3.0, mimeapps.list,
  #     wakectl, cudatext, Deskflow.conf
};
```

Corresponding nix-lab commits: `ace4172` (initial wiring), `ded5b93` (drop xfconf.settings), `b1fca80` (autostart), `0bcb602` (Thunar/gtk-3.0/mimeapps), `941e71f` (batch 3 + bin).

### 4.3 Collision Lesson

The first switch revealed a silent failure mode: without `force = true`, home-manager skips entries whose target exists as a real file. After the initial switch, the xfce4 symlink was live but `gh/config.yml` and two systemd user units were untouched originals. Two fixes followed:

- Every entry over a pre-existing path now carries `force = true`.
- Live swaps were performed manually (`mv` original aside, `ln -s` into the repo) so changes apply immediately rather than waiting for the next switch.

### 4.4 Pruning What the Model Obsoleted

- Stale zensical-build systemd **user** units (duplicates of the system-level service with a hardcoded store path) were deleted everywhere.
- The `xfconf.settings` wallpaper block was removed - desktop config belongs to the repo alone.
- Profile snapshots (`xfce4-panel.xml`, `panel/`, `mimeapps.list`) were deleted from nix-lab once unreferenced.
- Dead `.bashrc` / `.bash_profile` tracked in dotfiles were dropped: `programs.bash` generates those paths as store links, so the repo copies were unread.
- A stray real `~/.gitconfig` duplicating the home-manager git config (including a hardcoded old store path for the gh credential helper) was retired.

### 4.5 Script Wiring

The previously orphaned `bin/` scripts in dotfiles were linked to `~/bin`, and `sessionPath` gained `${config.home.homeDirectory}/bin`.

## 5. Coverage Inventory

| Path | Pattern | Excluded |
|---|---|---|
| `.config/xfce4` | dir symlink | |
| `.config/Thunar`, `.config/gtk-3.0`, `.config/wakectl`, `.config/cudatext` | dir symlinks | |
| `.config/autostart` | dir symlink | |
| `.config/gh/config.yml`, `.config/Deskflow/Deskflow.conf` | file symlinks | hosts.yml token; Deskflow tls/ certs |
| `.config/mimeapps.list` | file symlink | |
| `~/bin` | dir symlink | |
| pulse, dconf, go, google-chrome, opencode, tmuxai, copyparty, sops | not managed | runtime state, churn, or secrets |
| user-dirs.dirs/locale | not managed | written once by xdg-user-dirs-update |

## 6. Verification

End-to-end test: changing Xfce desktop settings produced immediate churn in the repo (`accels.scm`, `xfce4-desktop.xml`), committed as snapshot `b7cf804`. Both flake profiles (`workstation`, `server`) evaluate clean after every change. Pre-migration originals are preserved as `.pre-nix` siblings pending confidence.

## 7. Pending Actions

- Delete the accumulated `.pre-nix` backup directories once satisfied.
- Optional future candidates: `environment.d/`, `mpv/`, `fontconfig/` if they gain content; HM-native `xdg.userDirs` if declarative user-dirs is ever wanted.

## 8. Recommendations

- Prefer out-of-store symlinks whenever a config is edited through a GUI; reserve store copies for content nothing rewrites.
- Always set `force = true` when a symlink target may exist as a real file - otherwise home-manager skips the entry silently.
- Never point these symlinks at a flake input path; only a live tree supports write-through.
- Commit repo churn promptly; uncommitted GUI changes are indistinguishable from accidental edits.
- Keep secrets out by exclusion lists (`hosts.yml`, `tls/`, copyparty, age keys) verified with a grep pass before every batch commit.

Generated with Big Pickle (OpenCode)
