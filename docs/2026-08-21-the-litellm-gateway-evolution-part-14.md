# The LiteLLM Gateway Evolution - Part 14

*Provider-native discovery + providers.json*

**Date:** 2026-08-21  
**Author:** Codebot  
**Topic:** LiteLLM, refactor, cli, llm, homelab, NixOS

---

## 1. Objective

Replace the models.dev dependency in litellm-cli with direct provider API queries, rename `gateway.json` to `providers.json` for clarity, and move the effective config path from `/run/litellm-cli/config.yaml` to `/var/lib/litellm/config.yaml` to align with the native module's stateDir.

## 2. Background

The litellm-cli config pipeline had three problems:

1. **models.dev dependency** - The `fetch-models.sh` script queried `https://models.dev/api.json` for free model listings. This external API was unreliable, returned incomplete data, and did not match what providers actually served.

2. **Naming confusion** - The source-of-truth config was called `gateway.json`, but it primarily defined providers and their configurations. The name did not match the content.

3. **Config path mismatch** - The rendered config lived at `/run/litellm-cli/config.yaml` (tmpfs), while the native `services.litellm` module uses `/var/lib/litellm` as its stateDir. The paths should align.

## 3. Architecture

The three-layer config architecture was established in the previous session:

```text
Nix (eval time)          CLI (runtime)           Merge (startup)
──────────────           ──────────────          ────────────────
services.litellm.settings   providers.json        litellm-cli render
  ↓                          ↓                       ↓
/nix/store/config.yaml    data/models.json  →   /var/lib/litellm/config.yaml
(static defaults)         (discovered)          (effective config)
```

**Ownership:**
- Nix owns: service definition, general_settings, litellm_settings, router_settings
- CLI owns: model_list, model_alias, fallbacks
- SOPS owns: providers.env (API keys)

This session focused on three refinements: replacing models.dev with provider APIs, renaming for clarity, and aligning paths.

## 4. Work Performed

### 4.1 Rewrote fetch-models.sh for provider API discovery

The old script queried models.dev:

```bash
curl -sfL 'https://models.dev/api.json' | jq '...'
```

The new script queries each enabled provider's `/v1/models` endpoint directly:

```bash
# For each provider in providers.json:
curl -sfL -H "Authorization: Bearer $API_KEY" "$BASE_URL/models"
```

Pipeline:
1. Read `providers.json` for enabled providers
2. Load API keys from `providers.env` (SOPS-decrypted)
3. Query each provider's `/v1/models` endpoint
4. Normalize responses (handles both `.data` and `.models` shapes)
5. Write to `data/models.json`
6. Git commit

Results: 520 models discovered across providers (NVIDIA: 103, OpenRouter: 417, Ollama: 0, freetheai: 0).

### 4.2 Renamed gateway.json to providers.json

| Old | New |
|-----|-----|
| `data/gateway-seed.json` | `data/providers-seed.json` |
| `/srv/appdata/litellm/gateway.json` | `/srv/appdata/litellm/providers.json` |
| `LITELLM_GATEWAY_JSON` env var | `LITELLM_PROVIDERS_JSON` |
| `GATEWAY_JSON` script var | `PROVIDERS_JSON` |
| `gatewayFile` nix var | `providersFile` |
| `gatewaySeed` nix var | `providersSeed` |

Files updated: `module.nix`, `default.nix`, all `lib/*.sh` scripts, `scripts/fetch-models.sh`, `litellm-cli.nix`, `litellm.nix`.

### 4.3 Moved config path to stateDir

| Before | After |
|--------|-------|
| `/run/litellm-cli/config.yaml` (tmpfs) | `/var/lib/litellm/config.yaml` (persistent) |

The `configFile` default in `module.nix` was changed from `${runtimeDir}/config.yaml` to `/var/lib/litellm/config.yaml`. This aligns with the native `services.litellm.stateDir` and ensures the config persists across reboots.

### 4.4 Updated litellm.nix to use native services.litellm

The previous session's `litellm.nix` defined a custom `systemd.services.litellm`. The rework switched to the native `services.litellm` module:

```nix
services.litellm = {
  enable = true;
  port = 4000;
  host = "127.0.0.1";
  stateDir = "/var/lib/litellm";
  environmentFile = config.sops.secrets."providers.env".path;
  settings = {
    general_settings.master_key = "os.environ/LITELLM_MASTER_KEY";
    litellm_settings = { json_logs = true; drop_params = true; };
    router_settings = { routing_strategy = "usage-based-routing"; };
    model_list = [];
  };
};
```

The `model_list = []` in Nix is intentional: the CLI owns model_list at runtime.

ExecStart is overridden to use the CLI-rendered config:

```nix
systemd.services.litellm.serviceConfig.ExecStart = lib.mkForce
  "${pkgs.litellm}/bin/litellm --host 127.0.0.1 --port 4000 --config /var/lib/litellm/config.yaml";
```

A `litellm-render.service` runs before LiteLLM to generate the effective config.

### 4.5 Fixed package reference

The initial litellm.nix used `pkgs.litellm-cli` which does not exist in nixpkgs. Fixed to `config.services.litellm-cli.package` which references the package built by the module.

## 5. Issues Encountered

### 5.1 jq multi-line output in fetch-models.sh

The initial fetch script used `jq -r` which outputs multi-line JSON. When piped to `while IFS= read -r line`, each line was a JSON fragment, not a complete object. Fixed by using `jq -c` (compact output) to produce one JSON object per line.

### 5.2 sed over-replacement in module.nix

A bulk `sed` replacement of `gateway.json` to `providers.json` accidentally replaced the `package` option's `defaultText` value, turning `lib.literalExpression "pkgs.callPackage ./default.nix { }"` into `lib.literalExpression '/var/lib/litellm/config.yaml'`. Fixed by manually restoring the correct value.

### 5.3 Stale flake lock

The `litellm-cli` flake input in `flake.lock` pointed to an older revision. After modifying files in `/srv/repo/litellm-cli`, the lock needed updating with `nix flake lock --update-input litellm-cli` before `nixos-rebuild switch` would pick up the changes.

## 6. Data Flow

```text
providers.env (SOPS)  ───→  litellm-cli fetch  ───→  data/models.json
                                                     (520 models)
                                                          │
providers.json        ───→  litellm-cli render  ───→  /var/lib/litellm/config.yaml
(data/models.json)                                       (499 models after blacklist)
                                                          │
                                                    litellm --config
                                                          │
                                                    499 models served
```

## 7. Verification

```text
$ curl http://127.0.0.1:4000/health/liveliness
"I'm alive!"

$ litellm-cli providers list
  ✓ enabled   nvidia
  ✓ enabled   openrouter
  ✓ enabled   ollama
  ✓ enabled   freetheai

$ litellm-cli fetch
  fetch-models: committed updated inventory (520 models)

$ litellm-cli debug render
  litellm-cli render: wrote /var/lib/litellm/config.yaml with 499 models, 4 aliases, 1 fallbacks

$ curl -H "Authorization: Bearer $LITELLM_MASTER_KEY" http://127.0.0.1:4000/v1/models | jq '.data | length'
  499
```

## 8. Runtime State

```text
/srv/appdata/litellm/          # Persistent (dataDir)
├── providers.json             # Admin-owned source of truth
└── database.env               # Unused (no-DB mode)

/var/lib/litellm/              # Runtime (stateDir)
├── config.yaml                # Effective config (CLI-rendered)
└── tiktoken-cache/            # LiteLLM cache

/run/litellm-cli/              # Ephemeral (tmpfs)
├── models.json                # Inventory copy (from activation)
└── health.json                # Provider health status
```

## 9. Recommendations

- The `nixos-rebuild switch` is only needed when changing service architecture (port, security, settings). Model discovery runs via `litellm-cli fetch` + render without a rebuild.
- Monitor provider API availability: NVIDIA and OpenRouter are stable; Ollama returns 0 models when not installed; freetheai was unresponsive during testing.
- Consider adding a systemd timer for `litellm-cli fetch` to keep the model inventory fresh without manual intervention.
