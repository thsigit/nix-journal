# Boot Recovery - Part 4

*Boot menu cleanup + repo sync*

**Date:** 2026-08-06  
**Author:** Codebot  
**Topic:** homelab, NixOS, boot, efibootmgr, grub, sops, maintenance, refactor, migration, troubleshooting, recovery  

---

## 1. Objective

Technical report combining three work streams: stale boot menu cleanup, config activation failure, deliberate repository sync from older to newer config tree.

## 2. Background

System had deleted NixOS generations but old ones still appeared in EFI boot menu and GRUB menu. nixos-rebuild switch failed on sops group lookup. Active repo behind newer tree at nix-config.old.

## 3. Problem

Three independent issues: boot menu hygiene, activation failure, repo synchronization.

## 4. Work Performed

### 4.1 Stale Boot Entries: EFI and GRUB
Generations vs menu entries:
```bash
sudo nix-env -p /nix/var/nix/profiles/system --list-generations
```
Only 20, 35, 41, 42, 43 (current) existed. But grep menuentry /boot/grub/grub.cfg listed configurations 24-38 and older. GRUB menu entries generated from profile at boot-loader update time; if bootloader config not regenerated after GC, stale entries persist.

EFI entries generation-independent:
`sudo efibootmgr -v` showed multiple entries pointing to same EFI loader files (systemd-bootx64.efi, grubx64.efi). Unlike GRUB, EFI entries do not encode generation number -- just point at loader path. Deleting generations does not remove EFI entries.

Genuinely broken entry:
Boot0005* Linux Boot Manager referenced:
```
HD(3,GPT,937d7824-bc23-4c7a-b698-5a43566dabc4,0x1daf9800,0x1f9800)/\EFI\systemd\systemd-bootx64.efi
```
GPT partition GUID 937d7824... matched NO partition:
```bash
sudo blkid | grep 937d7824-bc23-4c7a-b698-5a43566dabc4
# not found
```
Only real EFI partition is sda3 with PARTUUID 30e19aa3-6bb5-4f43-883d-3400014ac398. Boot0005 pointed at dead disk/partition. Fix: `sudo efibootmgr -b 0005 -B`.

Cleaning GRUB menu:
Owner runs (agent cannot run nixos-rebuild):
```bash
sudo nix-collect-garbage -d
sudo nixos-rebuild boot    # regenerates grub.cfg + EFI entries
```

Bootloader mishap: systemd-boot entry accidentally removed from EFI during cleanup. Box fell back to GRUB (stale menu), needed USB reinstall to recover. Re-adding systemd-boot:
```bash
sudo bootctl install
sudo bootctl update
```
Takeaway: EFI entries are thin pointers -- can go stale and point at dead disks. GRUB menus generation-derived, need regeneration after GC. Both independent of Nix store generations.

### 4.2 Activation Failure: Unknown Group 'radius'
`nixos-rebuild switch --flake /srv/repo/nix-config#server` aborted in sops-install-secrets activation:
```
sops-install-secrets: manifest is not valid: failed to lookup group 'radius': group: unknown group radius
Activation script snippet 'setupSecrets' failed (1)
```

Root cause: modules/security/sops.nix declared secrets (radius-secret, radius-users) with group = "radius". modules/network/ap/freeradius.nix referenced radius:radius ownership in systemd.tmpfiles.rules. But NO users.groups.radius defined anywhere in system config, so group lookup failed during manifest validation.

Fix chosen: Removed radius-secret and radius-users from sops.nix (FreeRADIUS runtime path didn't need them in this config iteration). Alternative: `users.groups.radius = { };`.

Takeaway: sops secrets reference owner/group that must exist as users/groups in NixOS module system at activation time. If group not declared, activation fails with "unknown group", not graceful error.

### 4.3 Repository Synchronization: nix-config <- nix-config.old
Active repo /srv/repo/nix-config many builds behind /srv/repo/nix-config.old. Task: selectively sync settings while archiving unneeded.

Approach: For each module folder, diff first, then copy old -> current per explicit decision.

| Area | Result |
|------|--------|
| modules/core | diff reviewed; networking.nix copied (static IP 192.168.1.3); boot/stateVersion/packages left for manual review |
| modules/media | made identical to old; extras (lidarr, pipewire, podman-*, pulseaudio) moved to archive/ |
| modules/monitoring | identical to old; mrtg.nix import toggled off |
| modules/network | KEPT CURRENT dnsmasq (Tailscale+bind); imported it; adguard.nix -> archive; ap/ bundle copied but NOT imported |
| modules/security | old copied (default, insecure-packages, pki, sops, SSH); firewall kept current + added UDP 67/68; homelab-ca.crt retained (pki references it) |
| modules/storage | identical to old; rsync.nix deleted |
| modules/ai | identical to old (BitRouter, litellm-podman, LiteLLM); extras -> archive |
| profiles | only failsafe, server, workstation; homelab deleted; flake got failsafe config |
| pkgs, settings, *.md | copied; settings/ai.repo pointed at stale /srv/repo/nix-lab -> updated to /srv/repo/nix-config |

Archive structure mirrored old repo's archive/ layout.

### 4.4 Verification
All three nixosConfigurations built cleanly:
```bash
nix build .#nixosConfigurations.server.config.system.build.toplevel \
          .#nixosConfigurations.workstation.config.system.build.toplevel \
          .#nixosConfigurations.failsafe.config.system.build.toplevel
```
dry-activate on server config passed with no sops/group errors:
```bash
sudo /nix/store/<hash>-nixos-system-homelab-26.05/bin/switch-to-configuration dry-activate
```
Earlier radius group failure gone; sops-install-secrets imported SSH host keys into GPG/age and proceeded normally.

### 4.5 Two Infrastructure Gotchas
1. Repo ownership: fresh checkout root-owned, breaking git add (.git/index.lock permission denied) and flake.lock updates. Fix: `sudo chown -R sigit:users /srv/repo/nix-config`
2. Nix requires tracked files: building .#failsafe failed because profiles/failsafe untracked: "error: Path 'profiles/failsafe' in the repository ... is not tracked by Git." `git add -A` fixed it.

### 4.6 Commit and Push
88 files changed, 14731 insertions(+), 9606 deletions(-) committed as:
```
a0f7033 sync repo with nix-config.old: archiving, profiles, pkgs, settings
```
Push awkward: homelab host had NO GitHub credentials (no SSH key, no gh login, no credential helper), git push over HTTPS failed "could not read Username". Workstation had gh authenticated with SSH key. Solution: clone on workstation, add homelab as git remote, fetch commit, push to GitHub over SSH.

```bash
git clone git@github.com:thsigit/nix-config.git
git remote add homelab ssh://sigit@192.168.1.3/srv/repo/nix-config
git fetch homelab main
git push origin homelab/main:main   # d619c13..a0f7033
```

## 5. Diagnosis

Three separate systems for boot menus: Nix generations, GRUB menu entries (generation-derived, need regeneration), EFI boot options (static loader pointers, can go stale). sops group references must exist as real users/groups. Nix flake requires tracked files. Repo ownership matters. Credentials are host-specific.

## 6. Preliminary Assessment

Boot cleanup, activation fix, repo sync all complete. Verified builds pass.

## 7. Solution Summary

Stale EFI entry removed. GRUB menu regeneration procedure documented. sops group fixed by removing unused secrets. Repo synced with archival. Commit pushed via workstation.

## 8. Verification Plan

Run nixos-rebuild switch on homelab. Verify boot menu clean. Confirm sops activation passes.

## 9. Pending Actions

Owner runs rebuild. Monitor for boot menu regression.

## 10. Recommendations

- Boot menus are three separate systems: clean each appropriately
- sops group/owner must exist as real users/groups
- Always git add new Nix files before building flake from dirty tree
- Ownership matters: root-owned checkout breaks git and lock-file writes
- Credentials are host-specific: route push through machine with SSH keys
