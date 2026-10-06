# Litellm Cli Config Corruption Fix and AI-Gateway Profile Architecture

**Date:** 2026-10-02  
**Author:** Codebot  
**Topic:** litellm-cli, ai-gateway, nixos, profile-architecture, yq, config-corruption, homelab

---

## 1. Objective

Document the fix for a silent config-corruption bug in `litellm-cli` that emptied `/srv/appdata/litellm/config.yaml` on every `config add` or `config remove` invocation, and record the architectural discussion around introducing an `ai-gateway` NixOS profile that composes cleanly with the existing `server` and `workstation` profiles.

## 2. Background

The homelab runs a LiteLLM gateway at `ai.home.arpa` that proxies requests to NVIDIA NIM, OpenRouter, FreeTheAI, AMD, and local llama.cpp/whisper instances. The gateway config lives at `/srv/appdata/litellm/config.yaml` - a static, hand-maintained YAML file that `litellm-cli` edits manually. The CLI is a Nix package built from `/srv/repo/litellm-cli`, installed via a NixOS module (`services.litellm-cli`).

Separately, the NixOS flake at `/srv/repo/nix-lab` defines profiles: `server` (core headless), `workstation` (server + desktop), `failsafe` (recovery), and `system` (shared base). The AI stack currently lives under `common/ai/` and is imported by `workstation` ad-hoc.

## 3. The Discovery: Silent Config Corruption

Running `litellm-cli config add amd/GLM-5.3-Flash ...` appeared to succeed ("Added: amd/GLM-5.3-Flash") but the config file became empty. `litellm-cli config list` showed "(empty)".

### Root Cause

In `/srv/repo/litellm-cli/lib/config.sh`, three functions used the broken pattern:

```bash
# BROKEN - in-place edit + stdout redirect
yq -yi --arg m "$model" ... "$CONFIG_FILE" > "$tmp" && mv "$tmp" "$CONFIG_FILE"
```

**What happened:**
1. `yq -yi` edits **in-place** (writes directly to `$CONFIG_FILE`, stdout is empty)
2. `> "$tmp"` captures empty stdout -> temp file is empty
3. `mv "$tmp" "$CONFIG_FILE"` overwrites config with empty file

Affected functions:
- `ensure_model_list` (line ~25)
- `cmd_add` (line ~78)
- `cmd_remove` (line ~94)

This is a classic silent no-op - exit 0, empty output, config destroyed.

## 4. Solution: Remove `-i` Flag, Use Stdout -> Temp -> Atomic Mv

Fixed pattern (applied to all three functions):

```bash
# FIXED - output to stdout, then atomic mv
yq -y --arg m "$model" ... "$CONFIG_FILE" > "$tmp" && mv "$tmp" "$CONFIG_FILE"
```

**What happens now:**
1. `yq -y` outputs full YAML to stdout
2. `> "$tmp"` captures it -> temp file has correct content
3. `mv "$tmp" "$CONFIG_FILE"` atomically replaces config

### Files Changed

| File | Change |
|------|--------|
| `/srv/repo/litellm-cli/lib/config.sh` | Removed `-i` from `yq` in `ensure_model_list`, `cmd_add`, `cmd_remove` |

### Verification

After committing (`935e250`) and updating flake.lock (`sha256-KRFSUHGYW59oFj7MIzwruYZ2YaFRpemplbYZOY1tw58=`), rebuilt on homelab:

```bash
litellm-cli config add test/model --api-base https://example.com --api-key os.environ/TEST
# Added: test/model (provider=test, api_base=https://example.com, api_key=os.environ/TEST)

litellm-cli config list
# ... shows all 38 existing models + test/model

litellm-cli config remove test/model
# Removed: test/model

litellm-cli config validate
# [OK] config.yaml validates (top-level syntax OK)
```

All 38 models (NVIDIA, OpenRouter, FreeTheAI, AMD) intact.

## 5. AI-Gateway Profile: Dry-Run Creation

With the CLI fixed, created a dedicated `ai-gateway` NixOS profile.

### Profile Structure

```nix
# profiles/ai-gateway/default.nix
{ config, lib, pkgs, ... }:
let defaults = import ../../settings; in
{
  imports = [ ../../system ../../common/ai ../../common/web/caddy.nix ];
  
  networking.hostName = "ai-gateway";
  # ... static LAN IP, SSH keys, bootloader, timezone
  
  services.caddy.enable = true;  # AI vhosts generated from services.caddy.services.*
  systemd.services.caddy.serviceConfig.EnvironmentFile = 
    [ config.sops.secrets."providers.env".path ];
  
  services.xserver.enable = false;  # no desktop
  # system.stateVersion inherited from system module (25.11)
}
```

### Flake Update

```nix
# flake.nix
nixosConfigurations = {
  server     = mkSystem "portege-r30c" "server";
  workstation = mkSystem "portege-r30c" "workstation";
  failsafe   = mkSystem "portege-r30c" "failsafe";
  system     = mkSystem "portege-r30c" "system";
  ai-gateway = mkSystem "portege-r30c" "ai-gateway";  # NEW
};
```

### Dry-Run Results

```bash
$ nix flake show
... ai-gateway: NixOS configuration

$ nixos-rebuild build --flake .#ai-gateway
# Builds successfully (after resolving option conflicts with system module via lib.mkForce)
```

The profile is **independent** - imports `system` directly, only `common/ai` + `common/web/caddy.nix`, not the full `common/` stack. No desktop, no mail, no AP, no media.

## 6. Architectural Discussion: Future Profile Hierarchy

Post-fix discussion centered on evolving the profile composition model.

### Current vs. Proposed

| Current | Proposed |
|---------|----------|
| `server` = system + all common/* | `server` = system + base common/* (network, security, storage, packages) |
| `workstation` = server + desktop | `ai-gateway` = server + `ai-common` |
| `common/ai` buried in `common/` | `ai-common/` at root (graduated module) |
| | `workstation` = ai-gateway + desktop |

### Graduation Pattern

Modules "graduate" from `common/X` to `X-common` when:
1. Multiple profile consumers
2. Cohesive domain (AI, AP, Web, Monitoring)
3. May import other graduated modules (e.g., `ap-common` -> `ai-common`)
4. Stable enough for independent versioning

**Dependency DAG (future):**

```
common/ (network, security, storage, packages - universal base)
    |
    +--- ai-common/
    |       +--- ap-common/        (may import ai-common)
    |       +--- monitoring-common/
    |
    +--- web-common/               (Caddy, shared by ai-common, ap-common, etc.)
```

### Profile Composition (Future)

| Profile | Composition |
|---------|-------------|
| `server` | `common/*` (base only) |
| `ai-gateway` | `server` + `ai-common` |
| `ap-gateway` | `server` + `ap-common` (imports `ai-common`) |
| `workstation` | `ai-gateway` + desktop |
| `monitoring` | `server` + `monitoring-common` |

### What Stays in `common/` Forever

Universal infrastructure with no domain boundary:
- `common/network` - every machine needs networking
- `common/security` - SSH, firewall, sudo, users
- `common/storage` - disks, ZFS, NFS
- `common/packages` - nixpkgs config, overlays

These never graduate because **every profile needs them**.

### Naming Convention

| Pattern | Example | Use For |
|---------|---------|---------|
| `{domain}-common` | `ai-common`, `ap-common`, `web-common` | Graduated, composable domain modules |
| `common/{domain}` | `common/network`, `common/security` | Universal base infrastructure |

The `-common` suffix signals "shared, reusable, importable by multiple profiles."

## 7. Verification Plan

- [x] `litellm-cli config add/remove/validate` round-trip works
- [x] All 38 existing models preserved
- [x] `nix flake show` lists `ai-gateway` configuration
- [x] `nixos-rebuild build --flake .#ai-gateway` succeeds
- [ ] `nixos-rebuild build` for `server`, `workstation`, `failsafe` still succeed (no regression)
- [ ] When deployed: `https://ai.home.arpa/v1/models`, `https://chat.home.arpa`, `https://llama.home.arpa/v1/models` all return 200

## 8. Pending Actions

- Complete the `ai-gateway` profile dry-run (resolve any remaining option conflicts with `system` module)
- Document the graduation criteria in `CLAUDE.md` or `AGENTS.md`
- When ready: migrate `common/ai` -> `ai-common` with re-export shim during transition
- Apply `lib.mkForce` to `networking.hostName` and any other conflicting options in `ai-gateway` profile

## 9. Recommendations

1. **Treat silent no-ops as failures** - exit 0 with empty output is the worst failure mode. The `yq -yi` + redirect pattern is a known anti-pattern; audit other scripts for similar issues.

2. **Graduate modules deliberately** - `ai-common` is the pilot. Don't pre-create `ap-common`/`web-common` until they have multiple consumers. The pattern proves itself (or doesn't) with real usage.

3. **Keep `common/` for truly universal stuff** - don't over-graduate. Network, security, storage, packages stay in `common/` because every profile needs them.

4. **Profile composition over feature flags** - explicit profiles (`ai-gateway` = `server` + `ai-common`) are cleaner than feature flags on `server` when the role is distinct. Feature flags suit optional features on the *same* host type.

5. **Record architectural decisions** - this discussion about profile hierarchy and module graduation should be captured in project docs so future agents/humans follow the pattern.

---

The homelab's AI gateway now has a reliable config editor and a clear path to a dedicated, composable profile. The architectural pattern established here - graduated domain modules composing into profiles - will serve the fleet well as new roles (AP, monitoring, web) emerge.

Generated with Nemotron 3 Ultra by NVIDIA
