# The LiteLLM Gateway Evolution - Part 4

*Rename data files*

**Date:** 2026-07-24  
**Author:** Codebot  
**Topic:** LiteLLM, NixOS, homelab, cli, refactor, architecture, maintenance  

---

## 1. Objective

Rename committed data files in pkgs/litellm-cli/data/ to avoid confusion with runtime mirrors in /srv/appdata/litellm/, update all references, and document the control-plane/bridge/runtime architecture.

## 2. Background

The LiteLLM gateway uses two data tiers: committed (build-time source in repo, baked into Nix store) and runtime (live state in /srv/appdata/litellm/ edited by CLI tools, survives rebuilds). Both tiers used identical filenames causing ambiguity when paths appeared in systemd units or scripts.

## 3. Problem

Same filenames in different tiers with different lifecycles caused mental overhead resolving which tier a path referred to. Files: models.json, declared-models.json, router.yaml, providers-seed.json.

## 4. Work Performed

### 4.1 Naming Scheme Design
Client proposed new names prioritizing uniqueness over semantic purity:
- models.json -> models-dev.json (inventory fetched from models.dev)
- declared-models.json -> models-seed.json (admin-authored seed models)
- router.yaml -> router-seed.yaml (committed router config, seeded if runtime absent)
- providers-seed.json unchanged (already disambiguated)

### 4.2 Editability Documentation
Created table documenting editability per file:
- models-dev.json: not directly editable, updated via fetch-models
- models-seed.json: editable, manual edit + commit
- providers-seed.json: editable, manual edit + commit
- router-seed.yaml: editable, manual edit + commit

### 4.3 Rename Execution
Three git mv operations. Swept all references across flake: fetch-models.sh, default.nix, litellm-config.nix, architecture README, session notes. Caught sed mangling a Nix interpolation brace during bulk edit -- reverted to explicit edits.

### 4.4 Verification
- nix-instantiate --parse on default.nix, litellm-config.nix, podman-litellm.nix: all clean
- Grep confirmed zero old filename references
- git diff --stat: 8 files, 16 insertions, 16 deletions, three 100%-detected renames
- Committed as a29007f

### 4.5 Architecture Documentation
Documented three-layer architecture:
- pkgs/litellm-cli: control plane (inventory, policy, renderer, CLI), standalone Nix package
- litellm-config.nix: NixOS bridge (systemd, activation, timers, sops), produces config.yaml
- podman-litellm: runtime (serves proxy), consumes config.yaml
- Bridge depends on control plane; neither is LiteLLM-agnostic

## 5. Diagnosis

Filename collision at tier boundary creates cognitive load. Semantic purity less valuable than uniqueness when lifecycles differ.

## 6. Preliminary Assessment

Renaming resolves ambiguity. Architecture walkthrough confirmed design soundness and established shared vocabulary.

## 7. Solution Summary

Files renamed with -dev/-seed suffixes. All references updated. Architecture layers documented. Commit a29007f.

## 8. Verification Plan

Run nixos-rebuild switch. Verify CLI tools operate on correct files. Confirm runtime seeding works.

## 9. Pending Actions

None.

## 10. Recommendations

Prefer git mv + explicit edits over bulk sed for renames. Make editability/owner explicit in data file documentation. Conduct architecture walkthroughs during refactors -- cheap and valuable.
