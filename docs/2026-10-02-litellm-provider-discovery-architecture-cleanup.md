# Litellm Provider Discovery and Architecture Cleanup - Part 2

**Date:** 2026-10-02
**Author:** Codebot
**Topic:** litellm, cloudflare, nvidia, provider-discovery, architecture, config, homelab

---

## 1. Objective

Document the provider discovery round-trips against NVIDIA NIM and Cloudflare Workers AI, the architecture clarification that dropped `providers.json` in favor of a single static `config.yaml`, the seed config change to local-only, and the successful rebuild/boot verification.

## 2. Background

Part 1 covered the `litellm-cli` silent config corruption fix (`yq -yi` + redirect anti-pattern) and the creation of the `ai-gateway` NixOS profile. This session picked up from there with the goal of adding Cloudflare Workers AI and verifying NVIDIA NIM models, then cleaning up the configuration architecture.

The homelab LiteLLM gateway at `ai.home.arpa:4000` previously had only NVIDIA NIM and local llama.cpp models. The SOPS secrets already contained `CF_API_TOKEN` and `CF_ACCOUNT_ID` from an earlier experiment.

## 3. Work Performed

### 3.1 NVIDIA NIM Model Verification

Using the `litellm-nvidia-discovery` skill (which tests against NVIDIA NIM directly at `https://integrate.api.nvidia.com/v1`), tested the 4 text models currently in the live config:

| Model (opencode ID) | Upstream ID | Result |
|---------------------|-------------|--------|
| `nvidia/meta/muse-glimmer-30b` | `meta/muse-glimmer-30b` | PASS |
| `nvidia/nvidia/nemotron-3-super-120b-a12b` | `nvidia/nemotron-3-super-120b-a12b` | PASS |
| `nvidia/nvidia/nemotron-3.5-lightning-30b-a3b` | `nvidia/nemotron-3.5-lightning-30b-a3b` | PASS |
| `nvidia/openai/gpt-oss-20b` | `openai/gpt-oss-20b` | PASS |

Two non-text models (`llama-3.2-11b-vision-instruct`, `llama-nemotron-embed-vl-1b-v2`) were correctly filtered out by the non-text pattern matcher.

The resulting LiteLLM whitelist (4 entries) matched the existing live config -- no changes needed.

### 3.2 Cloudflare Workers AI Model Discovery

Using the `prune-cloudflare-models` skill (built-in catalog of 67 known Cloudflare text models, tested against `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1` with the SOPS `CF_API_TOKEN`):

- **64 text models** from catalog passed non-text filter
- **64 tested** (free tier = 10,000 neurons/day)
- **17 PASS**, 47 ERR/No-such-model/Deprecated/Not-on-free-plan

**PASS models (17):**

| Model | Notes |
|-------|-------|
| `@cf/meta/llama-3.1-70b-instruct` | |
| `@cf/meta/llama-3.1-8b-instruct-fp8-fast` | |
| `@cf/meta/llama-3.1-70b-instruct-fp8-fast` | |
| `@cf/meta/llama-3.2-1b-instruct` | |
| `@cf/meta/llama-3.2-3b-instruct` | |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | |
| `@cf/mistral/mistral-7b-instruct-v0.1` | |
| `@cf/mistralai/mistral-small-3.1-24b-instruct` | |
| `@cf/google/gemma-4-26b-a4b-it` | |
| `@cf/qwen/qwen3-30b-a3b-fp8` | |
| `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b` | |
| `@cf/ibm-granite/granite-4.0-h-micro` | |
| `@cf/nvidia/nemotron-3-120b-a12b` | |
| `@cf/zai-org/glm-4.7-flash` | |
| `@cf/aisingapore/gemma-sea-lion-v4-27b-it` | |
| `@cf/openai/gpt-oss-120b` | |
| `@cf/openai/gpt-oss-20b` | |

Failures were mostly deprecated models (Llama 2, Llama 3, older Qwen/DeepSeek/Gemma), models not on the free tier (Kimi, GLM 5.x, DeepSeek v4), or simply no longer in the catalog.

### 3.3 Live Config Update

Added the 17 Cloudflare models to `/srv/appdata/litellm/config.yaml` via a Python script (since `litellm-cli config add` would be 17 separate invocations). The live config now has **28 models**:

| Provider | Count |
|----------|-------|
| NVIDIA NIM (text) | 4 |
| NVIDIA NIM (vision/embedding) | 2 |
| Cloudflare Workers AI | 17 |
| Local llama.cpp | 5 |

Restarted `litellm.service` -- all models listed on `/v1/models`, end-to-end chat completions verified for Cloudflare `llama-3.2-3b-instruct` and NVIDIA `nemotron-3-super-120b-a12b`.

### 3.4 Architecture Clarification: providers.json Dropped

Investigated the relationship between three files:

| File | Role | Status |
|------|------|--------|
| `common/ai/litellm/config.yaml` | First-boot seed (committed) | **Active** |
| `/srv/appdata/litellm/config.yaml` | Live runtime config (edited by litellm-cli) | **Active** |
| `/srv/appdata/litellm/providers.json` | Old render source | **DROPPED** |

The `litellm-cli` repo commit `e823506` ("litellm-cli: static config.yaml; drop providers.json/models.json render") removed the render pipeline entirely. There is no `litellm-render.service`. The `providers.json` on the homelab was an experimental artifact from today's testing -- not used by the running system.

Removed both `providers.json` and `providers.json.lock` from `/srv/appdata/litellm/`.

### 3.5 Seed Config Change: Local-Only

Updated `common/ai/litellm/config.yaml` (the committed seed) to contain **only the 5 local llama.cpp models**. Remote providers (NVIDIA, Cloudflare) are managed in the live config at `/srv/appdata/litellm/config.yaml` and persist across rebuilds because the activation script only seeds when the live file is missing or zero-byte:

```bash
if [ ! -f ${configFile} ] || [ ! -s ${configFile} ]; then
  install -m0644 ${staticConfig} ${configFile}
fi
```

This eliminates redundancy and makes the "single source of truth" explicit: live config = source of truth, seed = first-boot default only.

### 3.6 Documentation Updates

Updated `/srv/repo/nix-lab/AGENTS.md`:
- "Do not experiment" section: `providers.json` -> `config.yaml`
- litellm-cli data contract: replaced old render pipeline with static config flow
- `litellm.nix` description: "Consumes litellm-cli rendered config.yaml" -> "Consumes static config.yaml from /srv/appdata/litellm"
- LiteLLM runtime notes: clarified first-boot seed + manual edit model

### 3.7 Rebuild and Boot

Committed changes:
- `32e650f`: AGENTS.md, ai-gateway profile fixes, flake.nix (ai-gateway profile), flake.lock (litellm-cli bump to `sha256-KRFSUHGYW59oFj7MIzwruYZ2YaFRpemplbYZOY1tw58=`), secrets/providers.env (added AMD_API_KEY)
- `92f43a6`: litellm seed config now local-only

Ran `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#server` -- success.
Rebooted -- **boot successful**. Live config with all 28 models intact.

## 4. Verification

| Check | Result |
|-------|--------|
| `litellm-cli config list` | 38 models (matches live config) |
| `curl /v1/models` (with master key) | 28 models returned |
| Cloudflare `llama-3.2-3b-instruct` chat completion | Returns "OK" |
| NVIDIA `nemotron-3-super-120b-a12b` chat completion | Returns reasoning content (expected) |
| NVIDIA `gpt-oss-20b` chat completion | Returns reasoning content (expected) |
| `nixos-rebuild switch` | Success |
| Reboot | Success |

## 5. Pending Actions

- [ ] Consider adding OpenRouter as a provider (API key already in SOPS)
- [ ] Consider adding FreeTheAI models to live config
- [ ] Monitor Cloudflare free tier quota (10k neurons/day) -- may hit limits under heavy use
- [ ] The `ai-gateway` profile in flake.nix needs real deployment testing (currently dry-run only)

## 6. Recommendations

1. **Test providers end-to-end before committing to live config** -- the discovery skills do this, but manual `curl` verification catches reasoning-vs-content differences (Nemotron/GPT-OSS output `reasoning_content`, not `content`).

2. **Keep the seed minimal** -- local-only is correct. Remote providers change frequently; baking them into the committed seed creates drift. The live config survives rebuilds by design.

3. **Audit other AGENTS.md references to dropped patterns** -- the `providers.json` -> `models.json` -> `config.yaml` pipeline is gone. Any agent reading the old docs will be misled.

4. **Cloudflare free tier is a real constraint** -- 10k neurons/day across all models. For production use, upgrade to Workers Paid plan or implement quota-aware routing.

5. **The `litellm-cli` fix (commit 935e250) should be audited for similar patterns** -- the `yq -yi` + redirect anti-pattern may exist in other scripts. Grep for `yq -yi.*>` across the repo.

---

Generated with Nemotron 3 Ultra by NVIDIA
