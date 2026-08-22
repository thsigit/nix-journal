# Captive Portal and Access Point Bundle - Part 4

*openNDS captive portal on NixOS*

**Date:** 2026-07-26  
**Author:** Codebot  
**Topic:** NixOS, openNDS, captive-portal, homelab, troubleshooting  

---

## 1. Objective

Install openNDS captive portal on NixOS for guest WiFi access without manual credential configuration.

## 2. Background

Homelab WiFi infrastructure ready: hostapd WPA2-Enterprise, dnsmasq DHCP, FreeRADIUS auth, nftables NAT. Missing: guest WiFi solution. Goal: openNDS v11.0.0 from GitHub with libmicrohttpd (MHD 1.0.2), declarative NixOS modules.

## 3. Problem

Seven distinct bugs discovered during deployment -- some NixOS-specific, some openNDS, some interaction bugs.

## 4. Work Performed

### 4.1 Packaging and Module Creation
Created pkgs/opennds/default.nix (builds from source) and modules/network/opennds.nix (UCI config, systemd service, shell scripts).

### 4.2 Bug 1: MHD Health Check Loop
Symptom: journalctl showed MHD starting, dying, restarting every 20s.
Root cause: openNDS health check uses wget but NixOS isolates service PATHs. wget not in service PATH.
Fix: Added wget and openNDS package to systemd path attribute.

### 4.3 Bug 2: Theme Script Path Mismatch
Symptom: Splash page didn't load, missing theme errors.
Root cause: openNDS binary expects theme_click-to-continue.sh but source has theme_click-to-continue-basic.sh.
Fix: Symlink in setupScript.

### 4.4 Bug 3: ndsctl/ndscfg Not Found
Symptom: Shell scripts failed calling bare ndsctl/ndscfg.
Root cause: ndsctl in bin/, ndscfg in lib/opennds/. Neither in script PATH.
Fix: Symlinks to /usr/local/bin/.

### 4.5 Bug 4: gatewayfqdn 'disable' Treated as Hostname
Symptom: Splash URL was disable/login -> ERR_NAME_NOT_RESOLVED.
Root cause: openNDS v11 treats 'disable' as literal hostname, not keyword.
Fix: Removed gatewayfqdn option entirely. Default (IP address) works.

### 4.6 Bug 5: NAT Firewall Mark Destroys openNDS Marks (Critical)
Symptom: Splash page showed gatewayAddress: 127.0.0.1, no client info.
Root cause: NixOS nixos-nat-pre chain does meta mark set 0x1 on ALL wlp2s0 traffic. openNDS sets auth marks 0x00030000. NixOS rule REPLACED openNDS marks.
Fix: Rewrote NAT chains using extraCommands with bitwise OR:
- meta mark set mark or 0x1 (preserves existing marks)
- Masquerade matches bit 0: meta mark & 0x1 != 0

### 4.7 Bug 6: Firewall-Start Missing nft Binary
Symptom: nft: command not found in extraCommands.
Root cause: NixOS firewall-start uses iptables, nft not in PATH.
Fix: Use full path ${pkgs.nftables}/bin/nft.

### 4.8 Bug 7: Shell Interprets & in extraCommands
Symptom: nft rules with meta mark & 0x1 caused syntax errors.
Root cause: & interpreted as shell background operator.
Fix: Heredoc with single-quoted delimiter <<'HEREDOC' prevents shell interpretation.

## 5. Diagnosis

Multiple integration points between openNDS, NixOS service isolation, nftables mark handling, and shell escaping. Each bug required different fix category.

## 6. Preliminary Assessment

All bugs fixable declaratively. Resulting config survives rebuilds.

## 7. Solution Summary

Seven bugs fixed. Final nixos-rebuild switch brought: splash page loads, click-to-continue works, internet access granted, session timeout works. Two tests confirmed.

## 8. Verification Plan

Test 1: Toggle wifi off/on -> splash -> connect -> internet.
Test 2: Fresh WPA2-Enterprise re-auth -> splash handled by Android CPD in background -> internet.

## 9. Pending Actions

Phase 4: Voucher-based login (see Part 2).
Phase 5: Database persistence (SQLite for vouchers, sessions, devices).
Phase 6: Rust backend for management.
Phase 7: Optional billing support.

## 10. Recommendations

- NixOS isolates service PATHs: declare required binaries in systemd path attribute
- Check NAT mark chains if openNDS shows gatewayAddress 127.0.0.1
- Use bitwise OR for marks: meta mark set mark or 0x1
- Use full paths in extraCommands
- Heredoc with single-quoted delimiter for nft rules
- Symlink missing binaries in setupScript
- Remove gatewayfqdn option entirely
