# "switch root target contains no usable init" - Part 1

*Stage-1 timing diagnosis*

**Date:** 2026-08-10  
**Author:** Codebot  
**Topic:** NixOS, homelab, troubleshooting, recovery, boot  

## 1. Objective

Diagnose the recurring boot failure on the homelab NixOS box (`portege-r30c` laptop, flake `.#server`) where the newest generation halts in stage-1 with the message `switch root target contains no usable init`. Establish whether the failure originates in NixOS configuration, bootloader state, or hardware, and propose a mitigation plan for verification in Part 2.

## 2. Background

The homelab runs NixOS 26.05 (`nixos-26.05` channel, kernel 6.18.36) from a single Samsung MZNLN256HCHP SSD on a Toshiba Portege R30-C (BIOS 8.40, dated 2018). The active bootloader is GRUB; a stale systemd-boot entry remains in NVRAM as a secondary option. Root is mounted with `x-initrd.mount`, which means stage-1 (the initrd) is responsible for mounting the real root filesystem before `switch_root` to stage-2.

The flake at `/srv/repo/nix-lab/flake.nix` exposes three configurations: `server`, `workstation`, `failsafe`. An older version of the boot-recovery skill referenced `.#homelab`, which does not exist; the correct attribute for the homelab is `.#server`.

## 3. History

The "no usable init" failure has recurred across multiple generations:

| Date | Event |
|------|-------|
| 2026-08-03 | Generation 22 fails. Reboot to gen 21 restores SSH. Diagnosis: gen 20/21/22 byte-identical in kernel, initrd, cmdline, fstab, machine-id. Failure deemed environmental. |
| 2026-08-06 | Multiple short boot cycles between 00:18 and 00:31 (boots -19 to -14 in the journal), indicating repeated failed-start attempts before a stable boot. |
| 2026-08-09 14:07 | Generation 90 built via `sudo nixos-rebuild switch --flake .#server`. |
| 2026-08-10 morning | Generation 90 fails on cold boot with the same error. User reboots to gen 89 to restore SSH. |
| 2026-08-10 | Diagnostic session (this report). |

## 4. Symptoms

The failure mode is consistent across every recurrence:

- The newest generation fails to boot. Stage-1 initrd loads, then panics with `switch root target contains no usable init`.
- Older generations boot cleanly on the same hardware, same disk, same kernel and initrd binaries - only the `init=` store path differs.
- The failing and working generations are content-identical (same kernel hash, same initrd hash, same kernel parameters, same `prepare-root` logic).
- No journal entry is left by the failed boot. The panic occurs before `systemd-journald` starts persisting to `/var/log/journal`, so `journalctl --list-boots` shows no entry for the failed attempt.
- Every observed failure happens on cold boot. Warm reboots from a running system have not triggered the issue.

## 5. Work Performed

### 5.1 Verify Generation Content Equality

Compared the failing generation 90 against the working generation 89 by reading their store paths from `/nix/var/nix/profiles/`:

| Component | Gen 89 (working) | Gen 90 (failing) | Result |
|-----------|-----------------|------------------|--------|
| Kernel | `n3y6zqiphvrsg3fxh1z2ymjhjl2qvqk2-linux-6.18.36/bzImage` | same | Byte-identical |
| Initrd | `6p8f8mqyj240yxgd00njrvjs323spv19-initrd-linux-6.18.36` | same | Byte-identical |
| kernel-params | `quiet loglevel=3 consoleblank=120 acpi_osi=Linux ahci.mobile_lpm_policy=0 root=fstab loglevel=4 lsm=landlock,yama,bpf` | identical | Match |
| init target | systemd 260 binary (hash `a48ce9d7...`) | same | Match |
| prepare-root | identical logic, differs only by the `systemConfig=` store-path line | identical logic | Match |
| Store closure | glibc, bash, systemd references resolve in `nix-store -q --tree` | resolves fully | Match |

Conclusion: generation 90's content is not the cause. Gen 89 and gen 90 are the same system; only the store paths differ.

### 5.2 Confirm the Failure Originates in Stage-1

The message `switch root target contains no usable init` is thrown by stage-1 systemd inside the initrd when it falls through to `switch_root` against an empty or unmounted `/sysroot`. It does not mean the `init` binary is missing from the store - gen 90's `init` is present and resolves cleanly. It means stage-1 never mounted the real root filesystem, so `switch_root` had no target.

### 5.3 Inspect a Working Boot's Stage-1 Sequence

Examined `journalctl -b -16` (Aug 6 00:28:56, a homelab generation with the same `ahci.mobile_lpm_policy=0` parameter). The stage-1 sequence on a successful boot:

```
systemd[1]: Trying to unpack rootfs image as initramfs...
systemd[1]: Expecting device /dev/disk/by-uuid/7b14c665-b692-43de-a090-322a236e2c3b...
kernel: ata2: SATA link up 6.0 Gbps (SStatus 133 SControl 300)
kernel: ata2.00: ATA-9: SAMSUNG MZNLN256HCHP-00000, EMT2100Q
kernel:  sda: sda1 sda2 sda3
systemd[1]: Found device SAMSUNG_MZNLN256HCHP-00000 root.
systemd[1]: Reached target Initrd Root Device.
systemd[1]: Starting File System Check on /dev/disk/by-uuid/7b14c665-...
```

Key findings from the kernel log:

- The SSD is on `ata2` (SATA port 2). Port 1 (`ata1`) reports `SATA link down` - nothing attached.
- The Samsung SSD has Dev-Sleep and DIPM power-management features enabled.
- `ahci.mobile_lpm_policy=0` is in the kernel cmdline, which disables AHCI link power management.
- From kernel start to `Found device root` is roughly one second on a successful boot.

### 5.4 Inspect fstab

`/etc/fstab` (generated from the NixOS `fileSystems` option) mounts root with `x-initrd.mount`:

```
/dev/disk/by-uuid/7b14c665-b692-43de-a090-322a236e2c3b / ext4 x-initrd.mount 0 1
/dev/disk/by-uuid/3E08-3093 /boot vfat fmask=0077,dmask=0077 0 2
/dev/disk/by-uuid/6369bfa1-6c53-4a13-8afc-e873a00ddf33 /srv ext4 defaults 0 2
```

Root is mounted by-uuid, and stage-1 (not stage-2) is responsible for it. The by-uuid symlink only appears in `/dev/disk/by-uuid/` once the kernel has fully enumerated the disk. This is the dependency that can race with the AHCI link bring-up.

### 5.5 Confirm the Failed Boot Left No Journal Record

`journalctl --list-boots` shows a gap between boot -1 (gen 89, ended Aug 10 02:10:13) and boot 0 (current gen 89, started Aug 10 08:19:24). Generation 90's failed attempt left no entry - the panic happened before journald persisted anything. Only an on-screen panic at the console would have been visible.

### 5.6 Update the boot-recovery Skill

Corrected two stale references in `~/.config/opencode/skills/boot-recovery/SKILL.md`:

- `.#homelab` replaced with `.#server` everywhere (the flake exposes `server`, `workstation`, `failsafe`; there is no `homelab` attribute).
- `modules/core/boot.nix` replaced with `system/boot.nix` (the file's internal header comment still says `modules/core/boot.nix` - that comment is stale; the actual path is `system/boot.nix`).
- Added a 2026-08-10 session log entry documenting the gen 89/90 verification, the stage-1 race diagnosis, and the cosmetic cleanup steps for the stale systemd-boot entries.

## 6. Diagnosis

The failure is a stage-1 timing race. Stage-1 systemd issues `Expecting device /dev/disk/by-uuid/7b14c665-...` and waits for the by-uuid symlink to appear. On this Toshiba Portege R30-C (BIOS 8.40 from 2018), cold-boot AHCI link bring-up on port 2 is sometimes delayed. When the device job times out before the by-uuid symlink appears, stage-1 falls through to `switch_root` against an empty `/sysroot`, producing `switch root target contains no usable init`.

The intermittency is consistent with a hardware-level race:

- The disk is healthy (SMART PASSED on 2026-08-03, no reallocated sectors).
- The store content is fine (byte-identical between failing and working generations).
- The bootloader is fine (grub.cfg is fresh, NVRAM boot order points at grub first).
- Once the disk is up, the system runs stably for days.
- Cold boot is the trigger, not warm reboot.

Confidence: high for the what (stage-1 cannot see root on `/dev/disk/by-uuid/...`). Medium for the why (AHCI link bring-up race on cold boot). A definitive confirmation would require capturing the failed boot's stage-1 console output, which the journal does not preserve.

## 7. Preliminary Assessment

This is not a NixOS content bug. It is a stage-1 timing race on a specific laptop's AHCI port. The recurring nature suggests the BIOS/AHCI firmware does not always bring port 2 up within stage-1's device-wait window. No amount of `nixos-rebuild` against the current configuration will eliminate the failure, because the configuration is already correct - it is the hardware's response to cold boot that varies.

## 8. Fix is a Work in Progress

This report is Part 1 of 2. Part 2 will document the chosen mitigation and its verification results once a fix is in place and tested across multiple cold boots.

## 9. Mitigation Plan

The levers, in rough order of invasiveness:

### Tier 1 - Safer, drop-in changes

1. Increase stage-1's root device timeout. NixOS exposes `boot.initrd.systemd` options; extending the wait would give a slow AHCI link bring-up more time before stage-1 gives up. Research needed: the right knob in NixOS 26.05's stage-1 systemd initrd configuration.
2. Switch root mount from by-uuid to by-partlabel or by-path. The by-uuid symlink only appears after full disk enumeration. By-partlabel or by-path symlinks can appear earlier in the device probe. This changes only the `fileSystems` NixOS option - no store content change.
3. Pin root via `root=/dev/sda1` instead of `root=fstab`. Most invasive of Tier 1 because it bypasses the fstab and by-uuid indirection. Worth trying only if the by-uuid symlink itself is the lagging artifact. Not preferred yet.

### Tier 2 - Kernel / boot-args tuning

4. Test alternative `ahci.mobile_lpm_policy` values. The current `0` (disabled) was set to fix stability on mobile chipsets, but disabling SLPM might actually be making cold-boot link bring-up flakier on this specific Samsung SSD. Empirical test on cold boot required.
5. Add `rootwait` to the kernel cmdline as a belt-and-braces fallback. `rootwait` makes the kernel block indefinitely until the root device appears, bypassing stage-1's timeout. Reasonable safety net, but it would mask a genuinely dead disk - pair with smartd alerts.

### Tier 3 - Hardware / firmware

6. Try a different SATA port. The SSD is on `ata2`; `ata1` reports `link down`. If the laptop exposes a second usable AHCI port, moving the SSD off port 2 might sidestep the race. Unlikely on a Portege R30-C, but check the service manual.
7. Firmware. Toshiba's last BIOS for this model is 8.40 from 2018. No newer firmware exists.
8. Replace the SSD or disk cable. Last resort; only justified if Tier 1 and Tier 2 attempts fail to reduce the recurrence rate.

## 10. Verification Plan

Once a mitigation is in place:

1. Force at least 5 cold-boot cycles.
2. Watch each boot from the console for `Found device root`.
3. If all 5 come up cleanly, observe the next 10 cold boots over the following week.
4. Only then mark the issue as resolved and document in Part 2.

## 11. Pending Actions

- Confirm the diagnosis by capturing one failed boot's stage-1 console output (via serial console if available, or by attaching a monitor and photographing the panic).
- Pick one Tier 1 mitigation and prepare the corresponding `system/boot.nix` or `hardware-configuration.nix` edit in `/srv/repo/nix-lab`.
- Apply the change (`sudo nixos-rebuild switch --flake .#server`), then perform the cold-boot verification sequence.
- Cosmetic: `sudo rm /boot/loader/entries/nixos-generation-{43..54}.conf` to drop stale systemd-boot entries; optionally `sudo efibootmgr -b 5 -B` to remove the unused `Linux Boot Manager` NVRAM entry.
- Document the chosen mitigation's effect in Part 2.

## 12. Recommendations

Until the fix is verified, stay on generation 89. Do not reboot into generation 90. If a cold boot fails again, interrupt the boot menu and pick gen 89 (or an earlier known-good generation) to restore SSH. The boot-recovery skill has been updated with the correct flake attribute (`.#server`), the correct bootloader config path (`system/boot.nix`), and the 2026-08-10 session findings.
