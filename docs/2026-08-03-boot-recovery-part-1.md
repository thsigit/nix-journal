# Boot Recovery - Part 1

*First no-usable-init failure*

**Date:** 2026-08-03  
**Author:** Codebot  
**Topic:** uncategorized  

---

## 1. Objective

Document NixOS boot failure "switch root target contains no usable init" on generations 28-31 and decision to stop troubleshooting.

## 2. Background

sudo nixos-rebuild switch --flake /srv/repo/nix-config#homelab + reboot lands on new generation but gens 28-31 all die with same console error.

## 3. Problem

Boot failure persists across generations despite configuration changes. AP bundle disabled in gen 31 -- no change.

## 4. Work Performed

### 4.1 AP Bundle Disabled
profiles/homelab/default.nix:
```nix
# was: services.ap.enable = true;
services.ap.enable = false;
```
Network module gates all five AP sub-services behind single boolean. Build verified clean (exit 0); switch ran; reboot -> same error.

### 4.2 What Was Proven NOT The Cause
- NOT AP bundle (off in gen 31)
- NOT BitRouter/LiteLLM (gen 27 boots, gen 28 fails; both have BitRouter+LiteLLM; LiteLLM store path byte-identical to working gen 27 init)
- NOT initrd (gen 27 and 28 use SAME initrd; gen 30/31 use netconsole-augmented initrd)
- NOT kernel parameters (gen 27 vs 28 identical; netconsole params only on gen 30+ initrd)
- NOT store integrity (ldd $init shows no missing libs; nix-store --verify clean)
- NOT SATA flakiness (dmesg shows ata2: SATA link up 6.0 Gbps stable; no failed command, resets, frozen)

Identical kernel (all gens -> n3y6zqiphvrsg3fxh1z2ymjhjl2qvqk2-linux-6.18.36), identical init binary hash (a48ce9d7...), identical initrd closure (CLOSURE_OK), valid init path on disk -- yet switch-root fails.

### 4.3 Session Attempts
- Added boot.initrd.kernelModules = ["e1000e" "netconsole"] + rootwait/rootdelay=10 + dual netconsole targets to capture kernel logs to 192.168.1.105:6666 (Windows listener in C:\Users\Public\netconsole.log)
- Committed 79d289b disabling AP bundle and rebuilt

On-screen error unchanged. Netconsole listener produced EMPTY log on last boot.

## 5. Diagnosis

Failure in boot/init path itself, not configuration content. Gens 28-31 fail with AP both on and off. Netconsole capture fragile: e1000e driver is module not builtin; if interface not link-up at module load or listener not reachable from initrd pre-root namespace, silent empty log.

## 6. Preliminary Assessment

Per client directive, stopping active troubleshooting. Failure requires separate boot-recovery session. Toggle commit 79d289b on main, clean build-verified delta. Nothing else half-done.

## 7. Solution Summary

Documented failure scope. Disabled AP bundle (no effect). Netconsole capture attempted (empty). Stopping per directive.

## 8. Verification Plan

Next session: apply boot-recovery hypotheses (ESP vs GRUB entry correctness, grubenv saved_entry, reliable serial/VGA console dump of initrd stage).

## 9. Pending Actions

Boot-recovery session per skill guidance. Investigate ESP/GRUB/NVRAM.

## 10. Recommendations

- Disabling services at NixOS level cannot mask boot-path failure if initrd->switch-root handoff broken
- Headless netconsole in initrd fragile when network driver is module. Next time: bind listener on box's own IP (192.168.1.3), confirm file writable before trusting
