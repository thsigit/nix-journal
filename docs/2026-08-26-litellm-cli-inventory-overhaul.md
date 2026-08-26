# LiteLLM CLI Inventory Overhaul

*How I learned to stop worrying and love the :free tag (also: config.yaml is the source of truth, not models.json)*

**Date:** 2026-08-26  
**Author:** Codebot  
**Topic:** litellm, homelab, nixos, openrouter, cli

---

## 1. The Grand Plan (or: What Are We Even Doing Here?)

User uses only `:free` models from OpenRouter. Some models stopped working (`openrouter/google/gemini-3.5-flash-lite:free` invalid, `openrouter/google/gemini-2.5-flash` no credits). The litellm-cli had three problems: openrouter models showed all variants instead of just free ones, `litellm-cli models` listed what was in `models.json` (raw inventory) instead of what was actually served in `config.yaml`, and capability filters (`--text-only`, `--vision`) had no modalities data to filter on.

Famous last words: "just filter to `:free`, how hard can it be?"

## 2. Background

Three-layer config architecture:
- **Nix layer** (`litellm.nix`): declares service, sets env vars
- **CLI layer** (`litellm-cli`): renders config.yaml from providers.json + models.json + settings
- **Runtime layer** (`/run/litellm-cli/models.json`): ephemeral inventory, rebuilt at boot

`litellm-cli models` read from `models.json` which contained the raw inventory from provider APIs - all variants, all tiers. The rendered `config.yaml` was the actual source of truth for what litellm serves, but the CLI ignored it.

## 3. Problem

| Issue | Root Cause |
|---|---|
| Non-free openrouter models shown | No `:free` filter in render.sh |
| `litellm-cli models` shows wrong models | Reads `models.json` not `config.yaml` |
| `--text-only` / `--vision` filters return 0 | No modalities data in `models.json` |
| `openrouter/openrouter/free` not routable | Missing manual model entry in providers.json |
| Routing aliases broken | `cloud-chat` etc. pointed to dead model IDs |

## 4. Work Performed

### 4.1 OpenRouter Free Filter in render.sh

Added jq filter in `lib/render.sh` that runs after model deduplication:

```bash
if $provider == "openrouter" then
  map(select((.id | endswith(":free")) or (.id == "openrouter/free")))
  | unique_by(.id)
else . end
```

This filters openrouter models to only `:free` variants and the `openrouter/free` auto-routing model. All other providers pass through unchanged.

### 4.2 models.sh Reads config.yaml (When No Capability Filters)

Rewrote `lib/models.sh` to read from `config.yaml` by default - because that's what litellm actually serves. Falls back to `models.json` only when capability filters are active (since `config.yaml` doesn't have modalities data).

```bash
if [ "$HAS_FILTER" -eq 1 ]; then
  INVENTORY=$(cat "$MODELS_JSON")   # has modalities
else
  INVENTORY=$("$YQ" -o=json '.' "$CONFIG_YAML")  # what's served
fi
```

### 4.3 Modalities Enrichment from models-dev.json

Added `data/models-dev.json` to the litellm-cli repo (523 model modality entries). Updated `scripts/fetch-models.sh` to enrich inventory after fetching from provider APIs:

```bash
jq --slurpfile dev "$MODELS_DEV" '
  . as $inv | ($dev[0] | to_entries | map(
    .key as $dk | .value.models // [] | map({
      key: ($dk + "/" + .id),
      value: .modalities
    })
  ) | flatten | from_entries) as $modality_map |
  ...
'
```

Key debugging: `add` produces an array from nested arrays; `from_entries` correctly builds the lookup object.

### 4.4 Runtime Sync

Added sync step to `fetch-models.sh` so enriched inventory pushes to runtime `/run/litellm-cli/models.json` immediately (not just at next boot).

### 4.5 Routing Aliases Fixed

In `providers.json`, fixed routing aliases (`cloud-chat`, `deep-reasoning`, `coding-agent`) to point to `openrouter/openrouter/free` instead of dead model IDs. Added `openrouter/free` as manual model entry.

### 4.6 Commits and Deploy

8 commits pushed to `litellm-cli` repo:
`1680dd0` `511d2a0` `7644f96` `21893f5` `3e7e268` `fe58e95` `a1c9875` `abab16a`

Flake lock updated after each litellm-cli change.

## 5. Diagnosis (or: Things That Went Wrong)

1. **`add` vs `from_entries`**: jq's `add` on an array of `{key, value}` objects merges them into a single object with just two fields. `from_entries` correctly converts the array to a dictionary. (The jq documentation is a choose-your-own-adventure where every path leads to confusion.)

2. **nix store is immutable**: Trying to patch `fetch-models.sh` in the nix store after rebuild fails silently. Changes must go through the git commit -> flake lock -> rebuild pipeline.

3. **Committed inventory vs runtime state**: `litellm-cli fetch` writes to `data/models.json` (committed), but the runtime reads from `/run/litellm-cli/models.json` (rebuilt at boot). Without explicit sync, enrichments are lost until next reboot.

## 6. Verification

```bash
litellm-cli models --text-only nvidia     # Shows 10 text-only models
litellm-cli models --vision nvidia        # Shows 14 vision models
litellm-cli models --embeddings nvidia    # Shows 7 embedding models
litellm-cli models nvidia                 # Shows all 34 nvidia models (from config.yaml)
```

All filters working. OpenRouter shows only `:free` variants. Routing aliases resolve correctly.

## 7. Recommendations

- **config.yaml is the truth**: Always read from the rendered config for "what's served" queries. `models.json` is raw inventory, not truth.
- **`from_entries` not `add`**: When building jq lookup tables from arrays of key-value objects, use `from_entries`. Always.
- **Runtime sync matters**: Enrichments applied only to committed inventory are lost at reboot. Push to runtime state immediately.
- **Test filters with real data**: Modalities enrichment only works if `models-dev.json` is in the repo and `fetch` has been run. Empty modality map = empty filter results.

Generated by Big Pickle (OpenCode)
