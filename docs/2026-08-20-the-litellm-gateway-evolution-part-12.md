# The LiteLLM Gateway Evolution - Part 12

*Module restructure recovery*

**Date:** 2026-08-20  
**Author:** Codebot  
**Topic:** session, NixOS, homelab, LiteLLM, sudo, workflow, skills, refactor

---

## 1. Objective

Get a working `nixos-rebuild switch` for the homelab `nix-lab` repo after a failed module restructuring, while respecting the data cap on the user's ISP and the limited disk on the homelab.

## 2. Background

The `nix-lab` repo had a failed rebuild caused by a broken `homelab-databases` activation script. Earlier work restored `common/db` to its original state and reorganized `common/ai/litellm` into a subdir. A nixpkgs bump to `b18a4b9` was then attempted to obtain `pnpm-9.15.9`.

## 3. Scope: Two Active Workstreams

- nix-lab module reorg: `common/db` restored to original; `common/ai/litellm` reorganized into a subdir (a `default.nix` index plus `litellm-cli.nix`, `litellm-podman.nix`, `litellm-podman-helper.nix`).
- LiteLLM reorg, in two parts: (1) the nix-lab `common/ai/litellm/` subdir reorg above; (2) the live `/srv/repo/litellm-cli` repo, which is actively being reorganized (current commit `02b6444`, "fix: update ZAI models"). Its flake narHash is a moving target, pinned to `NKbc...` via `nix flake update litellm-cli`. Any future change to `litellm-cli` requires re-running that update before a switch.

## 4. Symptoms

- Repeated `nixos-rebuild switch` failures: `error: Cannot build ... builder failed ... lack of free disk space`.
- A `litellm-cli` flake input NAR-hash mismatch (expected `NKbc...`, got `MwzD...`) because the external repo had advanced.
- Approximately 12 GB re-downloads repeatedly consuming the user's limited ISP data cap.

## 5. Work Performed

### 5.1 Skill and agent consolidation

- Deleted the duplicate `homelab-management` agent.
- Renamed and relocated the merged skill to `/home/sigit/.config/opencode/skills/homelab-management/SKILL.md`; deleted the old `ssh-homelab` skill directory. Preserved the "revert only the broken module" rule (rule 5).

### 5.2 Reverted the nix-lab build target to a proven-cached state

On the homelab host:

```bash
git checkout db4e196 -- flake.lock   # nixpkgs 714a5f8c4ead...
nix flake update litellm-cli         # offline; narHash -> NKbc...
git checkout db4e196 -- system/default.nix   # removed pnpm-9.15.9 permit
sudo nix-collect-garbage -d          # freed 12.7 GiB
```

Result: disk 24 G free; live generation `157` (`714a5f8`).

## 6. Diagnosis

Root causes: (a) rolling nixpkgs commits produces different store hashes, forcing full re-downloads; (b) the `0dd31db` 12 GB pull was wasted because a `git reset --hard` also reverted `flake.lock`, discarding the already-built closure. The disk failures were build-time pressure, not a service bug (an isolated build of the failing derivation succeeded).

## 7. Fix

Reverted to the cached `714a5f8` state, which switches cleanly with zero download. This abandons the `b18a4b9`/`pnpm-9.15.9` bump for now.

## 8. Mitigation Plan

- Never `git reset --hard` across `flake.lock`/nixpkgs on a failed build; revert only the broken module. Recorded in `AGENTS.md` and the skill (rule 5).
- Treat `litellm-cli` as a moving target: re-run `nix flake update litellm-cli` whenever that repo changes.

## 9. Verification Plan

User runs `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` (cached, zero download). Expect a benign transient `failed` LiteLLM healthcheck that self-clears.

## 10. Pending Actions

- Commit the reverted `flake.lock` and `system/default.nix` after a clean switch.
- Revisit the `b18a4b9`/`pnpm` bump only when bandwidth allows.

## 11. Recommendations

- On a failed build, revert only the broken module; never roll back nixpkgs.
- Keep the `714a5f8` closure cached; avoid aggressive `nix-collect-garbage` that removes it.
- Re-run `nix flake update litellm-cli` after any change to `/srv/repo/litellm-cli`.
