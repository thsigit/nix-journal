# Captive Portal and Access Point Bundle - Part 7

*common/ reorg + AP revival*

**Date:** 2026-08-12  
**Author:** Codebot  
**Topic:** NixOS, homelab, refactor, housekeeping, config, openNDS, hostapd, FreeRADIUS  

---

## 1. Objective

Clean up the nix-lab repo structure and bring the dormant access-point stack back to life: rename `modules/` to `common/`, make every module under `common/ai` and `common/ap` build and work, and re-enable the bundle on the live system.

## 2. Work Performed

### 2.1 Directory Rename: modules -> commons -> common

Renamed the reusable-module directory twice in one session. First `git mv modules commons`, updated every header comment, import, and doc reference, verified with `nix flake check`. Then the user corrected the semantics: `commons` -> `common`.

Two gotchas surfaced:

- Nix flakes read the git index, not the working tree. Edits must be `git add`-ed before `nix eval`, or Nix reports `Path 'commons' does not exist in Git repository`.
- A blanket `s|commons/|common/|g` misses bare path references like `../../commons` (no trailing slash) in `profiles/server/default.nix` and `profiles/workstation/default.nix`. Those had to be fixed by hand.

Committed as `7e54a6f` and `1ac32ab`.

### 2.2 common/ap Revival

The AP bundle had been commented out since the Aug 7 litellm/postgres change (`# ./ap` in `common/default.nix`). Making it work again:

- Deleted stale `common/ap/router.nix`, an orphaned hand-rolled NAT setup nobody imported.
- Wired `opennds.nix` into the bundle. It had been orphaned: never imported, and its referenced sops secret (`opennds-faskey`) was never declared.
- Gated all three modules (hostapd, FreeRADIUS, openNDS) on a single real switch, `services.ap.enable`, which defaults to on when the directory is imported. The old header claimed this was already the case; it was not.
- Kept the modules independent: commenting out any single import still builds, verified for all three.

### 2.3 Secrets

The AP modules referenced three sops secrets that did not exist anywhere in the repo: `radius-secret`, `radius-users`, `opennds-faskey`. User provided the values; encrypted them with the homelab age key into `secrets/radius.yaml` and `secrets/opennds.yaml`, and declared all three in `system/sops.nix`.

## 3. Verification

- `nix eval` of all four configs (`server`, `workstation`, `failsafe`, `system`) succeeds.
- `nix flake check`: all checks passed. One benign evaluation warning about hostapd radios vs client-mode on the same wireless interface.
- Independence tests: commenting `./hostapd`, `./freeradius`, or `./opennds` each still builds.
- User ran `sudo nixos-rebuild switch --flake .#workstation` -- succeeded.

## 4. Pending Actions

- hostapd, FreeRADIUS, and openNDS now activate on boot. Watch the Wi-Fi network `kebabtamalate` and the captive portal on the next boot.
- The benign wireless warning could be silenced later by excluding the AP interface from client-mode management explicitly, if it becomes noisy.
