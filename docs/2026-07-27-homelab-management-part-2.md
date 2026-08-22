# Homelab Management - Part 2

*Single reference skill for agents*

**Date:** 2026-07-27  
**Author:** Codebot  
**Topic:** homelab, NixOS, skills, openNDS, FreeRADIUS, hostapd, LiteLLM, openNDS, troubleshooting  

---

## 1. Objective

Create homelab-management skill: single reference document for any agent to understand homelab without re-explanation.

## 2. Background

Homelab context accumulated across dozens of sessions, memory entries, config files -- none unified. Loaded existing ssh-homelab and homelab-litellm skills. Searched Mem0: 65 memories covering WiFi debugging, FreeRADIUS TLS, openNDS, network topology, architectural decisions.

## 3. Problem

No unified reference. Agents would repeat trial-and-error cycles without consolidated knowledge.

## 4. Work Performed

### 4.1 Live System Probing
SSH into homelab, read actual configs:
- README.md: machine list (Toshiba Portege R30-C, both #homelab and #workstation), module structure, key features (NixOS 26.05, internal PKI, SOPS, Tailscale+ZeroTier)
- AGENTS.md: standing constraints (never nixos-rebuild, no wall, identical hardware, default .#workstation)
- flake.nix: entry point for both profiles
- modules/network/: WiFi stack (hostapd, FreeRADIUS, dnsmasq, openNDS, router with bitwise-OR mark fix)
- modules/security/firewall.nix: trusted interfaces, allowed ports
- settings/default.nix: canonical user, domain, paths
- pkgs/opennds/default.nix: openNDS package
- Session files: SESSION-2026-07-26-opennds.md (7 issues), SESSION-2026-07-18b-litellm.md (Podman transition)
- systemctl list-units, openNDS notes, CODE_REVIEW.md, README-opennds.md

### 4.2 Skill Content
Final SKILL.md covers:
1. Architecture overview: two profiles same hardware, network topology (enp0s31f6 -> NAT -> wlp2s0 -> clients -> Enterprise/Guest split)
2. 12 running services: hostapd, FreeRADIUS, dnsmasq, openNDS, Caddy, Tailscale, LiteLLM, linkding, wallabag, localai, vane, cockpit, darkstat (ports and roles)
3. WiFi auth strategy: WPA2-Enterprise trusted, openNDS captive portal guests
4. Debugging commands per service: ndsctl status, journalctl -fu hostapd, radiusd -X, nft list chain, podman ps
5. Nine openNDS gotchas: MHD health check (wget in PATH), theme symlink, ndsctl/ndscfg symlinks, NAT mark conflict (bitwise OR), gatewayfqdn disable literal, nft not in PATH, & shell interpretation, Android CPD background, uppercase voucher
6. LiteLLM details: Podman container, no-DB mode, config rendering, CLI tools, v1.92.0 quirks
7. Config paths: every file agent might need
8. Development roadmap: Phases 1-7, voucher system design
9. Operating constraints: never nixos-rebuild, same hardware, no wall, default .#workstation
10. TLS/PKI: Homelab CA, wildcard cert, NODE_EXTRA_CA_CERTS, FreeRADIUS PEM key format quirk
11. Firewall config: allowed ports, trusted interfaces, NAT mark handling

### 4.3 Value Capture
Skill captures WHY behind decisions, not just WHAT. Session files explain router.nix bitwise-OR, nft heredoc, FreeRADIUS server.pem. Mem0 memories fill gaps: hostapd password change, Android splash behavior, OpenSSL 3.x PEM incompatibility.

## 5. Diagnosis

Fragmented context causes repeated debugging. Unified reference prevents re-learning.

## 6. Preliminary Assessment

Single SKILL.md dense enough to orient any agent in under a minute. System is runtime; skill is map.

## 7. Solution Summary

homelab-management skill created at ~/.agents/skills/homelab-management/SKILL.md. No scripts, no helpers -- pure reference document.

## 8. Verification Plan

Test skill loading in new sessions. Verify all references accurate.

## 9. Pending Actions

Update skill as homelab evolves. Add new gotchas as discovered.

## 10. Recommendations

Skills should capture reasoning, not just facts. Include debug commands and known gotchas. Reference live config paths, not just module names.
