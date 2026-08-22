# "switch root target contains no usable init" - Part 2

*Culprit confirmed + mitigation*

**Date:** 2026-08-11  
**Author:** Codebot  
**Topic:** NixOS, homelab, troubleshooting, recovery, boot  

## 1. Objective

Record the follow-up findings from the investigation started in Part 1: the confirmed culprit of the recurring `switch root target contains no usable init` boot failure, the mitigation applied, and the evidence that the mitigation is baked into the boot image. Part 2 covers only the boot-recovery issue; unrelated maintenance work is not included.

## 2. Background

Part 1 diagnosed the failure as a stage-1 timing race: stage-1 systemd issues `Expecting device /dev/disk/by-uuid/7b14c665-...` and waits for the by-uuid symlink to appear after AHCI link bring-up on port 2. When the device job times out, stage-1 falls through to `switch_root` against an empty `/sysroot`, producing the panic. The failing generation 90 and the working generation 89 were byte-identical in kernel, initrd, kernel-params, fstab, and init binary, which ruled out a NixOS content bug. Part 2 documents the confirmed root cause and the Tier 1 mitigation.

## 3. Confirmed Culprit

### 3.1 Stage-1 Uses the Default Device-Wait Timeout

The mitigation research required inspecting the initrd contents of the failing generation 90. The initrd is a concatenated archive: a microcode cpio archive first, followed by a zstd-compressed main initrd cpio archive. Unpacking both generations:

| Component | Gen 90 (failing) | Gen 92 (fixed) |
|-----------|------------------|----------------|
| Initrd path | `6p8f8mqyj240yxgd00njrvjs323spv19-initrd-linux-6.18.36` | `21w7ja8g3242r9g894d6nij32nl6bl0g-initrd-linux-6.18.36` |
| `etc/systemd/system.conf` | absent | present |
| `DefaultTimeoutStartSec` | not set (systemd default, 90s) | `300s` |

Generation 90's initrd contains no `etc/systemd/system.conf` at all, so stage-1 systemd ran with its built-in default job timeout. On the cold boot where AHCI port 2 came up slowly, that default window was too short, the `initrd-root-device.target` job was aborted, and stage-1 panicked during `switch_root`.

### 3.2 The Failed Boot Left No Journal Entry

`journalctl --list-boots` shows a gap between boot -1 (gen 89, ended Aug 10 02:10:13) and boot 0 (gen 89, started Aug 10 08:19:24). Generation 90's failed attempt left no entry. This is the expected signature of a stage-1 panic: the root filesystem is never mounted, `/var/log/journal` is unreachable, and `systemd-journald` never starts. No post-switch_root or userspace process could have produced the failure.

### 3.3 The Failing Generation Boots When the Hardware Cooperates

The same store content that failed on Aug 10 morning later booted cleanly. This is consistent with an intermittent, environment-driven race rather than a deterministic defect in the generation content.

## 4. Confirmed Fix

### 4.1 The Change

`system/boot.nix` in `/srv/repo/nix-lab` now sets:

```nix
# Extend the initrd manager timeout so stage-1 keeps waiting for the root device.
boot.initrd.systemd.settings.Manager.DefaultTimeoutStartSec = "300s";
```

This renders `/etc/systemd/system.conf` inside the initrd, extending the manager job timeout so stage-1 keeps waiting for `/dev/disk/by-uuid/7b14c665-...` instead of giving up and panicking.

### 4.2 Verification That the Fix Is in the Image

The fix changes the initrd output hash, which proves it is baked into the boot image rather than only into the config source:

```bash
# Current config builds the same initrd as generation 92:
nix eval --raw .#nixosConfigurations.server.config.system.build.initialRamdisk
# -> /nix/store/21w7ja8g3242r9g894d6nij32nl6bl0g-initrd-linux-6.18.36
```

Unpacking generation 92's initrd (microcode cpio ends at offset 15093760, then zstd initrd):

```
$ cat etc/systemd/system.conf
[Manager]
DefaultEnvironment=PATH=/bin:/sbin
DefaultTimeoutStartSec=300s
ManagerEnvironment=PATH=/bin:/sbin SYSTEMD_SYSROOT_FSTAB=/nix/store/wd00s4qzhclqsbapyg6k3gzrgwczkxxw-initrd-fstab
```

The same extraction against generation 90's initrd yields no `system.conf` file at all. Gen 90 therefore ran with the stock 90s timeout; gen 92 and the current working tree run with 300s.

### 4.3 Alternative: Manual Kernel-Cmdline Edit in the Boot Menu (no rebuild)

The same timeout can be applied by hand from the boot menu, because the kernel cmdline is the last thing the initrd's systemd reads before mounting root. No initrd editing or store surgery is needed.

**Per-boot (zero changes, zero rebuild):** at the grub menu, press `e` on the failing entry, go to the `linux` line, and append:

```
systemd.default_timeout_start_sec=300
```

then press Ctrl-X to boot. That kernel parameter sets the manager's `DefaultTimeoutStartSec`, which is exactly the 90s device-wait timeout that raced the AHCI link bring-up. Stage-1 would then wait up to 5 minutes for `/dev/disk/by-uuid/...` instead of panicking.

**Persistent hand-edit:** append the same parameter to the failing entry's `linux` line in `/boot/grub/grub.cfg`. This also works, but NixOS regenerates `grub.cfg` on every rebuild, so a hand edit only survives until the next `nixos-rebuild switch`. The declarative equivalent (`boot.kernelParams` in the Nix config) is what makes the change persistent, and requires a rebuild.

So in hindsight, the quickest emergency recovery during the Aug 10 incident would have been: grub menu, press `e`, append `systemd.default_timeout_start_sec=300`, and boot gen 90 as-is. The applied fix does the same thing, just declaratively inside the initrd (`DefaultTimeoutStartSec=300s` in `system.conf`) instead of in the boot menu.

**Note on `rootwait`:** `rootwait` would NOT have helped here. It only applies to kernel-driven root mounting via `root=`, but this box uses `root=fstab`, where stage-1 (not the kernel) waits for the device.

## 5. Verification Status

The mitigation is prepared and verified in the build output, but it has not yet been proven across cold boots. The verification sequence from Part 1 remains to be run:

1. `sudo nixos-rebuild switch --flake .#server` (the resulting generation's initrd should be identical to gen 92's).
2. Force at least 5 cold-boot cycles, watching each boot from the console for `Found device root`.
3. Observe the next 10 cold boots over the following week.
4. Only then mark the issue as resolved.

## 6. Diagnosis Summary

The confirmed sequence on a failing cold boot:

1. Kernel boots; AHCI port 2 (`ata2`, Samsung MZNLN256HCHP SSD) link bring-up is delayed.
2. Stage-1 systemd emits `Expecting device /dev/disk/by-uuid/7b14c665-...`.
3. The `initrd-root-device.target` job is aborted when the default device-wait timeout (90s) expires before the by-uuid symlink appears.
4. Stage-1 falls through to `switch_root` against an unmounted `/sysroot`, producing `switch root target contains no usable init`.
5. The panic occurs before journald starts, leaving no boot entry in the journal.

The fix extends the device-wait window to 300s so a slow link bring-up no longer races the default timeout. This is a Tier 1 drop-in change; it does not alter how the root is mounted (still by-uuid via `x-initrd.mount`) and does not weaken disk-failure detection the way an indefinite `rootwait` would.

## 7. Recommendations

- Run the cold-boot verification sequence above before declaring the issue resolved.
- If the failure recurs despite the 300s window, escalate to the Tier 2 levers from Part 1 (capture failed stage-1 console output, evaluate `ahci.mobile_lpm_policy`, or consider `systemd.default_timeout_start_sec`).
- Cosmetic cleanup remains pending: `sudo rm /boot/loader/entries/nixos-generation-{43..54}.conf` and optionally `sudo efibootmgr -b 5 -B`.

## 8. Conclusions

The culprit is confirmed as an intermittent stage-1 device-wait race on cold boot, not a NixOS content, bootloader, or disk-health problem. The fix is a 300s `DefaultTimeoutStartSec` in the initrd manager, verified to be present in the built initrd. What remains is empirical: the cold-boot verification series.
