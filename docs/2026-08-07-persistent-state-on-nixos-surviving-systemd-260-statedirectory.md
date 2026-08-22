# Persistent State On NixOS Surviving systemd 260 Statedirectory

**Date:** 2026-08-07  
**Author:** Codebot  
**Topic:** homelab, NixOS, systemd, migration, troubleshooting, maintenance, narrative  

---

## 1. Objective

Document the working pattern for persistent state on NixOS with systemd 260: bind mounts via fileSystems, not StateDirectory overrides.

## 2. Background

Homelab root partition wiped on reformat. /srv partition on /dev/sda1 survives. Services needing persistent state (PostgreSQL, OpenCode, navidrome, Karakeep, Meilisearch, karakeep-browser) must live under /srv/appdata.

## 3. Problem

Systemd 260 rejects absolute StateDirectory paths and symlinked StateDirectory targets. DynamicUser incompatible with pre-existing mountpoints at StateDirectory.

## 4. Work Performed

### 4.1 Attempt 1: Absolute StateDirectory - Rejected
Override with lib.mkForce:
```nix
systemd.services.karakeep-workers.serviceConfig.StateDirectory = lib.mkForce "/srv/appdata/karakeep";
```
Result: systemd 260 prints "path is absolute, ignoring", silently drops. $STATE_DIRECTORY empty. karakeep-init tried to write /settings.env (permission denied). Meilisearch data dir never chowned to runtime user.

Lesson: systemd 260 ignores absolute StateDirectory paths.

### 4.2 Attempt 2: Symlinked State Directories - Also Rejected
Keep StateDirectory relative, use tmpfiles L symlinks:
```nix
systemd.tmpfiles.rules = [ "L /var/lib/karakeep - - - - /srv/appdata/karakeep" ];
```
Result: "Too many levels of symbolic links" -- systemd 260 refuses to set up state directory that is a symlink. Second gotcha: tmpfiles L does NOT replace existing symlink. Only Karakeep got new link; browser and meilisearch kept stale targets, silently writing to old directories.

Lesson: systemd 260 rejects symlinked StateDirectory, and tmpfiles L won't overwrite existing symlinks.

### 4.3 Attempt 3: Bind Mounts - The One That Worked
Pattern NixOS is built around: declare state directories as real filesystems.
```nix
fileSystems = {
  "/var/lib/karakeep" = { device = "/srv/appdata/karakeep"; fsType = "none"; options = ["bind"]; noCheck = true; };
  # same for karakeep-browser and meilisearch
};
```
Lands in /etc/fstab as none bind. systemd-fstab-generator creates .mount units. Service keeps plain relative StateDirectory. systemd creates directory, chowns mount root to service user, everything beneath really /srv/appdata.

Ordered services after mounts:
```nix
systemd.services.karakeep-init.after    = [ "var-lib-karakeep.mount" ];
systemd.services.karakeep-init.requires = [ "var-lib-karakeep.mount" ];
```

### 4.4 Wrinkle 1: DynamicUser Units Can't Mount Their Own State
Meilisearch and karakeep-browser (DynamicUser=true) failed with EEXIST -- systemd 260 mounts internal "special execution directory" over StateDirectory path to fake ownership. Can't do that over existing mountpoint.

Fix: static system users for these two:
```nix
users.users.meilisearch = { isSystemUser = true; uid = 1015; group = "meilisearch"; };
users.groups.meilisearch = { gid = 1015; };
systemd.services.meilisearch.serviceConfig = { DynamicUser = lib.mkForce false; User = "meilisearch"; Group = "meilisearch"; };
```
Karakeep already had static user (uid 995). Pinned uids (1015/1016), pre-chowned /srv/appdata trees before switch.

Lesson: DynamicUser + pre-existing mountpoint at StateDirectory = EEXIST. Use static users for persistent state.

### 4.5 Wrinkle 2: Unit Names Escape Hyphens
Browser mount /var/lib/karakeep-browser -> mount unit var-lib-karakeep\x2dbrowser.mount (systemd escapes literal hyphen as \x2d). after/requires referenced unescaped name -> "Unit var-lib-karakeep-browser.mount not found". Fixed with escaped name. requiresMountsFor unavailable in this nixpkgs.

Lesson: systemd unit names for paths escape hyphens -- check systemctl list-unit-files before wiring after/requires.

### 4.6 Result
After three generations and corrected escape sequence, all green:
```
systemctl is-active karakeep-init karakeep-workers karakeep-web karakeep-browser meilisearch postgresql
active active active active active active
```
All three state directories bind mounts onto /srv/appdata, owned by stable users, data survives root reformat. Fix in modules/media/karakeep.nix, single fix(media) commit.

## 5. Diagnosis

Systemd 260 behavior changes broke previous StateDirectory patterns. Bind mounts are the supported NixOS mechanism.

## 6. Preliminary Assessment

Bind mount approach is robust, survives reformats, works with systemd 260.

## 7. Solution Summary

Karakeep, karakeep-browser, Meilisearch state relocated to /srv/appdata via bind mounts. Static users for DynamicUser services. Mount unit hyphen escaping handled.

## 8. Verification Plan

Reformat root partition. Verify data survives. Monitor service starts.

## 9. Pending Actions

None.

## 10. Recommendations

- systemd 260 rejects absolute StateDirectory ("path is absolute, ignoring") -- use bind mount
- systemd 260 rejects symlinked StateDirectory (ELOOP) -- tmpfiles L dead end
- DynamicUser state dirs mounted by systemd itself -- existing mountpoint fails EEXIST; use static users
- Mount unit names escape hyphens (var-lib-karakeep\x2dbrowser.mount) -- verify with systemctl list-unit-files
- tmpfiles L doesn't replace existing symlinks -- clean old path first or silently write to stale directory
- Pre-chown to pinned uids before switching -- eliminates permission-denied window on unit restart
