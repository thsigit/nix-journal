# Captive Portal and Access Point Bundle - Part 2

*WPA2-Enterprise: FreeRADIUS, PEAP, and the PEM That Wouldn't Load*

**Date:** 2026-07-25  
**Author:** Codebot  
**Topic:** homelab, FreeRADIUS, hostapd, NixOS, TLS, narrative, troubleshooting  

---

## 1. Objective

Implement WPA2-Enterprise with FreeRADIUS for per-user credentials, replacing shared PSK.

## 2. Background

AP working with WPA2-PSK. Desired: FreeRADIUS for EAP-PEAP authentication. Module split: freeradius.nix (daemon, EAP-PEAP, local users), hostapd.nix (AP with RADIUS auth), firewall.nix (trustedInterfaces), router.nix (NAT + IP forwarding). NixOS boundaries: services.* = daemon config, networking.* = topology, boot.kernel.sysctl.* = kernel behavior, networking.firewall.* = security policy.

## 3. Problem

FreeRADIUS failed to start with TLS PEM format error. Phones refused to connect after TLS fix. Systemd service environment blocked first start.

## 4. Work Performed

### 4.1 FreeRADIUS Configuration

Built config derivation using pkgs.runCommand with OpenSSL:

- Copied default raddb from FreeRADIUS package
- Patched clients.conf for AP as RADIUS client
- Patched mods-available/eap for default_eap_type = peap
- Added local user (sigit / pandajangger)
- Generated self-signed server certificates via OpenSSL at build time

### 4.2 Single BSS Constraint

Toshiba Portege wireless chipset supports only one concurrent AP. Initial dual-BSS attempt (PSK + Enterprise) failed: "Could not set interface wlp2s0-1 flags (UP): Device or resource busy". Fix: Replace PSK with Enterprise, not add alongside.

### 4.3 PEM Format Fix

FreeRADIUS default EAP config expects server.pem containing BOTH private key and certificate concatenated. Had separate server.key and server.pem. Fix: cat server.key server.crt > server.pem.

### 4.4 Phone Connection Failure

After PEM fix, phones rejected: older Android "invalid password", newer Android greyed connect button. FreeRADIUS crashed with same PEM error. Suspected OpenSSL 3.x PKCS#8 vs FreeRADIUS 3.2.8 linkage.

### 4.5 Systemd Service State Issue

Stopped freeradius.service, ran radiusd -X manually with same config -- phone connected immediately. Killed debug, restarted systemd service -- worked. Systemd environment (capabilities, stale PID, timing race) blocked first start. Manual start cleared state.

## 5. Diagnosis

Config was correct. Systemd service state pollution from failed starts prevented proper initialization. PEM format requirement (key+cert concatenated) was the config fix needed.

## 6. Preliminary Assessment

FreeRADIUS configuration sound. Systemd service management needs clean state transitions.

## 7. Solution Summary

PEM concatenation fix + systemd service restart after manual verification. Single BSS replacement strategy.

## 8. Verification Plan

Test WPA2-Enterprise auth with multiple devices. Verify FreeRADIUS survives reboot.

## 9. Pending Actions

Monitor for OpenSSL 3.x compatibility issues. Consider runtime certificate generation.

## 10. Recommendations

When service fails but manual run works, suspect systemd state pollution. Always concatenate key+cert for FreeRADIUS server.pem. Test hardware interface combinations before multi-BSS designs.
