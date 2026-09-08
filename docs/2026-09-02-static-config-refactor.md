# Static Config Refactor: LiteLLM Gateway Now Uses Committed config.yaml

**Date:** 2026-09-02  
**Author:** Codebot  
**Topic:** litellm, nix, config, gateway, cli, providers

---

## 1. Objective (or: The One Config to Rule Them All)

We set out to eliminate the build-coupled render pipeline that made changing provider handling require a `nixos-rebuild`. The goal was to adopt a **static, hand-maintained `config.yaml`** as the single source of truth, committed in the consuming repo (nix-lab), and copied into place at activation. This would allow the `litellm-cli` to become a purely manual config editor—never invoked at rebuild or activation—while preserving all gateway functionality.

The concrete roadmap had four items:
1. Replace the dynamic render pipeline with a static committed `config.yaml`
2. Update the nix-lab `litellm.nix` to copy the committed config at activation
3. Repurpose `litellm-cli` as a manual config editor (add/remove/validate)
4. Remove all dynamic inputs: `providers.json`, `models.json`, fetch/render logic, and capability filters

## 2. Background

### 2.1 Where We Left Off

The previous report (`2026-09-01-retiring-bitrouter-single-gateway.md`) established LiteLLM as the homelab's single gateway, serving a curated 32-model set via a render pipeline that joined `providers.json` (admin-edited) and `models.json` (fetched inventory) into `/var/lib/litellm/config.yaml`. This pipeline lived in the `litellm-cli` flake, meaning any change to how models render (e.g., adding a whitelist) required a `nixos-rebuild`.

We identified the config-ergonomics friction as a follow-up: *"The real annoyance is that changing *provider handling* needs a rebuild."* This session was exactly that follow-up.

### 2.2 How the Litellm Setup Actually Works (Pre-Refactor)

The effective model list was produced by:
```
providers.json (admin)          -> defines providers, keys, whitelist/blacklist
/run/litellm-cli/models.json    -> auto-discovered model catalog (fetched from providers)
      |
      v
lib/render.sh (jq)              -> joins the two into model_list entries
      |
      v
/var/lib/litellm/config.yaml    -> what the litellm daemon actually reads
      |
      v
systemctl restart litellm       -> daemon picks up the new config
```

The catch: `render.sh` lives inside the nix-flake `litellm-cli` input, so changing *provider handling* needed a rebuild.

## 3. Problem

The render pipeline created a frustrating decoupling: the admin could edit `providers.json` freely (survives reinstalls), but changing how those edits translated to gateway behavior required a rebuild. This violated the principle that configuration should be data, not code that needs recompilation.

We wanted to:
- Make the config file itself the source of truth (committed and hand-maintained)
- Keep `litellm-cli` as a manual tool for editing that file (no automatic rendering)
- Preserve all gateway functionality: model listing, chat completions, usage logging, health checks

## 4. Work Performed

### 4.1 Nix-Lab: Static Config Architecture

**`common/ai/litellm/litellm.nix`** - Rewired to use static config:
- Removed the `litellm-render` systemd service entirely
- Kept `ExecStart = litellm --config /var/lib/litellm/config.yaml` + `PYTHONPATH` + `LITELLM_USAGE_CALLBACK`
- Added activation script `system.activationScripts.litellm-static-config` that:
  - Copies committed `./config.yaml` -> `/var/lib/litellm/config.yaml`
  - Installs `usage_logger.py` -> `/srv/appdata/litellm/`
  - Sets correct ownership/permissions

**`common/ai/litellm/litellm-cli.nix`** - Updated wiring:
- Removed redundant `litellm-healthjson-prep` and `litellm-cli-config.deps` overrides
- Clarified comments: config.yaml is static and hand-maintained in consuming repo
- Persistence contract: `dataDir` -> `usage_logger.py` (survives reinstall), `/run/litellm-cli` -> `health.json` (ephemeral)

### 4.2 Litellm-CLI: Manual Config Editor

**`default.nix`** - Pure package, no NixOS knowledge:
- Dropped `git` dependency (no fetch anymore)
- Removed `models.json`/`producers-seed.json` installs (no longer used)
- Removed `scripts/*` install (empty dir)
- Kept `data/usage_logger.py` install
- Exposes `bin/litellm-cli` and `lib/*.sh` with standard substitutions

**Module.nix** - Independent NixOS module:
- Owns only the CLI wrapper and runtime state (`health.json` on tmpfs)
- Does **not** run LiteLLM or render any config
- Exposes `services.litellm-cli.configFile` (default `/var/lib/litellm/config.yaml`)
- `litellm-cli` is a purely MANUAL tool: edits `config.yaml` directly, never invoked by any systemd unit

**CLI Scripts** - All rewritten to read/edit static config.yaml:
- `bin/litellm-cli`: Added `config` subcommand, dropped `providers`/`fetch`
- `lib/config.sh`: New manual editor (`list`, `add`, `remove`, `validate`)
- `lib/models.sh`: Lists models from config.yaml only (no capability filters)
- `lib/run.sh`: Default model + alias resolution from config.yaml
- `lib/doctor.sh`: Derives providers from config.yaml (unique provider/api_base/key_env)
- `lib/status.sh`: Shows routing table (aliases/fallbacks) from config.yaml
- `lib/debug.sh`: Now `doctor` | `status` | `config` (no `render`/`fetch`)
- Removed obsolete: `lib/render.sh`, `lib/providers.sh`, `lib/fetch.sh`, `scripts/fetch-models.sh`

### 4.3 Data Cleanup
- `git rm` data/models.json, data/models-dev.json, data/providers-seed.json (tracked files)
- Removed stale backup files: `default.nix.backup`, `default.nix.broken`

## 5. Diagnosis

The render pipeline was the fundamental friction point: it coupled config *generation* (which should be data) to the nix build (which should be infrastructure). By making the config file itself static and committed, we inverted the relationship:
- **Before**: Admin edits -> render pipeline (build-coupled) -> config.yaml -> gateway
- **After**: Admin edits -> committed config.yaml -> gateway (via activation copy)

This follows the **"Configuration Is Data"** principle: config.yaml now describes things like enabled models, aliases, fallbacks, and router settings—just as it should.

## 6. Preliminary Assessment

- **Static config active**: `/var/lib/litellm/config.yaml` is the committed copy (32 models)
- **Service running**: `litellm.service` active since activation, using the static config
- **Usage logger working**: `/srv/appdata/litellm/usage_logger.py` installed, `usage.jsonl` growing
- **Gateway responsive**: `/v1/models` returns exactly the 32 configured models
- **CLI functional**: `litellm-cli models` reads from config.yaml, `litellm-cli run` works
- **litellm-cli enhancements pending**: The new `config` subcommand and manual editor require a lock update and rebuild to activate (flake.lock needed updating to pick up e823506)

## 7. Solution Summary

We replaced the dynamic render pipeline with a static, hand-maintained `config.yaml` committed in nix-lab (`common/ai/litellm/config.yaml`). The nix-lab module now copies this file to `/var/lib/litellm/config.yaml` at activation and installs the usage logger. The `litellm-cli` becomes a purely manual tool for editing that file—never invoked during rebuild or activation.

Key changes across two commits:
- **nix-lab 6d90cbe**: litellm.nix (static config + activation copy), litellm-cli.nix (updated wiring)
- **litellm-cli e823506**: CLI as manual editor (config subcommand, lib/config.sh), removed render/providers/fetch logic, updated README, cleaned data files

All changes are committed and ready. The nix-lab changes are active post-rebuild; the litellm-cli enhancements await a lock update and rebuild.

## 8. Verification Plan

- [x] Static config in place: `/var/lib/litellm/config.yaml` matches committed copy (32 models)
- [x] Service active: `litellm.service` active since activation, using the static config
- [x] Usage logger installed: `/srv/appdata/litellm/usage_logger.py` present
- [x] Usage logging working: `/srv/appdata/litellm/usage.jsonl` growing with requests
- [x] Gateway responsive: `/v1/models` returns 32 models (4 freetheai + 11 nvidia + 17 openrouter)
- [x] CLI functional: `litellm-cli models` lists models from config.yaml, `litellm-cli run` works
- [ ] litellm-cli enhancements: `config` subcommand requires lock update and rebuild (pending)

## 9. Pending Actions

1. **Update flake.lock in nix-lab**: `nix flake lock --update-input litellm-cli` (to pick up e823506)
2. **Run nixos-rebuild**: `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` (to activate litellm-cli enhancements)
3. **Post-rebuild verify**: 
   - `litellm-cli config list` works
   - `litellm-cli config add`/`remove` edit the committed config.yaml
   - `litellm-cli config validate` validates against cached sample
   - `litellm-cli` is never invoked during rebuild/activation (confirm via service logs)

## 10. Recommendations

1. **Static config is the way forward**: Keep the config.yaml as the single source of truth—committed, hand-maintained, and copied at activation.
2. **Update the lock and rebuild**: The litellm-cli enhancements (manual config editor) are ready and waiting for a lock update and rebuild to activate.
3. **Preserve the no-rebuild-at-runtime principle**: The gateway should never depend on litellm-cli existing at runtime—it only needs the static config file.
4. **Consider future ergonomics**: If changing *how* the gateway works (e.g., routing strategy) still feels build-coupled, explore moving those settings into the static config.yaml as well.
5. **Remember the decoupling win**: Admin edits to config.yaml are now immediately available for activation—no build step needed to change what models are served.

## 11. Relevant Files

- `/srv/repo/nix-lab/common/ai/litellm/config.yaml` - committed static config (32 models)
- `/srv/repo/nix-lab/common/ai/litellm/litellm.nix` - static config + activation copy
- `/srv/repo/nix-lab/common/ai/litellm/litellm-cli.nix` - updated wiring (no redundant deps)
- `/srv/repo/litellm-cli/bin/litellm-cli` - added config subcommand, dropped providers/fetch
- `/srv/repo/litellm-cli/lib/config.sh` - new manual editor (list/add/remove/validate)
- `/srv/repo/litellm-cli/default.nix` - pure package (dropped git, data installs, passthru)
- `/srv/repo/litellm-cli/README.md` - updated to static-config architecture
- `/srv/appdata/litellm/usage_logger.py` - usage callback (installed at activation)
- `/var/lib/litellm/config.yaml` - runtime copy (matches committed config)
- `/srv/appdata/litellm/usage.jsonl` - usage log (growing with requests)

---

Generated by Nemotron 3 Super (NVIDIA)
