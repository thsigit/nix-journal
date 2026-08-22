# The LiteLLM Gateway Evolution - Part 2

*4-way provider split refactor*

**Date:** 2026-07-20  
**Author:** Codebot  
**Topic:** LiteLLM, NixOS, homelab, architecture, OpenCode, controller-pattern  

## 1. Objective

Refactor LiteLLM gateway from four-way provider split to clean inventory/policy architecture with pure-join renderer.

## 2. Background

By 2026-07-17, gateway split into controller (pkgs/litellm-controller/, mkGateway entry point) and thin NixOS module (modules/ai/litellm/). Pipeline: models-dev.json -> litellm-render -> config.yaml -> LiteLLM service. Provider model had four independent lists with no shared truth source.

## 3. Problem

Four independent provider lists answering different questions:
- providers-open.nix: active backends (auto from models-dev.json)
- providers-restricted.nix: blocklist (no credits, paid-only, free-requiring-topup)
- providers-manual.nix: hand-added (Gemini, Ollama)
- lib/health.nix: separate registry with env vars and health endpoints

Adding provider required editing four files. Renderer had fallback tables and classification logic baked in. Health check carried own provider rules. Structural problem deferred from 2026-07-17 review.

## 4. Work Performed

### 4.1 Redesign (2026-07-18)
Separated questions into three files:
- models.json: "What models exist?" Canonical inventory (discovered from models.dev + declared in declared-models.json). No secrets.
- providers.json: "Which providers exposed and how?" Carries enabled, connection (api_base, api_key_env as name, prefix), endpoints (discovery path), policy (priority, disabled_models). No discovery metadata.
- config.yaml: "How does LiteLLM implement policy?" Fully derived, never hand-edited.

### 4.2 Pure-Join Renderer
Renderer became pure join: for each enabled provider, take inventory models, drop disabled_models, emit one YAML entry per model. No classification, fallback tables, or provider-specific if. Backend-agnostic - swapping LiteLLM only touches renderer.

### 4.3 Legacy Removal
Deleted four-way Nix split: providers-open/-restricted/-manual.nix, health registry, providers-enabled.json, provider-defaults.json. Health check (litellm-doctor) now derives from providers.json (zero provider-specific rules).

### 4.4 Runtime Editability
Committed providers-seed.json seeds runtime providers.json only on first boot (if absent). Runtime edits survive rebuild. litellm-add-provider as no-rebuild CLI.

### 4.5 Key Fixes in Seed
- aihubmix -> disabled (free requires topup)
- fireworks-ai -> enabled (genuinely free)
- Result: 131 models rendered with correct prefixes, litellm-doctor clean

## 5. Diagnosis

Four lists with same data = three too many. Drift inevitable. Collapsing to providers.json (policy+connection+endpoints) updates all consumers at once. Pure-join renderer discipline enables backend-agnostic data files. Runtime state editable without rebuild via seed-on-first-boot pattern.

## 6. Preliminary Assessment

Architecture quiet. 131 models rendered correctly. Doctor passes. Inventory/policy shape unchanged through later Podman transition and live backend tests.

## 7. Solution Summary

- Replaced 4 provider lists with 2 data files (models.json, providers.json) + derived config.yaml
- Renderer: pure join (no provider logic)
- Health check derives from providers.json
- Runtime providers.json seeded once, editable without rebuild
- No-rebuild CLI for provider additions
- Fixed aihubmix/fireworks-ai classification in seed

## 8. Verification Plan

- Verify litellm-doctor passes
- Confirm 131 models rendered with correct prefixes
- Test no-rebuild provider addition
- Validate runtime edits survive rebuild

## 9. Pending Actions

- Rename litellm/ to gateway/ (deferred)
- Daily fetch-models timer (deferred)

## 10. Recommendations

- Single source of truth per question (inventory vs policy vs implementation)
- Pure-join renderer worth upfront discipline
- Seed runtime state on first boot only
- Keep Nix build vs runtime state boundary explicit
- Defer premature renames/timers