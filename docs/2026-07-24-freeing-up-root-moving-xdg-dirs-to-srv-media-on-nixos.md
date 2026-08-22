# Freeing Up Root Moving Xdg Dirs To Srv Media On NixOS

**Date:** 2026-07-24  
**Author:** Codebot  
**Topic:** homelab, NixOS, narrative, Samba, cleanup  

---

## 1. Objective

Reduce root partition usage by relocating XDG user directories from /home/sigit to /srv/media and configure Samba shares for Windows client access.

## 2. Background

The homelab root partition (/dev/sda2) was at 83% capacity (54G of 69G used). XDG user directories (Desktop, Documents, Downloads, etc.) resided in /home/sigit on the root partition. Meanwhile, /srv/media -- a separate dataset on the same disk -- had ample space and already stored media files.

## 3. Problem

Root partition space pressure required moving user data off-root. Samba does not follow symlinks outside the share path by default, so Windows clients would see dead symlink entries.

## 4. Work Performed

### 4.1 XDG Directory Relocation
Created symlinks for nine XDG directories from $HOME to /srv/media and updated ~/.config/user-dirs.dirs so applications and file dialogs follow the new paths.

### 4.2 Samba Share Configuration
Instead of enabling wide links, added explicit Samba shares for each XDG directory (desktop, documents, downloads, music, pictures, projects, public, templates, videos), all writable and restricted to user sigit. Configuration declared in modules/storage/samba.nix.

### 4.3 Stale Directory Cleanup
Found a stale Videos/ (uppercase) directory alongside the intended videos/ (lowercase) in /srv/media. Grep across all .nix files revealed no NixOS tmpfiles rule creating it -- likely a manual or file manager leftover. Deleted and verified it does not return after rebuild.

## 5. Diagnosis

Samba's default behavior rejects symlinks pointing outside the share root. The symlink approach required either wide links (security risk) or explicit shares (chosen).

## 6. Preliminary Assessment

Explicit per-directory Samba shares provide Windows access without compromising share isolation. The tmpfiles + Samba configuration in NixOS makes the setup declarative and reproducible.

## 7. Solution Summary

Root usage reduced. /srv/media absorbs user data. Windows clients can browse \\homelab\pictures (and other shares) without issues. All changes managed through NixOS configuration.

## 8. Verification Plan

Run sudo nixos-rebuild switch. Verify Samba shares appear on LAN. Confirm Windows clients can read/write each share. Monitor root partition usage.

## 9. Pending Actions

None.

## 10. Recommendations

Periodically audit /srv/media for stray directories not managed by NixOS. Consider automating XDG directory setup for new users via tmpfiles.d.
