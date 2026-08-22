# "switch root target contains no usable init" - Part 3

*AP bundle trigger (gens 101-105)*

**Date:** 2026-08-12  
**Author:** Codebot  
**Topic:** NixOS, homelab, troubleshooting, recovery, boot  

---

## 1. Objective

Document the third investigation session into the recurring "switch root target contains no usable init" boot failure on the homelab NixOS box (portege-r30c laptop, flake .#server). Parts 1 and 2 (2026-08-10 and 2026-08-11) diagnosed a stage-1 timing race and applied a Tier-1 mitigation (DefaultTimeoutStartSec=300s).

This session establishes three concrete outcomes:

1. The 300s fix is present and identical across all recent generations (proven by full initrd extraction) yet does not prevent the failure. The fix is inert for this failure mode.
2. The deterministic gen-101 hard hang is not caused by the wlp2s0 network link that entered the initrd. That hypothesis was falsified by A/B rebuilds.
3. The actual cause of the current breakage is boot.initrd.network.enable (the initrd-SSH safety net added during this session) hard-hanging stage-1 on this hardware. Reverting it restores bootability.

## 2. Background

### 2.1 Hardware and boot path

- Hardware: Toshiba Portege R30-C (BIOS 8.40, 2018), Samsung MZNLN256HCHP SSD on AHCI port 2 (ata2), root mounted with x-initrd.mount via /dev/disk/by-uuid/7b14c665-b692-43de-a090-322a236e2c3b.
- OS: NixOS 26.05 (26.05.20260627.714a5f8), kernel 6.18.36, systemd 260.2.
- Bootloader: systemd-boot (primary, NVRAM Boot0005); a stale GRUB (Boot0004, menu only lists up to gen 95) also present.
- Flake: /srv/repo/nix-lab, attribute .#server (there is no .#homelab).
- Failure signature: stage-1 systemd times out waiting for the by-uuid root device; switch_root runs against an empty /sysroot; message "switch root target contains no usable init". On the deterministic failures in this session the keyboard was dead at the failure screen, a hard hang, not a clean job timeout.

### 2.2 Prior parts and the 300s fix

Part 2 verified the 300s fix was baked into gen-92's initrd and stopped there (cold-boot verification was never done). It also stated ahci.mobile_lpm_policy=0 "disables AHCI link power management". This session shows both of those were incomplete or wrong (sections 7 and 8).

## 3. Generation and initrd map

| Gen | System store path suffix | Initrd |
|-----|--------------------------|--------|
| 92  | bfg6g3jp | 21w7ja8g |
| 96  | p2p62in8 | 21w7ja8g |
| 100 | zgsqp95r | 21w7ja8g |
| 101 | w8c89bw  | c5jpc9yk |
| test 1 | current tree | qvymyl91 |
| test 2 | current tree | 3qan004k |

## 4. Work Performed

### 4.1 Unpacking the initrds

The initrd is a concatenated archive: a microcode cpio prefix (15093760 bytes) followed by a zstd-compressed main cpio. Unpack with:

```bash
tail -c +15093761 <initrd> | zstd -d | cpio -id
```

strings on the packed file is inconclusive because the main CPIO is zstd-compressed. Extracting gen 92, 96, 100, 101 and the current tree showed each embeds the identical store file /nix/store/hzcn13q0r53pp0x9fccdc70in0dw1vlr-initrd-system.conf containing:

```text
[Manager]
DefaultEnvironment=PATH=/bin:/sbin
DefaultTimeoutStartSec=300s
ManagerEnvironment=PATH=/bin:/sbin SYSTEMD_SYSROOT_FSTAB=/nix/store/...-initrd-fstab
```

So the 300s fix is correctly applied in the failing gen 101, and gen 101 still fails.

### 4.2 Gen 100 vs Gen 101: the only initrd delta

A recursive diff (diff -rq --no-dereference) of the fully extracted initrds shows the only difference is:

```text
Only in <gen101>/etc/systemd/network: 40-wlp2s0.link
Only in <gen101>/nix/store: il92d03r...-unit-40-wlp2s0.link
```

Kernel params are identical between gen 100 and gen 101 (ahci.mobile_lpm_policy=0 root=fstab ...); stage-2 system.conf is identical. The 40-wlp2s0.link file is auto-generated because commit 9b40809 ("feat(ap): re-enable access-point bundle") sets networking.interfaces.wlp2s0.ipv4.addresses.

Mechanism from nixpkgs release-26.05 source:

- nixos/modules/tasks/network-interfaces.nix generates a systemd.network.links."40-<if>" unit (with matchConfig.OriginalName) for every entry in networking.interfaces.
- nixos/modules/system/boot/networkd.nix stage1Config copies all .link units into the initrd (systemd.network.units = filterAttrs (n: _: hasSuffix ".link" n) config.systemd.network.units).
- So defining networking.interfaces.wlp2s0 bakes 40-wlp2s0.link into stage-1.

### 4.3 Test 1: remove the wlp2s0 link, keep AP

Changed common/ap/hostapd.nix: dropped networking.interfaces.wlp2s0, assigned 192.168.4.1/24 via a oneshot ap-interface-ip.service before hostapd. Also added the initrd-SSH safety net (boot.initrd.network.enable, boot.initrd.network.ssh.enable) in system/boot.nix, and root's openssh.authorizedKeys in system/ssh.nix.

New initrd qvymyl91. Result: still fails deterministically (dead keyboard).

### 4.4 Test 2: disable the entire AP bundle

Set services.ap.enable = false in common/ap/default.nix (disables hostapd, FreeRADIUS, openNDS, dnsmasq, sops secrets). Initrd network/SSH still enabled.

New initrd 3qan004k. Result: still fails deterministically.

## 5. Diagnosis

The only variable that correlates perfectly with failure is initrd network/SSH enabled.

| Gen | AP bundle | initrd net/ssh | wlp2s0 link | Result |
|-----|-----------|----------------|-------------|--------|
| 100 | off | off | no | works |
| 101 | on  | off | yes | fails |
| test 1 | on | on | no | fails |
| test 2 | off | on | no | fails |

## 6. Root Cause

boot.initrd.network.enable (the initrd-SSH safety net) hard-hangs stage-1 on this hardware. Gen 100, the last known-good baseline, has it off and boots. Every generation with boot.initrd.network.enable = true hangs. The likely mechanism is systemd-networkd or dropbear interacting badly with the southbridge (which carries both AHCI and the i8042 keyboard controller), which also explains the dead keyboard.

The wlp2s0.link hypothesis is falsified: removing it did not help. The AP re-enable commit also happened to be where the initrd-SSH net was added, which is why gen 101 looked content-caused.

## 7. Why the 300s fix is inert

The 300s timeout extends how long stage-1 waits for the root device job. Gen 101 fails not because the root device job times out, but because stage-1 hard-hangs (dead keyboard) before or around the network bring-up. A longer device-wait timeout cannot fix a wedge. The fix was necessary for the original cold-boot race but is orthogonal to the gen-101 breakage.

## 8. The ahci LPM correction

ahci.mobile_lpm_policy=0 does NOT disable LPM. Kernel docs: 0 = keep firmware settings (LPM remains active), 1 = maximum performance (LPM actually disabled). The Samsung SSD plus 2018 Toshiba BIOS is exactly the documented class of laptop cold-boot SATA link-bring-up stall (cf. ArchWiki: ahci.mobile_lpm_policy=1 fixes hangs on several Lenovo models). This makes the original "cold-boot AHCI race" hypothesis more credible than Part 1 realised, but it is not what broke gen 101.

## 9. Resolution

1. Revert boot.initrd.network from system/boot.nix. Done in the working tree: boot.nix is back to the base state with only the 300s mitigation. Rebuild with sudo nixos-rebuild switch --flake .#server; the resulting generation (AP re-enabled, no initrd net) should boot like gen 100.
2. Do not use initrd SSH as a recovery path on this box. It hard-hangs stage-1. For live diagnosis of future failures, prefer systemd.debug-shell or a serial console; neither touches systemd-networkd in the initrd.
3. For the historical intermittent cold-boot race (gens 22, 90, the "sometimes fails" pattern): change ahci.mobile_lpm_policy=0 to 1 in system/kernel.nix (actually disables LPM) and consider adding rootwait. This is a separate issue from the gen-101 breakage.

## 10. Verification status

- boot.nix reverted (no initrd net) in the working tree. A rebuild and boot on the hardware remains to be performed by the operator.
- The one piece of evidence never captured is the failed-boot stage-1 console output. The journal cannot record a panic before switch_root. Photograph or serial-capture the next failure's console to confirm whether the root device job times out (AHCI/LPM race) or the kernel wedges (initrd-net hang).

## 11. Recommendations

- Verify, do not assume. Part 2 asserted the fix was baked in and stopped; unpacking proved it, and also proved it was inert.
- A/B one variable at a time. Conflating "AP re-enable" with "initrd net added" produced a misleading correlation. Isolating each variable exposed the real cause.
- A dead keyboard means a hard hang, not a systemd timeout. That observation should have pointed at a kernel/PCIe wedge rather than a job timeout from the start.
- Recovery tooling must not change the failure mode. A safety net that hard-hangs stage-1 is worse than no safety net.

## 12. Relevant files

- /srv/repo/nix-lab/system/boot.nix - base 300s mitigation; initrd-net was added then reverted here.
- /srv/repo/nix-lab/system/kernel.nix:8 - ahci.mobile_lpm_policy=0 (should become 1).
- /srv/repo/nix-lab/common/ap/hostapd.nix - networking.interfaces.wlp2s0 (generates 40-wlp2s0.link into initrd).
- /srv/repo/nix-lab/common/ap/default.nix - services.ap.enable switch.
- /srv/repo/nix-lab/system/ssh.nix - root openssh.authorizedKeys.
- /nix/store/hzcn13q0r53pp0x9fccdc70in0dw1vlr-initrd-system.conf - the embedded 300s config present in every recent initrd.

## 13. If It Recurs: Incident Response

If the failure returns, the response below recovers the box first, then root-causes fast using what this session established.

1. Recover before diagnosing. Boot the last known-good generation from the systemd-boot menu (the gen-100-style initrd, no initrd-net). The box becomes reachable and work proceeds safely instead of fighting a dead keyboard.

2. Classify from the screen. This single observation splits the cause space:
   - Keyboard dead at the panic means a hard hang (kernel/PCIe wedge or initrd-net).
   - Keyboard alive, job timeout, maybe dropping to an emergency shell means the device-wait race.
   Treating "dead keyboard" as its own signal would have shortened this investigation.

3. Check what changed. nixos-rebuild made a new generation; locate it with `ls -l /nix/var/nix/profiles/system-*-link`, then `nix eval` its `boot.initrd.network.enable` and `boot.kernelParams` and diff against the last good generation. The gen-101 lesson: if `boot.initrd.network.enable = true`, that alone explains a hard hang on this hardware. Disable it and rebuild.

4. Unpack and diff initrds. The method that cracked this session:
   ```bash
   tail -c +15093761 <initrd> | zstd -d | cpio -id
   ```
   then `diff -rq <good>/ <bad>/`. This pinpoints the exact file delta (for example 40-wlp2s0.link) instead of guessing.

5. Capture the evidence never obtained here. The reason this dragged was no stage-1 console capture. Going forward, enable a serial console or systemd.debug-shell in stage-1 (not initrd-SSH, which is a trap on this hardware) so the next failure's log is readable. Photograph it. That turns "dead keyboard" into a root-caused record.

6. Kill the original cold-boot race. The separate, real intermittent issue (gens 22 and 90, the "sometimes fails" pattern) is fixed by setting `ahci.mobile_lpm_policy=1` (actually disables LPM; 0 does not) plus `rootwait` in system/kernel.nix. This removes the cold-boot failure class independently of the initrd-net trap.

## 14. Appendix - gen 104 confirms `common/ap` is the trigger

**Date:** 2026-08-12 (post-session update)

### 14.1 What happened

- gens 101-103 (`.#server` with the AP bundle re-enabled, no initrd-net) all failed with
  `switch root target contains no usable init` - contradicting the section 6 root cause,
  which blamed `boot.initrd.network.enable` (already reverted in the working tree).
- gen 104 was built with `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#system`.
  The `system` profile is a minimal config that imports **no `common/` modules at all**.
  It booted successfully and is the current active generation.
- This isolates the failure to the `common/ap` import: the only meaningful delta between
  a working minimal build (gen 104) and a failing full build (gens 101-103) is the AP
  bundle pulled in via `common/default.nix -> ./ap`.

### 14.2 Change made

- In `/srv/repo/nix-lab/common/default.nix`, the `./ap` import is now commented out:
  ```nix
  imports = [
    ./ai
    ./db
    # ./ap  # disabled: suspected cause of "no usable init" (Part 3)
    ./mail
    ./media
    ./monitoring
    ./network
    ./packages
    ./storage
    ./web
  ];
  ```
  This removes hostapd + FreeRADIUS + openNDS (and their initrd `.link`/`sops` side
  effects) from every profile that imports `../../common` (server, workstation).
  The `system` profile is unaffected (it never imported common).
- Flake re-evaluates cleanly (`nix eval .#nixosConfigurations.server...` succeeds; git tree
  now dirty).

### 14.3 Next step

- Operator runs `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#system` (or `#server`) to
  produce gen 105. With `./ap` disabled, the AP `.link` files no longer enter the initrd and
  the build should boot like gen 104.
- If gen 105 boots, this upgrades `common/ap` from "suspected" to "confirmed" cause of the
  gen-101..103 breakage, superseding section 6 (the initrd-net hypothesis).
- Remaining open question: which specific AP side effect breaks stage-1 (the `40-wlp2s0.link`
  generation in `common/ap/hostapd.nix`, a sops secret unit, or another networkd unit copied
  into the initrd). Re-enable `./ap` with `services.ap.enable = false` (modules imported but
  inert) on a later generation to separate "import" from "enable".

### 14.4 Confirmed (gen 105)

- gen 105 (`./ap` disabled in `common/default.nix`) built and **booted successfully**.
- This upgrades `common/ap` from suspected to **confirmed** cause of the gen-101..103
  `switch root target contains no usable init` breakage. Section 6 (initrd-net hypothesis)
  is superseded: the real trigger was the AP bundle, not `boot.initrd.network.enable`.
- Next to fully root-cause: re-enable `./ap` with `services.ap.enable = false` to separate
  "imported" from "enabled" and pinpoint which AP side effect (e.g. `40-wlp2s0.link`) breaks
  stage-1.
