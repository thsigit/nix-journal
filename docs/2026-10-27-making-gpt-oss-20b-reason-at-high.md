---
nav:
  series: "OpenCode Configuration Evolution"
  part: 7
  prev:
    title: "The Agent CLI Path: OpenClaw to Hermes Agent to OpenCode"
    slug: 2026-08-22-agent-cli-path-openclaw-hermes-agent-opencode
---

# The Low That Would Not Leave (or: Making gpt-oss-20b Reason at High)

**Date:** 2026-10-27  
**Author:** Codebot  
**Topic:** OpenCode, NVIDIA NIM, model variants, reasoning effort, configuration

---

## 1. Objective

Make the NVIDIA NIM `gpt-oss-20b` model use high reasoning effort in OpenCode. The model kept showing `low` in the picker no matter what the config said, so the real objective became narrower: find which layer actually owns that label, and give the model a clean high-effort entry that survives a restart.

## 2. Background

OpenCode's model catalog treats `gpt-oss-20b` as a reasoning model with variants. The catalog entry for the NVIDIA provider reported three:

| Variant | Meaning |
|---|---|
| `low` | Low reasoning effort |
| `medium` | Medium reasoning effort |
| `high` | High reasoning effort |

The provider block looked like this before the experiment:

```json
"nvidia": {
  "npm": "@ai-sdk/openai-compatible",
  "name": "NVIDIA NIM (direct)",
  "options": {
    "baseURL": "https://integrate.api.nvidia.com/v1"
  },
  "models": {
    "openai/gpt-oss-20b": {
      "name": "gpt-oss-20b",
      "options": {
        "reasoningEffort": "high"
      }
    }
  }
}
```

On paper, `reasoningEffort: "high"` should have been enough. In practice, the model picker still displayed `low`. Famous last words: "It is just a one-line config change."

## 3. Problem

The config and the UI disagreed about which layer wins:

- The model entry set `options.reasoningEffort` to `high`.
- The catalog also carried built-in variants named `low`, `medium`, and `high`.
- Variant settings are applied after model options, so the selected variant can override the model-level option.
- The `low` label in the picker was the active variant, not the `reasoningEffort` value.

That distinction mattered because every obvious edit was aimed at the wrong layer.

## 4. Work Performed

### 4.1 The first one-line fix

Added `reasoningEffort: "high"` to the model entry, validated the JSON, restarted OpenCode, and opened a new session. The picker still showed `low`.

### 4.2 The key that should not carry a variant

The next attempt changed the provider model key itself:

```json
"openai/gpt-oss-20b#high": {
  "name": "gpt-oss-20b",
  "options": {
    "reasoningEffort": "high"
  }
}
```

This was the wrong layer. The `#high` suffix belongs on a model *reference* such as `nvidia/openai/gpt-oss-20b#high`, not on the provider's model key. The key is the upstream model ID, and the whitelist still pointed at `openai/gpt-oss-20b`. Restart, new session, same `low`.

### 4.3 Disabling the other variants

The schema allows variants to be disabled, so the next attempt removed the competition:

```json
"openai/gpt-oss-20b": {
  "name": "gpt-oss-20b",
  "options": {
    "reasoningEffort": "high"
  },
  "variants": {
    "low": { "disabled": true },
    "medium": { "disabled": true }
  }
}
```

JSON validated. Restart, new session. Still `low`.

### 4.4 The removal experiment

To find out whether the model block controlled availability at all, the whole `openai/gpt-oss-20b` block was removed and OpenCode was restarted. The model disappeared from the picker. That was useful: the block does control whether the model exists, but it does not control which variant the picker selects.

The block was restored. The model came back. So did `low`.

### 4.5 The alias that worked

The final attempt gave the model a different identity while keeping the same upstream model:

```json
"gpt-oss-20b-high": {
  "id": "openai/gpt-oss-20b",
  "name": "gpt-oss-20b (high)",
  "options": {
    "reasoningEffort": "high"
  },
  "variants": {
    "low": { "disabled": true },
    "medium": { "disabled": true }
  }
}
```

The whitelist entry was updated from `openai/gpt-oss-20b` to `gpt-oss-20b-high`. The alias key has no slash, so the full selector became:

```text
nvidia/gpt-oss-20b-high
```

After a restart, the picker showed `gpt-oss-20b (high)`. Selecting it opened the variant/reasoning choice with `default`, `low`, `medium`, and `high`. Choosing `high` worked. The old `low` entry was still present and the owner planned to remove it separately.

| Attempt | Change | Result |
|---|---|---|
| 1 | `options.reasoningEffort: "high"` | still `low` |
| 2 | model key `openai/gpt-oss-20b#high` | still `low`; wrong layer |
| 3 | disabled `low` and `medium` variants | still `low` |
| 4 | removed the whole model block | model disappeared; block controls availability |
| 5 | custom alias with `id: "openai/gpt-oss-20b"` | alias appeared as `gpt-oss-20b (high)`; `high` selectable and working |

## 5. Diagnosis

The label in the picker was the active variant, not the `reasoningEffort` option. OpenCode's variant layer applies after the model-level `options`, so a built-in `low` variant can quietly override `options.reasoningEffort: "high"`.

The key change in attempt 2 failed for a second reason: `#high` is a selector suffix, not part of the provider model ID. Putting it in the key creates a model that does not match the whitelist entry and does not match the upstream model name.

The alias worked because it created a distinct model entry with its own identity:

- `gpt-oss-20b-high` is the local model key.
- `id: "openai/gpt-oss-20b"` points at the real upstream model.
- `name: "gpt-oss-20b (high)"` makes the intent obvious in the picker.
- `options.reasoningEffort: "high"` supplies the preferred effort.
- The variant picker still exists, so `high` must be selected explicitly when offered.

That last point is the honest limit of the fix: the alias does not remove the variant chooser. It gives the model a clean, clearly named entry and keeps the high-effort option available without the original catalog entry's default `low` label.

## 6. Preliminary Assessment

The alias is a practical workaround, not a magic default. It solves the identification problem and makes the high-effort choice explicit. The old `openai/gpt-oss-20b` entry should be removed to avoid two nearly identical models in the picker, one of which still advertises `low`.

The JSON was validated with `python3 -m json.tool` after each edit. A restart and a new session were required every time; the running session kept the stale config.

## 7. Solution Summary

- `options.reasoningEffort` alone does not beat a selected catalog variant.
- The `#variant` suffix belongs in a model reference, not in the provider model key.
- Disabling `low` and `medium` variants did not force `high` in this OpenCode version.
- A custom alias with a distinct key, `id` mapping to `openai/gpt-oss-20b`, and a clear name produced a usable `gpt-oss-20b (high)` entry.
- The variant chooser still appears; `high` is selected explicitly.
- The old `low` entry should be removed by the owner.

## 8. Verification Plan

- [x] `python3 -m json.tool ~/.config/opencode/opencode.json` reports valid JSON.
- [x] OpenCode restart and new session show `gpt-oss-20b (high)` in the picker.
- [x] The alias exposes `default`, `low`, `medium`, and `high`; selecting `high` works.
- [ ] Remove the old `openai/gpt-oss-20b` entry from the NVIDIA provider and whitelist.
- [ ] Restart once more and confirm only the high alias remains.

## 9. Pending Actions

- Remove the old `openai/gpt-oss-20b` model and whitelist entry so the picker does not show both the high alias and the low original.
- If any agent or command later references `gpt-oss-20b`, use `nvidia/gpt-oss-20b-high` rather than the old catalog ID.
- Re-check the model list after the cleanup restart.

## 10. Recommendations

- Do not put `#variant` in a provider model key. Put it in the model reference, for example `nvidia/openai/gpt-oss-20b#high`.
- When a catalog variant keeps overriding model options, create a custom alias with a distinct key and an `id` that points at the real upstream model.
- Use the model picker's variant selector deliberately; the label is part of the model state, not decoration.
- Validate JSON before restarting. A missing comma is a boring way to lose an afternoon.
- After changing a provider model, restart OpenCode and open a new session. The old session is a museum of the previous config.
- Keep the old entry until the new one is proven, then remove it in a separate step. That is exactly what the removal experiment did.

Generated with DeepSeek V4.1 Flash Free by OpenCode
