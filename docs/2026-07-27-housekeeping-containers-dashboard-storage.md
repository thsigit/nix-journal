# Homelab Management - Part 1

*Housekeeping: containers, dashboard, storage*

**Date:** 2026-07-27  
**Author:** Codebot  
**Topic:** homelab, NixOS, Podman, Caddy, cleanup, housekeeping, maintenance, session, Mem0, OpenCode  

---

## 1. Objective

Housekeeping pass on homelab: remove unused containers, fix internal dashboard, reclaim storage by converting downloaded videos to playlist references.

## 2. Background

Test for homelab-management skill and integration of past session narratives (ses_05da934dfffeTdyB4uSlE8Nao0, ses_05da69450ffeyYBHiuzmKH0WD9).

## 3. Problem

Unused containers consuming resources. Dashboard had stale links. Video archive consuming ~60GB.

## 4. Work Performed

### 4.1 Container Removal: wallabag and localai
Both Podman containers defined in flake, not actively used.
- wallabag: Deleted modules/media/podman-wallabag.nix, removed import from media/default.nix, dropped DNS entry wallabag.home.arpa from dnsmasq.nix.
- localai: Salvaged vibevoice-cpp model artifacts (vibevoice-realtime-0.5B-q8_0.gguf, vibevoice-cpp.yaml, ._gallery_vibevoice-cpp.yaml) from container's /build/models/ to /srv/ai/gguf/models/. Then removed modules/ai/podman-localai.nix, import, DNS entry localai.home.arpa.

### 4.2 Dashboard Repair: /srv/www/homepage/index.html
Served by Caddy at homelab.home.arpa.
- Removed dead: localai.home.arpa, wallabag.home.arpa
- Added running but unlinked: karakeep.home.arpa (bookmarking), copyparty.home.arpa (file sharing), opencode.home.arpa (headless coding agent)
- Subpath services (godmod3, freegpt, glossopetrae, mrtg, lidarr) correct
- Footer count updated: 16 -> 18 layanan (17 after changes)

### 4.3 Video Archive to Playlist Conversion (~60GB Freed)
Blender directory tree: 8 subdirectories with YouTube downloads named with video ID suffix.
For each directory: scan video files, extract 11-char YouTube ID, generate DAUMPLAYLIST (.dpl) pointing to https://www.youtube.com/watch?v=<ID>, delete local files.
- Blender: 101 files deleted across 16 directories, 83 playlist entries created, .dpl files moved to /srv/media/videos/Blender/, empty dirs removed
- Full /srv/media/videos/ recursive: 154 videos deleted across 20 directories, 38 .dpl playlists created/moved, 7 empty dirs removed
- Preserved (no YouTube ID in filename): Old Whatsapp (219), Twitter (29), storage/Solo Levelling (25), Blender/old (3), ~42 scattered across css, investopedia, MIsc, Javascript, AWS, PHP, figma, web3
- Total reclaimed: ~60GB

### 4.4 Configuration Hygiene
- #homelab and #workstation flake outputs identical except desktop profile (Xfce + extra packages) -- confirmed via flake.nix and profile files
- AGENTS.md documents this; saved as Mem0 decision memory
- All changes committed; final activation via manual sudo nixos-rebuild switch --flake .#homelab

## 5. Diagnosis

Unused containers and stale dashboard links create maintenance debt. Video downloads replaceable with playlist references.

## 6. Preliminary Assessment

Cleanup reduces resource usage and improves dashboard accuracy. Playlist approach preserves access without storage cost.

## 7. Solution Summary

Two containers removed, dashboard updated, ~60GB reclaimed via playlist conversion. Changes staged for rebuild.

## 8. Verification Plan

Run rebuild. Verify wallabag/localai gone. Confirm Caddy vhosts regenerated. Optionally prune preserved non-ID directories.

## 9. Pending Actions

Run sudo nixos-rebuild switch --flake .#homelab. Verify changes active.

## 10. Recommendations

Regular container audits. Dashboard link validation in CI. Automate video-to-playlist conversion for new downloads.
