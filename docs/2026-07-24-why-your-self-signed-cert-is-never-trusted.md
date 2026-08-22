# Why Your Self Signed Cert Is Never Trusted

**Date:** 2026-07-24  
**Author:** Codebot  
**Topic:** SSL, troubleshooting, NixOS, Caddy, homelab  

---

## 1. Objective

Diagnose and fix self-signed certificate trust failures for *.home.arpa services behind Caddy reverse proxy.

## 2. Background

Adding new services to homelab triggered browser "Your connection is not private" errors. Wildcard certificate (*.home.arpa) signed by Homelab Internal CA, Caddy in front. Certificate on disk correct, CA correct, but Chrome rejected: "This server could not prove that it is homelab.home.arpa."

## 3. Problem

Two-layer issue: (1) Caddy serving stale certificate without new SAN entries, (2) Certificate chain broken server-side (AKI/SKI mismatch) not client-side.

## 4. Work Performed

### 4.1 Layer 1: Caddy Certificate Cache
Caddy starts once, caches certs in memory. Adding litellm.home.arpa triggered homelab-cert.service to regenerate cert with new SAN, but Caddy (running since July 18) served old cert without LiteLLM in SANs. Wildcard should cover but old cert issuer pointed to deleted CA key.

Fix: sudo systemctl reload Caddy

### 4.2 Layer 2: Broken Chain Server-Side
Served leaf cert AKI (E0:5B:7E:BB...) != Current CA SKI (81:7A:0B:8D...). Leaf signed by different (old) CA. Manual homelab-ca.service restart regenerated CA with new key, leaf re-signed on disk by new CA, but Caddy still served old leaf signed by old CA (deleted from Windows store).

### 4.3 Diagnosis Method
Compared served vs disk certificates:
```
echo | openssl s_client -connect 127.0.0.1:443 -servername litellm.home.arpa 2>/dev/null | openssl x509 -noout -sha256 -fingerprint
sudo openssl x509 -in /etc/ssl/homelab/homelab.crt -noout -sha256 -fingerprint
```
Different fingerprints confirmed Caddy serving stale. openssl verify on disk files said OK, served cert failed.

### 4.4 Three-Part Fix
1. homelab-cert.service now runs systemctl reload-or-restart caddy.service after cert generation
2. homelab-ca.service deletes stale leaf, triggers homelab-cert to re-sign, then reloads Caddy
3. Import CA into Windows certificate store (only actual client-side issue)

### 4.5 PKI Service Bootstrap Fix
RemainAfterExit=true prevented re-run on nixos-rebuild switch. Removed it for idempotency. Added install -d for directory creation independence. Added requires = [ "homelab-ca.service" ] on cert service.

## 5. Diagnosis

Root cause: Caddy in-memory cache vs disk reality. Chain break from CA regeneration without leaf re-sign + Caddy reload. Browser error message misleading -- often server-side, not client trust.

## 6. Preliminary Assessment

Certificate lifecycle management must coordinate CA, leaf, and proxy reload atomically.

## 7. Solution Summary

Automated Caddy reload on cert/CA changes. Fixed PKI service idempotency. Client CA import still needed.

## 8. Verification Plan

Add new service, verify cert regenerates, Caddy reloads, browser trusts. Check openssl fingerprint match.

## 9. Pending Actions

Monitor for stale cert issues on future service additions.

## 10. Recommendations

Always compare served vs disk cert fingerprints when trust fails. Automate proxy reload in cert generation pipeline. Don't trust browser error messages -- verify chain independently.
