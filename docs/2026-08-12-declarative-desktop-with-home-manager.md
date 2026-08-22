# Declarative Desktop Config with Home-Manager on NixOS

**Date:** 2026-08-12  
**Author:** Codebot  
**Topic:** NixOS, homelab, config, desktop, home-manager  

---

## 1. Objective

Bring the `#workstation` profile under home-manager management: install home-manager as a flake input, adopt the user's Xfce desktop config (panels, wallpaper), unify the git identity, and manage a handful of dotfiles declaratively instead of relying on files that drift at runtime.

## 2. Background

The homelab repo (`/srv/repo/nix-lab`) is a flake-based NixOS configuration. The `#workstation` profile (`profiles/workstation/`) was previously system-only: `xfce4.nix` enabled the Xfce desktop and `packages.nix` provided packages, but all per-user settings lived as mutable dotfiles in `/home/sigit`. A prior session had already created a minimal `#system` test flake and switched every flake to systemd-boot; this session extended the flake to add home-manager and started migrating user config into it.

## 3. History

- `3367f03` - Add home-manager for user sigit (flake input, NixOS module, initial `home.nix`)
- `63b2c81` - Pin home-manager to `release-26.05`
- `412a2c9` - Declarative Xfce panel config + wallpaper
- `fa7272e` - Stretched wallpaper, drop unused icon/theme packages
- `afc3a8e` - Wallpaper image-style scaled (3)
- `866741c` - Unify git identity, manage autostart + mimeapps
- `3c1f8ac` - Sync panel config, force home.file ownership

## 4. Work Performed

### 4.1 Flake Integration

Added `home-manager` as a flake input following `nixpkgs`, passed it through `commonSpecialArgs`, and imported `home-manager.nixosModules.home-manager` in `profiles/workstation/default.nix`. Enabled `useGlobalPkgs` and `useUserPackages`, then pointed `users.sigit` at `./home.nix`.

The initial `home.nix` was minimal: bash with completion, git with a placeholder identity, and `stateVersion = "26.05"`.

### 4.2 Pin to release-26.05

The unpinned input resolved to a recent `master` commit whose `stateVersion` values (e.g. `26.11`) did not match the system's `26.05`. Pinned the input to the `release-26.05` branch, which also guaranteed the `xfconf` module was present in the pinned version.

### 4.3 Declarative Xfce Panel

Rather than re-deriving every panel property through `xfconf-query`, the current `xfce4-panel.xml` was copied verbatim into the repo (`profiles/workstation/xfce4-panel.xml`) along with the four launcher `.desktop` files referenced by plugins 13-16 (`profiles/workstation/panel/launcher-*/`). All six files are declared under `home.file`.

### 4.4 Wallpaper via xfconf

The `xfconf.settings` module (available in the pinned release) is used to set the desktop backdrop:

```nix
xfconf.settings = {
  "xfce4-desktop" = {
    "backdrop/screen0/monitoreDP-1/workspace0/last-image" = "${wallpaper}";
    "backdrop/screen0/monitoreDP-1/workspace0/image-style" = 3;
    "backdrop/screen0/monitoreDP-1/workspace0/image-show" = true;
  };
};
```

The wallpaper source is `assets/wallpaper.jpg` (already tracked in the repo), referenced as a relative path so it resolves to a store path. The monitor name (`eDP-1`) was confirmed via `xrandr` on the live session.

The image style was iterated: `5` (zoom) initially, then `4` (stretched), finally settled on `3` (scaled/fit).

### 4.5 Theme Cleanup

While reviewing, the user removed three unused icon/theme packages from `xfce4.nix` (`papirus-icon-theme`, `arc-theme`, `plano-theme`). The active `xsettings.xml` already referenced `Vimix-jade-dark` and `Bibata-Modern-Ice`, so the removals were safe.

### 4.6 Git Identity Unification

The existing `~/.gitconfig` carried the personal identity `thsigit <th.sigit@gmail.com>` plus a `safe.directory` entry for `/srv/repo/nix-config`, while home-manager's `programs.git` had been seeded with a homelab identity (`sigit.prasetyo@home.arpa`). These were unified by pointing `programs.git.settings` at the personal identity and preserving the `safe.directory` entry:

```nix
programs.git = {
  enable = true;
  settings = {
    user.name = "thsigit";
    user.email = "th.sigit@gmail.com";
    safe.directory = [ "/srv/repo/nix-config" ];
  };
};
```

Home-manager writes git config to `~/.config/git/config`; the generated `hm_gitconfig` store file was verified to contain exactly these three keys.

### 4.7 Additional Dotfiles

Two more files were pulled under management via `home.file`:

- `~/.config/autostart/Deskflow.desktop` (autostart entry)
- `~/.config/mimeapps.list` (default applications)

## 5. Diagnosis

The first real `switch` after the panel changes failed:

```text
Existing file '/home/sigit/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml'
would be clobbered
```

Two contributing causes:

1. The user had edited the panel colors at runtime, and Xfce had added a new `recent` item to the Whisker menu - so the live XML no longer matched the repo copy.
2. `home.file` by default refuses to overwrite a pre-existing file.

## 6. Fix

Two changes resolved it:

1. Re-synced `profiles/workstation/xfce4-panel.xml` from the live file so the tracked copy matches current state.
2. Added `force = true` to every `home.file` entry, so home-manager owns these files outright and activation no longer aborts when Xfce rewrites the panel config at runtime.

The follow-up `nixos-rebuild build --flake .#workstation` succeeded, and `home-manager-files` was confirmed to contain the panel XML, launchers, autostart entry, and mimeapps list.

## 7. Verification Plan

1. Run `sudo nixos-rebuild switch --flake .#workstation` and confirm `home-manager-sigit.service` activates cleanly.
2. Check that `~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml`, the launcher `.desktop` files, `Deskflow.desktop`, and `mimeapps.list` are symlinks into the home-manager generation.
3. Verify the wallpaper renders scaled (not stretched) on the eDP-1 monitor after login.
4. Confirm `git config --get user.email` returns `th.sigit@gmail.com` from a shell.

## 8. Pending Actions

- Owner to run the switch and confirm the desktop behaves after logout/login.
- Future panel edits will be reverted by the next activation (by design) - if runtime tweaks should persist, capture them back into the repo XML.

## 9. Recommendations

1. When a managed file is also written by the application (e.g. `xfce4-panel.xml`), use `force = true` and treat the repo copy as the source of truth.
2. Always pin home-manager to a release branch matching `stateVersion` to avoid schema drift.
3. Verify generated config (store files like `hm_gitconfig`) rather than assuming the module output.
4. Keep `assets/` for static media and reference it with relative paths in Nix so sources resolve to stable store paths.
5. Run `nixos-rebuild build` before committing; flake inputs that are not yet git-tracked will fail the build with a clear `git add` hint.
