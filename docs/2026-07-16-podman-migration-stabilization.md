# The LiteLLM Gateway Evolution - Part 1

*Podman migration & stabilization*

**Date:** 2026-07-19  
**Author:** Codebot  
**Topic:** homelab, LiteLLM, Podman, NixOS, Caddy, troubleshooting  

## 1. Objective

Stabilize LiteLLM proxy on NixOS homelab through Podman container migration, auto-restart system, and configuration fixes over three days (9 sessions).

## 2. Background

LiteLLM migrated from systemd-native service to Podman container fronted by Caddy on port 4000. Two profiles shared hardware: #homelab (headless) and #workstation (desktop GUI). Operational wrapper handled config rendering, provider management, CLI tools. Proxy unreachable initially.

## 3. Problem

Container crash-looping, config mount path mismatch between image versions, rogue provider in runtime models.json, 502 errors from Caddy, database requirements for UI, sudo policy conflicts, wall command freezing terminals, profile targeting confusion.

## 4. Work Performed

### 4.1 Day 1: Initial Access and Config Changes
- SSH into homelab, navigated to /srv/repo/nix-lab/modules/ai/
- Modified wrapper: litellm-render auto-restart via systemd path unit
- Added file watching for config.yaml
- Committed, rebuilt, tested

### 4.2 Day 1 Evening: Container Crash-Loop Fix
- Root cause 1: :main tag entrypoint reads /app/proxy_server_config.yaml, but Nix module mounted to /app/config.yaml. LiteLLM fell back to bundled Azure config and crashed.
- Root cause 2: :main nightly hangs on large configs (131 models). Switched to v1.92.0 stable.
- Version-specific mount path: v1.92.0 reads /app/config.yaml (correct), :main reads /app/proxy_server_config.yaml.
- Fixed: pinned v1.92.0, mounted to correct path.
- Removed rogue mygpu provider from runtime models.json (no API key).

### 4.3 Day 2: Provenance Tracking and No-Rebuild Provider
- Item 2: litellm-add-provider supports --models '<json>' for single-step provider+model registration. Each model gets origin.type=manual, added_at timestamp.
- Item 3: Added origin provenance metadata to models.json, threaded through renderer to config.yaml. Every model carries source (declared vs discovered vs manual). Merge logic preserves manual-origin across rebuilds.

### 4.4 Day 2 Evening: 502 Debug and Constraints
- 502 from Caddy: container up but refusing connections.
- LiteLLM v1.92.0 expects database for UI login. Rendered config had no database_url.
- Tried SQLite database_url: crash-loop. SQLite support broken in v1.92.0 image.
- Reverted to no-DB mode: proxy works, UI login non-functional (accepted).
- Three constraints documented in AGENTS.md:
  1. wall broadcasts freeze terminals -> reverted to logger only
  2. Sudo policy: passwordless for all except nixos-rebuild (prevent accidental generation changes) -> locked down
  3. #homelab vs #workstation on same hardware -> always rebuild workstation

### 4.5 Day 3: Cleanup and Documentation
- Removed duplicate cmd in Nix module (entrypoint ignores it)
- Added logs/ volume mount (harmless, journald primary)
- Updated README: pinned image, config mount path, no-DB limitation
- Certificate never the problem: Caddy serves valid *.home.arpa from Homelab Internal CA. Browser errors were client-side trust.

## 5. Diagnosis

Image version dictates config mount path. Large configs hang on nightly. Database required for UI but SQLite broken in v1.92.0. Operational constraints (sudo, wall, profile targeting) must be codified. Client-side cert trust != server cert validity.

## 6. Preliminary Assessment

Stable LiteLLM container on v1.92.0 behind Caddy. Auto-restart on config changes. No-rebuild provider registration. Provenance tracking through pipeline. Locked-down sudo policy. AGENTS.md documents operational knowledge.

## 7. Solution Summary

- Pinned LiteLLM to v1.92.0 with correct config mount (/app/config.yaml)
- Implemented systemd path unit auto-restart on config.yaml changes
- Added no-rebuild provider registration with provenance metadata
- Accepted no-DB mode (UI login non-functional, API proxy works)
- Codified 3 operational constraints in AGENTS.md
- Documented pinned image, mount path, limitations in README

## 8. Verification Plan

- Verify container stability over time
- Test auto-restart on provider/model changes
- Confirm no-rebuild provider registration works
- Validate sudo policy enforcement

## 9. Pending Actions

- Rename litellm/ to gateway/ (deferred)
- Daily fetch-models timer under wrapper (deferred)

## 10. Recommendations

- Pin container images to stable versions
- Match config mount path to image version expectations
- Accept UI limitations when database backend problematic
- Document operational constraints in AGENTS.md
- Always target workstation profile on shared hardware
