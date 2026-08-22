# Captive Portal and Access Point Bundle - Part 3

*Runtime-editable RADIUS users*

**Date:** 2026-07-26  
**Author:** Codebot  
**Topic:** homelab, FreeRADIUS, hostapd, NixOS, troubleshooting, narrative  

---

## 1. Objective

Replace hardcoded FreeRADIUS users with runtime-editable users file to avoid rebuilds for new users.

## 2. Background

Part 1: FreeRADIUS running, phones connected, EAP-PEAP working. But config hardcoded in Nix store -- new user required full rebuild.

## 3. Problem

Needed simpler user management without rebuilds. $INCLUDE directive added pointing to /srv/appdata/freeradius/users with preStart seeding and tmpfiles for directory.

## 4. Work Performed

### 4.1 Runtime Users File
Added $INCLUDE /srv/appdata/freeradius/users to authorize config. preStart seeds file on first start. Workflow: edit file, restart FreeRADIUS, no rebuild.

### 4.2 Password Typo Issue
Users file overwritten, sigit missing. Restored users, reloaded. radtest local: Access-Reject. radiusd -X debug: Access-Accept. Systemd service runs as radius user with ProtectSystem=full.

Root cause: Password typo -- pandajagger in Nix config vs pandajangger in users file (rogue 'n'). Fixed typo, reloaded. Still rejected.

### 4.3 Reload vs Restart
FreeRADIUS SIGHUP reload silently ignores new $INCLUDE paths not in original config. systemctl reload returned OK but config not picked up. Full restart fixed instantly.

### 4.4 Infrastructure Check
dnsmasq dead: inactive since 12:04:55, dependency failed. No DHCP, no IPs. Phones couldn't get lease. systemctl start dnsmasq restored it.

## 5. Diagnosis

FreeRADIUS reload doesn't re-read $INCLUDE files added after initial config. Infrastructure dependency (dnsmasq) failed silently, masking auth issues.

## 6. Preliminary Assessment

Runtime users file works but requires full restart, not reload. Always verify infrastructure services first.

## 7. Solution Summary

Runtime users file with $INCLUDE. Fixed password typo. Used restart not reload. Restarted dnsmasq.

## 8. Verification Plan

Add new user to runtime file, restart FreeRADIUS, test auth. Monitor dnsmasq stability.

## 9. Pending Actions

Typo-proof passwords (use UUIDs). Document reload vs restart behavior.

## 10. Recommendations

- FreeRADIUS HUP reload doesn't re-read new $INCLUDE files: restart when in doubt
- Check infrastructure (DHCP/DNS) before debugging auth
- Use distinct passwords to avoid typo confusion
