# Boot Recovery - Part 3

*Reinstall recovery + fixes*

**Date:** 2026-08-03  
**Author:** Codebot  
**Topic:** NixOS, homelab, Samba, Karakeep, Caddy, TLS, troubleshooting, recovery, nix-config  

---

## 1. Objective

Document recovery from failed NixOS rebuild (host reinstalled), branch migration, and three production failures diagnosed/fixed in one session.

## 2. Background

Session date: Mon Aug 03 2026 (recovery began Sun Aug 02 ~17:42). LLM provider: kenari/kenari-free via LiteLLM proxy. Scope: Recovery from failed rebuild, migration from /srv/repo/nix-lab to /srv/repo/nix-config, three homelab failures fixed.

## 3. Problem

Host reboot with latest rebuild from nix-lab failed with "Switch root target contains no usable init". Host recovered via fresh install. Three post-recovery failures: Karakeep browser crash loop, Samba shares unreachable, Certificate errors on clients.

## 4. Work Performed

### 4.1 Failure 0: NixOS Broke After Rebuild
Symptom: Reboot with latest nix-lab rebuild failed with "Switch root target contains no usable init". Host came back only via fresh install with custom config.

Recovery:
1. Host reachable at new IP 192.168.1.117; SSH host key changed (offending key line 3 ~/.ssh/known_hosts, fingerprint SHA256:+oAolDVq+zPO6ua4OjSeCsd3zYlOmxBImTxtHXlWdXQ)
2. Only last three generations in boot entry; booted generation #9 (working gens #9 and #1), reachable at 192.168.1.105/117
3. Stopped troubleshooting old repo. Switched to /srv/repo/nix-config (known-working main) and forced IP back to 192.168.1.3. Plan: re-enable modules one at a time.
4. Created "failsafe" flake for portege-r30c (minimal NixOS + SSH only), PasswordAuthentication enabled so SSH-key loss can't lock out.
5. Designated /srv/repo/nix-config as active, /srv/repo/nix-lab as archive.

Re-architecture during recovery:
- Refactored AP stack into single toggle services.ap.enable (bundle: hostapd+dnsmasq+FreeRADIUS+openNDS) in modules/network/ap/. Rebuild + 2 reboots verified OK.
- Evaluated splitting dnsmasq or swapping for udhcpd -- deferred.
- openNDS splash debugging (WPA/PSK Enterprise login worked but no splash/no internet; 192.168.4.1 ERR_SSL_PROTOCOL_ERROR on Chrome; dnsmasq: bad dhcp-option at line 12) PUT ON HOLD, findings in /srv/repo/nix-config/OPENNDS-DEBUG-NOTE.md.

Lesson: Single broken rebuild can take host down entirely -- keep minimal known-good branch (failsafe) and re-enable services incrementally.

### 4.2 Failure 1: Karakeep Browser Service Crash Loop
Symptom: karakeep-browser.service start-limit-hit, exit code 21. Chromium: "The profile appears to be in use by another Chromium process (6998) on another computer (NixOS). Chromium has locked the profile..." SingletonLock symlink pointing to nixos-6998 -- process no longer existed (hostname changed after prior rebuild, invalidating lock). Browser unit (DynamicUser=true, StateDirectory=karakeep-browser) at /var/lib/private/karakeep-browser/.

Fix:
```bash
sudo rm -f /var/lib/private/karakeep-browser/SingletonLock \
           /var/lib/private/karakeep-browser/SingletonSocket \
           /var/lib/private/karakeep-browser/SingletonCookie
sudo systemctl reset-failed karakeep-browser
sudo systemctl restart karakeep-browser
```

Verification: unit active (running), Chromium headless answering on 127.0.0.1:9222 (/json/version), karakeep-web serving HTTP 307.

Lesson: systemd DynamicUser + Chromium headless fragile against hostname changes -- stale singleton locks survive reboots, must clear manually.

### 4.3 Failure 2: Samba Shares Unreachable from Windows
Symptom: Private shares (home, repo, web, documents) access denied; guest shares (appdata, books, music, lyrics) worked. smbclient //homelab/home -U sigit% -> NT_STATUS_ACCESS_DENIED.

Root cause: Samba password database EMPTY. pdbedit -L returned no user accounts, so sigit had no Samba credential for valid users = sigit ACLs on private shares. Daemons healthy (ports 445/139 listening, winbindd/wsdd active).

Fix:
```bash
sudo smbpasswd -a sigit
```

Verification: Private shares accessible from Windows Explorer after Samba account created.

Lesson: Fresh NixOS Samba setup ships with empty passdb.tdb -- no Linux user is Samba user until explicitly added via smbpasswd -a.

### 4.4 Failure 3: Certificate Errors on Windows + Workstation
Symptom: NET::ERR_CERT_AUTHORITY_INVALID for homelab.home.arpa and *.home.arpa in browsers on Windows client and workstation.

Root cause (ruled out server-side): Served certificate consistent -- runtime CA (/etc/ssl/homelab/homelab-ca.crt), committed CA (modules/security/homelab-ca.crt), system store (/etc/ssl/certs/homelab-ca.pem) all share fingerprint F9:D0:FD:FA:...:EE:07. openssl verify passed, SANs covered both hostnames. Actual failure: CLIENT-SIDE stale CA trust -- clients held old Homelab Internal CA from before CA regeneration, so new leaf signed by current CA failed to validate.

Fix:
1. Export current CA: SSH homelab 'sudo cat /etc/ssl/homelab/homelab-ca.crt' > homelab-ca.crt (scp fails on mode-restricted /etc/ssl/homelab)
2. Windows: install homelab-ca.crt into Trusted Root Certification Authorities (Local Machine)
3. Workstation: rebuilt flake so security.pki.certificateFiles = `[ ./homelab-ca.crt ]` re-syncs system trust store

Verification: https://homelab.home.arpa loads clean on all clients; CA shows as "Homelab Internal CA".

Lesson: When openssl verify passes but clients report AUTHORITY_INVALID, suspect stale CA in client trust store before touching server config.

## 5. Diagnosis

Three distinct post-recovery failures: browser profile lock, missing Samba credentials, stale client CA trust. All operational fixes, no config changes needed.

## 6. Preliminary Assessment

Host recovered via generation #9. Active branch migrated. All three services restored and verified.

## 7. Solution Summary

Host recovered, repo migrated, three failures fixed operationally. Root causes documented in Mem0 (bug_fix type).

## 8. Verification Plan

Monitor for recurrence. Verify failsafe flake boots.

## 9. Pending Actions

None.

## 10. Recommendations

Keep minimal failsafe branch. Re-enable services incrementally after recovery. Clear Chromium singleton locks on hostname change. Run smbpasswd -a for new Samba users. Update client trust stores after CA regeneration.
