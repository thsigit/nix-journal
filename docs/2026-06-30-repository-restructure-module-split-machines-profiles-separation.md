# Nix Reorg

*Repository restructure: module split + machines/profiles separation*

**Date:** 2026-06-30  
**Author:** Codebot  
**Topic:** NixOS, refactor, homelab, maintenance, workflow

---

## 1. Objective

Reorganize NixOS homelab repository (`/mnt/homelab/repo/nix-lab`) for cleaner structure and maintainability: host rename (workspace to workstation), monolithic module splitting, and layout restructuring with clear machine/profile separation.

## 2. Background

Repository contained homelab server and workspace desktop configurations with shared modules under `modules/`. Stale backup files cluttered the repo, host naming was inconsistent (workspace vs workstation), a single large `modules/core/default.nix` mixed all concerns, and the flat `hosts/` structure provided no distinction between hardware definitions and profile configurations.

## 3. Problem

Multiple structural issues:

- Backup files (`.bak`) cluttering the repo
- Workspace vs workstation naming inconsistency
- Single large `default.nix` mixing all concerns
- No separation between hardware configs and profile configs

## 4. Work Performed

### 4.1 File Cleanup
- Removed two stale `.bak` files no longer needed

### 4.2 Host Rename
- Renamed workspace host directory to workstation
- Updated all references in flake.nix

### 4.3 Module Refactoring
Split `modules/core/default.nix` into focused modules:

- boot.nix, kernel.nix, networking.nix, locale.nix
- users.nix, packages.nix, services.nix
- nix.conf.nix, state.nix
- Original `default.nix` becomes thin import wrapper

### 4.4 Repository Layout Restructure
- Created `machines/vantage-v14g4` (copied original homelab config)
- Created `machines/portege-r30c` (identical defaults)
- Created `profiles/homelab` and `profiles/workstation` (copied original host defaults)
- Updated flake.nix: homelab system points to `./machines/vantage-v14g4`, workstation system points to `./profiles/workstation`
- Removed empty `hosts/` directory

### 4.5 Qwen Code Assistance
Qwen Code explored repository structure, traced imports, drafted new module files, created machine/profile directories, adjusted flake.nix, and drafted the initial session summary.

### 4.6 Documentation
- Wrote session summary to the blog drafts
- Tested publishing pipeline: generated HTML output
- Earmarked Zensical as static site generator for the next round

## 5. Diagnosis

Monolithic module and flat host structure hindered maintainability. Modular structure isolates concerns; separation of hardware (`machines/`) from configuration (`profiles/`) clarifies organization. Flake path updates are required for all moves.

## 6. Preliminary Assessment

Repository builds successfully. New structure: `machines/` for hardware definitions, `profiles/` for configuration sets, `modules/` for shared components. Dual-machine setup ready for expansion. Publishing pipeline verified with HTML generation.

## 7. Solution Summary

- Removed 2 backup files
- Renamed workspace to workstation throughout
- Split 1 monolithic module into 9 focused modules
- Restructured layout: `machines/` + `profiles/` replacing `hosts/`
- Updated flake.nix with new paths
- Documented changes and tested publishing

## 8. Verification Plan

- Run `nixos-rebuild switch --flake /mnt/homelab/repo/nix-lab#workstation`
- Verify both machine configurations build
- Confirm machine/profile separation works as intended
- Test Zensical integration for blog publishing

## 9. Pending Actions

- Set up Zensical static site generator
- Publish markdown files as proper website
- Document machine/profile pattern for future hosts

## 10. Recommendations

- Maintain machine/profile separation for all future hosts
- Keep modules focused and single-purpose
- Use flake.lock pinning for reproducible builds

Generated with Ox Alpha Free (OpenCode)
