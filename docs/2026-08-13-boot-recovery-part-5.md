# Boot Recovery - Part 5

*Emergency grub failsafe entry*

**Date:** 2026-08-13  
**Author:** Codebot  
**Topic:** NixOS, troubleshooting, recovery, fallback, homelab  

---

## 1. Objective

Provide an emergency grub boot entry on the homelab that always boots the
current NixOS generation, usable as a fallback when systemd-boot is the primary
loader. The entry must coexist with the standard NixOS and "All configurations"
grub entries and must never clobber them.

## 2. Background

The homelab boots via UEFI with two loaders installed on the ESP (`/boot`,
sda3, vfat, uuid `3E08-3093`):

- Boot0004 "NixOS-boot" -> `\EFI\NixOS-boot\grubx64.efi` (grub, first in BootOrder)
- Boot0005 "Linux Boot Manager" -> `\EFI\systemd\systemd-bootx64.efi` (systemd-boot)

systemd-boot is the day-to-day primary; grub is kept as an emergency loader.
The root filesystem uuid is `7b14c665-b692-43de-a090-322a236e2c3b` and `/nix`
lives on the root filesystem (not a separate mount).

The original motivation was a cold-boot failure: "switch root target contains
no usable init". Slow AHCI link bring-up occasionally exceeded stage-1's default
wait, so the root device was not ready in time. That was mitigated separately by
raising `boot.initrd.systemd.settings.Manager.DefaultTimeoutStartSec` to `300s`.
The grub failsafe entry is a second line of defence: if the systemd-boot menu
ever fails to present a bootable generation, the operator can drop to the grub
menu and pick a known-good entry.

## 3. History

An earlier attempt handcrafted a single grub menuentry in `/boot/grub/grub.cfg`
so the current generation (gen 117 at the time) would boot. That worked once but
did not track new generations and was fragile against grub regenerating the file.

## 4. Symptoms

Iterating on an automated solution surfaced several distinct failures:

- `sed: command not found` during `nixos-rebuild switch`.
- The same failure reappeared after switching the script to `awk`.
- "Failed to run activate script" with no obvious cause; `grub.cfg` remained a
  single manually edited block (no NixOS / All configurations entries).
- Switching `boot.nix` to grub and rebuilding produced no full grub menu.

## 5. Work Performed

### 5.1 First attempt: activation script with sed

A `system.activationScripts.grub-failsafe` snippet computed the kernel/initrd
paths from the booted profile, copied them onto the ESP (`/boot/kernels`), and
rewrote `/boot/grub/grub.cfg` inside a marker-delimited block
(`### BEGIN /nix-manual-edit` ... `### END /nix-manual-edit`). This failed at
activation with `sed: command not found`.

### 5.2 Second attempt: activation script with awk

Replaced `sed` with `awk` for the block deletion. The rebuild still failed at
activation. Inspection of the built activate script showed the snippet itself
was reported as failed ("Activation script snippet 'grub-failsafe' failed"), and
that the activation PATH contains only coreutils (`readlink`, `cp`, `mktemp`,
`printf`, `dirname`, `basename`) - not `gnused`, `gnugrep`, `gawk`, or
`findutils`. So both `sed` and `awk` are absent from the activation environment.

### 5.3 Discovery: ordering and recursion

Two deeper problems were found:

1. The bootloader is installed by `installBootLoader` (invoked from
   `switch-to-configuration`) AFTER the activation scripts run. Even a working
   activation-script edit to `grub.cfg` would be overwritten by the freshly
   generated `grub.cfg`. So the activation-script approach can never persist the
   manual entry.
2. Trying `boot.loader.grub.extraEntries` instead caused an infinite recursion
   error, because the entry referenced `config.system.build.toplevel`, and the
   grub configuration depends on the toplevel which depends on the grub
   configuration.

### 5.4 Final solution: extraEntries with the profile symlink

The fix is to emit the entry via `boot.loader.grub.extraEntries` (generated
natively by the grub installer, no activation script) and to point it at the
stable profile symlink `/nix/var/nix/profiles/system` instead of the
per-build toplevel. The symlink is repointed at the active generation on every
switch, so the entry always boots the current generation without forcing an
evaluation-time reference to `config.system.build.toplevel`.

## 6. Diagnosis

The activation PATH is minimal (coreutils only). Any activation snippet that
relies on `sed`, `awk`, `grep`, or `findmnt` will fail and abort the entire
activation phase, preventing `installBootLoader` from running and leaving
`grub.cfg` unchanged. Separately, `extraEntries` cannot reference the per-build
toplevel without creating a cycle in the module graph.

## 7. Preliminary Assessment

The grub installer's PATH (used by `install-grub.pl`) does include `gnused`,
`gnugrep`, `findutils`, and `util-linux`, unlike the activation PATH. So the
correct home for the manual entry is the grub-generated config, not an activation
script. The only constraint is that `extraEntries` must be a static string with
no recursive references.

## 8. Fix

`system/grub-failsafe.nix` now sets:

```nix
{ config, ... }:

{
  boot.loader.grub.extraEntries = let
    prof = "/nix/var/nix/profiles/system";
    rootUuid = "7b14c665-b692-43de-a090-322a236e2c3b";
  in ''
    menuentry "NixOS - (Manual Edit)" --class nixos {
      search --set=drive1 --fs-uuid ${rootUuid}
      linux ($drive1)${prof}/kernel init=${prof}/init quiet loglevel=3 consoleblank=120 acpi_osi=Linux ahci.mobile_lpm_policy=0 root=fstab loglevel=4 lsm=landlock,yama,bpf
      initrd ($drive1)${prof}/initrd
    }
  '';
}
```

The entry references the profile symlink, which grub resolves through to the
current generation's store paths on the root filesystem, exactly like the
standard NixOS grub entries.

To materialise a frozen full grub menu as the failsafe (Option B): set
`boot.nix` to `grub.enable=true`, rebuild (`installBootLoader` writes
`grub.cfg` with NixOS + All configurations + Manual Edit), then flip back
to systemd-boot. The UEFI BootOrder still prefers grub (Boot0004), so the frozen
full grub menu is the emergency fallback while systemd-boot remains the daily
driver.

## 9. Mitigation Plan

Keep systemd-boot as the primary loader. Treat the grub "NixOS - (Manual Edit)"
entry as the always-current fallback. If a future switch ever breaks the
systemd-boot menu, reboot into the grub menu (it is first in BootOrder) and
select either the current generation or Manual Edit.

## 10. Verification Plan

- `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#server` with grub
  enabled builds `grub-config.xml` containing the Manual Edit entry.
- After rebuild, `sudo grep -E "menuentry|All configurations" /boot/grub/grub.cfg`
  shows NixOS, NixOS - All configurations, and NixOS - (Manual Edit).
- Reboot confirms the grub menu appears (UEFI prefers Boot0004) with all three
  entries, and Manual Edit boots the active generation.

## 11. Pending Actions

None. The solution is implemented, staged, and verified on hardware.

## 12. Recommendations

- Never put boot-menu edits in `system.activationScripts` - the activation PATH
  lacks sed/awk/grep/findmnt and the edit is overwritten by installBootLoader
  anyway. Use `boot.loader.grub.extraEntries`.
- Avoid `config.system.build.toplevel` inside `extraEntries`; reference the
  stable `/nix/var/nix/profiles/system` symlink instead to prevent infinite
  recursion.
- There is no first-class systemd-boot equivalent of `extraEntries`. A
  systemd-boot "bridge" entry would require a hand-written Boot Loader Spec
  `.conf` in `/boot/loader/entries/` plus ESP-resident kernel/initrd, re-written
  by an activation script. It is unnecessary here because systemd-boot already
  regenerates its per-generation entries fresh on every switch.
