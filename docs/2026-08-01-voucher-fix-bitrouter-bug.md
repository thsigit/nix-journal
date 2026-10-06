# Captive Portal and Access Point Bundle - Part 6

*Voucher fix + BitRouter bug*

**Date:** 2026-08-01  
**Author:** Codebot  
**Topic:** NixOS, homelab, openNDS, BitRouter, LiteLLM, wifi, captive-portal  

---

## 1. Objective

Fix guest WiFi voucher login, catch latent BitRouter bug, draft gateway refactor plan.

## 2. Background

openNDS captive portal serving splash page correctly but "Continue" with voucher returned "Login failed."

## 3. Problem

Three issues: stale faskey mismatch, stale browser fas value, latent BitRouter databaseUrl default.

## 4. Work Performed

### 4.1 Splash Voucher Acceptance Fix
Journal showed daemon computing SHA-256 of client hid + faskey. Hash mismatch: daemon using hardcoded default 1234567890 (old commit), /etc/config/opennds rewritten at 18:18 with real sops secret 7a6f148b4ab55ef6bc22e1927c610158. Daemon started at 17:59 BEFORE config written, never re-read it.

Root cause: openNDS reads /etc/config/opennds ONLY at startup. Theme reads live. Config change after daemon start = stale-key mismatch.

Fix: restart openNDS. Deadlocked: systemctl restart openNDS -> ExecStop: ndsctl stop -> dnsconfig.sh restart_only -> systemctl restart dnsmasq -> dnsmasq job stuck waiting on openNDS stop. systemctl cancel <job-id> broke cycle. New daemon PID 552322, correct faskey, hash matched.

User retried: still failed. Daemon had right key but browser submitted stale fas value -- splash page rendered before restart, embedding old hid. Daemon reassigned new hid. Reloading splash page fixed.

Lesson: any faskey/config change requires daemon restart AND client splash reload. UX friction noted.

### 4.2 Latent BitRouter Bug
BitRouter databaseUrl default in modules/ai/bitrouter/settings.nix rendered host path SQLite:///srv/appdata/bitrouter/bitrouter.db. In container mode, daemon runs in Podman mounting state dir at /var/lib/bitrouter. Host path doesn't exist in container -- daemon creates fresh DB in ephemeral layer, BitRouter key sign writes to mounted volume. Keys never validate.

Running config at /srv/appdata/bitrouter/bitrouter.yaml already had correct container path (seeded manually), so auth worked NOW. But fresh seed/rebuild would break.

Fix: make default mode-aware:
```nix
default = if cfg.mode == "container"
  then "sqlite:///var/lib/bitrouter/bitrouter.db"
  else "sqlite://${stateDir}/bitrouter.db";
```
Committed as 1b1c7b0. Picked up on next nixos-rebuild switch.

### 4.3 Gateway Refactor Plan
User asked to bundle AI gateway (LiteLLM/BitRouter via HTTPS) and Internet gateway (hostapd/freeradius/opennds) into self-contained directories, each enabled with single line.

Drafted task instruction saved to /srv/repo/nix-lab/sessions/2026-08-01-gateway-service-refactor.md and locally.

Plan:
- modules/gateways/ai-gateway/ : bundles LiteLLM (Podman) and BitRouter (container), owns models/providers config, sops wiring, Caddy reverse proxy
- modules/gateways/internet-gateway/ : bundles hostapd + FreeRADIUS + openNDS + dnsmasq/router bits
- Each enabled via single flag (services.aiGateway.enable, services.internetGateway.enable)
- modules/ai and modules/network shed gateway code, keep legacy re-exports
- Unrelated systemPackages from modules/ai moved to dedicated profile

Eleven acceptance criteria from "one-line enable" through "docs updated" to "end-to-end functional after rebuild."

## 5. Diagnosis

openNDS reads config only at startup. BitRouter default path not mode-aware. Gateway modules scattered across trees.

## 6. Preliminary Assessment

Fixes applied. Refactor plan ready for execution.

## 7. Solution Summary

openNDS restart + splash reload fixes voucher login. BitRouter databaseUrl mode-aware default prevents future breakage. Gateway refactor planned with 11 acceptance criteria.

## 8. Verification Plan

Run rebuild for BitRouter fix. Test voucher login after restart. Execute gateway refactor per plan.

## 9. Pending Actions

User runs rebuild for BitRouter fix. Gateway refactor as next major task (multi-session). Stale-fas UX friction on backlog: auto-refresh splash or surface "session expired, reload" message.

## 10. Recommendations

Document config-read timing for services. Make defaults mode-aware for container/native variants. Bundle related services into single-toggle modules.
