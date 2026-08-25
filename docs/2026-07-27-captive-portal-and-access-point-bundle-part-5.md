# Captive Portal and Access Point Bundle - Part 5

*Voucher-based guest auth*

**Date:** 2026-07-27  
**Author:** Codebot  
**Topic:** NixOS, homelab, openNDS, FreeRADIUS, captive-portal, guest-wifi  

---

## 1. Objective

Replace click-through captive portal with voucher-based authentication for guest WiFi.

## 2. Background

Phase 3 (openNDS integration) complete -- captive portal working with click-through splash. Phase 4: voucher system requiring code for internet access.

## 3. Problem

Need voucher validation, custom splash theme, runtime configuration, and management tooling without rebuilds.

## 4. Work Performed

### 4.1 Voucher Flow
1. Guest connects to AP
2. Splash page shows 8-char input boxes: _ _ _ _ - _ _ _ _
3. Guest enters voucher (e.g. X4PJ91AK)
4. openNDS validates against static file
5. Valid: 1 hour internet access
6. Invalid/expired: access denied

### 4.2 Custom Theme (theme_voucher.sh)
Replaces username/email login with single voucher input. Features:
- 8 individual character boxes with auto-advance
- Auto-uppercase via CSS text-transform and JavaScript
- Backspace navigates to previous box
- Hidden emailaddress field (openNDS requirement)
- Server-side uppercase + dash stripping fallback

Theme at /srv/appdata/opennds/theme_voucher.sh -- runtime file, editable without rebuild.

### 4.3 Voucher Validation (binauth-voucher.sh)
Validates against /srv/appdata/opennds/vouchers:
```
X4PJ91AK 1785111321
```
Each line: code + creation timestamp. Expires 1 hour after creation. Used/expired stay with status markers.

Script: decodes base64 customdata, strips dashes, uppercases, looks up code, checks expiry, marks USED, sets session timeout, logs to syslog.

### 4.4 Runtime Configuration
Created /srv/appdata/opennds/config:
```bash
VOUCHER_VALIDITY=3600
SESSION_TIMEOUT=0
```
Edit file, restart openNDS -- no nixos-rebuild needed.

### 4.5 Management Scripts
- generate-vouchers.sh `[COUNT]`: generate random 8-char codes
- list-vouchers.sh `[all|valid|used]`: show status with expiry

### 4.6 BlastRADIUS Fix
FreeRADIUS logged: "Error: BlastRADIUS check: Received packet with Message-Authenticator."
Fix: sed command in freeradius.nix sets require_message_authenticator = yes in clients.conf during config build.

### 4.7 NixOS Module Changes
freeradius.nix: BlastRADIUS fix.
opennds.nix: login_option_enabled=3 (custom theme), themespec_path to voucher theme, custombinauth to validation script, setup script copies binauth/theme from /srv/appdata/opennds/, added ${openNDS}/lib/opennds to service PATH for ndscfg, tmpfiles rule for /srv/appdata/opennds.

## 5. Diagnosis

Runtime configuration files in /srv/appdata/ enable faster iteration. openNDS custombinauth is correct extension point for custom auth.

## 6. Preliminary Assessment

Voucher system operational. Android version differences: older handles CPD in background, newer shows full splash. Both work.

## 7. Solution Summary

Voucher-based captive portal deployed. Custom theme, validation script, runtime config, management CLIs. BlastRADIUS fixed.

## 8. Verification Plan

Test voucher generation, validation, expiry. Verify both Android behaviors.

## 9. Pending Actions

Phase 5: Database persistence (SQLite for vouchers, sessions, devices) -- skipped for now, static list sufficient.
Phase 6: Rust backend (admin dashboard, real-time monitoring, API).
Phase 7: Optional billing.

## 10. Recommendations

- Split character inputs work well for voucher/OTP forms
- Runtime config in /srv/appdata/ better than baking into NixOS modules
- openNDS custombinauth runs after standard binauth_log.sh, can override exitlevel/sessiontimeout
- ${openNDS}/lib/opennds in service PATH resolves ndscfg not found for custombinauth
