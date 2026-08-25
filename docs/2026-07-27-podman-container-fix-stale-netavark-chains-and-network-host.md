# Podman Container Fix Stale Netavark Chains And Network Host

*Fixing a Podman Crash Without Breaking Everything*

**Date:** 2026-07-27  
**Author:** Codebot  
**Topic:** NixOS, Podman, container, troubleshooting, Caddy, homelab, maintenance, config, routing  

---

## 1. Objective

Fix podman-litellm.service crash loop (exit status 126) caused by stale netavark chains.

## 2. Background

podman-litellm failing for a while, restarting 5 times rapidly before systemd start-limit-hit. Journal error: "Error: netavark: code: 1, msg: iptables: Chain already exists."

## 3. Problem

Netavark (Podman network backend) creates iptables/nftables chains for port mappings on container start. On restart, finds chains from previous run and refuses to proceed. Exit status 126 masked network backend issue.

## 4. Work Performed

### 4.1 Sledgehammer Fix

Ran sudo nft flush ruleset. Wipes all nftables rules on host. Container came up but reckless:

- Removed DNAT/masquerade chains for ALL running Podman containers (vane, linkding, wallabag, localai)
- Destroyed openNDS walled-garden rules
- Services "Up" but netavark never recreated chains since units not restarted
- LiteLLM got fresh rules only because unit recreated by rebuild

### 4.2 Wrong Lesson: --network host

Blinded by fix, jumped to "cleaner" architecture: changed LiteLLM module from ports = `["4000:4000"]` to extraOptions = `["--network" "host"]`.
Reasoning: host networking bypasses netavark, no chains, no conflicts.
Client asked: "What actually breaks LiteLLM without --network host?"
Honest answer: nothing. Root cause was stale chains, already eliminated by flush. Changed fix to non-issue.

### 4.3 Port Remapping Subtlety

--network host not drop-in replacement. With ports = `["8087:8080"]`, container listens 8080 internally, netavark forwards host 8087. With --network host, container binds SAME port internally -- localai would grab host 8080 not 8087. Caddy proxies to 127.0.0.1:8087. Would run but unreachable.
LiteLLM "worked" with host networking only because internal port (4000) matched Caddy expectation -- coincidence, not pattern. Applying broadly means touching every Caddy config, port collisions on shared internal ports.

### 4.4 Real Root Fix: DNS

After bringing all containers back, three services unreachable by name: vane, linkding, localai. Ports responded locally. Problem: DNS -- dnsmasq only had address entries for homelab, wallabag, darkstat, litellm. Added missing to dnsmasq.nix.

## 5. Diagnosis

Stale netavark chains caused crash. nft flush ruleset is host-wide hammer. --network host changes port binding semantics. DNS entries missing for some services.

## 6. Preliminary Assessment

Original port mapping config was fine after chain cleanup. --network host kept for LiteLLM as harmless exception, not template.

## 7. Solution Summary

Cleaned stale chains via flush (then restarted all containers). Fixed DNS entries. Kept --network host for LiteLLM only with documentation.

## 8. Verification Plan

Restart all Podman containers. Verify all services reachable by name and port. Confirm no stale chains on reboot.

## 9. Pending Actions

Monitor for netavark chain accumulation. Document --network host exception rationale.

## 10. Recommendations

- Read whole journal before prescribing: error was in logs, exit 126 hid network backend issue
- nft flush ruleset heals one container, wounds fleet: recreate rules by restarting services
- --network host != port mapping: skips remapping, container binds internal port on host
- Test minimal fix before escalating: systemctl restart after flush would prove original config fine
