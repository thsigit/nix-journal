# "OpenCode Provider and Fallback Chain" - Part 3 (Final)

**Date:** 2026-09-01  
**Author:** Codebot  
**Topic:** opencode, providers, nvidia, litellm, kenari, openrouter, model-management

---

## 1. Objective (or: The Middleman Gets the Boot)

Two sessions ago we pruned OpenCode down to a healthy provider set, and last
session we retired BitRouter and pointed opencode at `litellm.home.arpa` as its
single custom gateway. Nobody complained, and yet.

This session the user looked at the running config and had one of those quiet
realizations: opencode was the only consumer of LiteLLM, and LiteLLM was
proxying a small set of curated models that we already had direct keys for. Why
pay the proxy tax for something we can hit directly? Decision: **drop the
middleman.** remove LiteLLM from opencode entirely, go direct to three
providers, and let LiteLLM keep serving only "the other apps."

## 2. Background

The fallback-chain history so far:

- Part 1 (2026-08-09): fixed the LiteLLM master key, removed 15 dead
  providers, moved direct-access providers into opencode.json.
- Part 2 (2026-08-30): audited and pruned the NVIDIA whitelist, discovered
  LiteLLM's database-less mode limitation.
- Earlier today (2026-09-01): retired BitRouter, made LiteLLM the single
  gateway, folded the nvidia whitelist + blacklist into `providers.json`.

The opencode config this session started with a single `litellm` provider
pointing at `litellm.home.arpa/v1` and routing `openrouter/...:free` +
`nvidia/...` models through it.

## 3. Problem

Three friction points pushed this change:

1. **The middleman tax**: opencode -> LiteLLM -> upstream added a hop, a
   serialization normalization, and a point of failure for no benefit when
   opencode is the sole consumer.
2. **opencode.json is the source of truth** - and it was the thing the user
   actually wanted to maintain. Keeping the model registry in two places
   (opencode.json + providers.json) was double bookkeeping.
3. **A wrong-free-tier-id bug**: the config used `openrouter:free` (colon),
   which OpenRouter rejects. litellm happened to tolerate it; direct access
   would not. Getting this right mattered once the proxy was out of the path.

## 4. Work Performed

### 4.1 The Reversal: litellm Out, Three Direct Providers In

`opencode.json` rewritten. `provider.litellm` removed. In its place:

| Provider  | Base URL                       | Whitelisted models                    |
| --------- | ------------------------------ | ------------------------------------- |
| nvidia    | https://integrate.api.nvidia.com/v1 | 5 (see 4.2)                      |
| openrouter| https://openrouter.ai/api/v1   | `openrouter/free` (only)              |
| kenari    | https://kenari.id/v1           | `kenari-free` (only)                  |

The user was explicit and firm: **no per-model free-tier expansion.** For
openrouter, exactly `openrouter/free`. For kenari, exactly `kenari-free`.
Everything else the gateway providers advertise is rejected.

### 4.2 NVIDIA Whitelist: Keep Only the Fast Five

We round-trip tested every curated NVIDIA candidate directly against
`integrate.api.nvidia.com/v1`. The keepers:

| Model                                        | Latency | Role              |
| -------------------------------------------- | ------- | ----------------- |
| `openai/gpt-oss-120b`                        | 0.68s   | default/code/build|
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | 1.1s  | reasoned work     |
| `nvidia/nemotron-3-super-120b-a12b`          | 0.7s    | plan/homelab      |
| `nvidia/nemotron-3.5-content-safety`         | 0.7s    | low-overhead      |
| `minimaxai/minimax-m3`                       | 0.66s   | coding (429-prone)|

Rejected with evidence (000 timeouts unless noted):

| Model                                        | Reason                          |
| -------------------------------------------- | ------------------------------- |
| `google/gemma-4-31b-it`                      | 000 timeout                     |
| `nvidia/nemotron-3-ultra-550b-a55b`          | 000 timeout                     |
| `mistralai/mistral-nemotron`                 | 000 timeout / content-tool_calls error |
| `moonshotai/kimi-k3`                         | 000 timeout                     |
| `nvidia/nemotron-3-nano-30b-a3b` (bare)      | not in catalog                  |
| `nvidia/openai/gpt-oss-20b`                  | 31s - too slow                  |
| `nvidia/nemotron-3.5-lightning-30b-a3b`      | 20.9s - too slow                |
| `meta/llama-3.3-70b-instruct`                | 410 Gone (EOL 2026-08-26)       |
| `step-3.7-flash`, `laguna-*`, others         | overloaded / bad on NixOS       |

### 4.3 The `openrouter/free` vs `openrouter:free` Discovery

Submitted a test to the vision agent and got back:

```
openrouter:free is not a valid model ID
```

Direct API archaeology settled it:

| Model id               | Direct result                                   |
| ---------------------- | ----------------------------------------------- |
| `openrouter:free`      | invalid - rejected by OpenRouter               |
| `openrouter/auto`      | 402 - needs credits                            |
| `openrouter/auto:free` | 429 - rate-limited upstream                    |
| `openrouter/free`      | **200 - valid free auto-route**                |

litellm had been resolving `openrouter:free` as its own id
`openrouter/openrouter/free` and forwarding model id `openrouter/free` to
OpenRouter - which is why it only broke once the proxy left. The fix was to use
the slash form everywhere: `openrouter/free` in the registry,
`openrouter/openrouter/free` in agent references.

### 4.4 Agent Fleet Pruned to Minimum

Reviewed the original nine agents. Kept only what earns its slot:

| Agent              | Model                                      | Notes                 |
| ------------------ | ------------------------------------------ | --------------------- |
| code               | `nvidia/openai/gpt-oss-120b`               |                       |
| homelab-management | `nvidia/nvidia/nemotron-3-super-120b-a12b` |                       |
| build              | `nvidia/openai/gpt-oss-120b`               | built-in              |
| plan               | `nvidia/nvidia/nemotron-3-super-120b-a12b` | built-in, default     |
| writer             | `openrouter/openrouter/free`               | blog writer, model TBD|

Pruned: `review`, `fast`, `cheap` (redundant), and `vision` (see 4.5).

### 4.5 Vision: A Fitting End

We tested `meta/llama-3.2-11b-vision-instruct` (direct NVIDIA, 3.7s, described
a wheat-field image correctly) and whitelisted it. But the OpenCode workflow
itself can't pass images to the model reliably:

```
ERROR: Cannot read "IMG_20151217_0001.jpg" (this model does not support image input)
```

Not a model problem - an opencode-image-input mismatch. The vision agent and
its model were removed from the config; the nvidia whitelist is back to the
fast five.

### 4.6 The model-management Skill

Created `~/.config/opencode/skills/model-management/SKILL.md`: the single
source of truth for the accepted/rejected model registry. Applies ONLY to
opencode.json, never to other gateways. Records:

- Accepted: the 5 nvidia models, `openrouter/free`, `kenari-free`.
- Rejected: every other openrouter/kenari `:free`, plus the nvidia troublemakers
  with the verification table above.
- The slash-vs-colon rule (`openrouter/free`, never `openrouter:free`).
- The prefix rule (hosted ids unprefixed, nvidia-branded double-prefixed).
- A test-before-add procedure for any new nvidia model.

## 5. Diagnosis

LiteLLM worked fine as a gateway - it was just excess architecture for a
single consumer. Direct access surfaced two latent bugs the proxy had been
hiding: the invalid `openrouter:free` id and the rate-limit/credit behavior of
the other OpenRouter id forms. Direct access also made the latency differences
between "fast five" and "slow four" NVIDIA models impossible to ignore.

## 6. Solution Summary

- Removed `provider.litellm` from opencode.json entirely.
- Added `nvidia` (direct, 5 fast models), `openrouter` (only
  `openrouter/free`), `kenari` (only `kenari-free`).
- Pruned agents to: code, homelab-management, build, plan, writer.
- Created the model-management skill as the canonical accepted/rejected
  registry.
- LiteLLM stays up for "other apps"; it no longer fronts opencode.
- Credentials: nvidia + openrouter + kenari direct keys in auth.json; litellm
  credential removed.

## 7. Verification Plan

- [x] `openrouter/free` direct round-trip (HTTP 200)
- [x] `kenari-free` reachable via `https://kenari.id/v1` (66 models listed)
- [x] All 5 nvidia whitelist models round-trip direct
- [x] JSON validation of rewritten opencode.json
- [x] opencode restarts cleanly with the new providers
- [x] vision agent tested and removed (open code workflow limitation)

## 8. Pending Actions

- Test the `code` and `homelab-management` agents in a live opencode session
  with the new direct models.
- Decide the final model for the `writer` agent (user said "we will change the
  model later").
- Watch `minimaxai/minimax-m3` - free-tier 429-prone, may need replacement.

## 9. Recommendations

- Keep the "fast five" nvidia whitelist; add models only after a direct
  round-trip test passes.
- Remember the id forms: openrouter is `openrouter/free` (slash). Never the
  colon form.
- Use the model-management skill whenever someone asks to add/remove a model
  to opencode.json - it is the registry of record.
- If a vision workflow is ever needed again, revisit the opencode image-input
  path before blaming the model.

## Relevant Files

- `/mnt/c/users/sigit/.config/opencode/opencode.json` - 3 direct providers, 5 agents
- `/mnt/c/users/sigit/.config/opencode/skills/model-management/SKILL.md` - canonical model registry
- `/home/sigit/.local/share/opencode/auth.json` - nvidia, openrouter, kenari keys
- `/mnt/c/users/sigit/.config/opencode-backups/opencode-pre-litellm-removal-20260901-*.json` - pre-change backup

---

Generated by GPT-OSS 120B (NVIDIA)