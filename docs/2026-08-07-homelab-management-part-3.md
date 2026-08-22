# Homelab Management - Part 3

*State relocation + multi-service fixes*

**Date:** 2026-08-07  
**Author:** Codebot  
**Topic:** NixOS, homelab, Podman, LiteLLM, Karakeep, meilisearch, openNDS, pki, recovery  

---

## 1. Objective

Document four parallel work threads: Karakeep/Meilisearch state relocation to persistent storage, LiteLLM migration to Podman+PostgreSQL, openNDS captive portal regression repairs, boot failure investigation.

## 2. Background

Root partition wiped on reformat. /srv partition on /dev/sda1 survives. Data needing persistence must live under /srv/appdata.

## 3. Problem

Four threads: state relocation for Karakeep/Meilisearch, LiteLLM container migration, openNDS regressions, unsolvable boot failure on gens 28-31.

## 4. Work Performed

### 4.1 State Relocation: Karakeep and Meilisearch
Both store mutable state under /var/lib (root fs). Goal: move to /srv/appdata on preserved /dev/sda1 ext4.

Attempt 1: Absolute StateDirectory paths (/srv/appdata/karakeep). Systemd 260 silently ignores absolute paths, logging "StateDirectory= path is absolute, ignoring" -- $STATE_DIRECTORY empty, karakeep-init couldn't write /settings.env (permission denied), Meilisearch data dir never chowned.

Attempt 2: tmpfiles L symlinks mapping /var/lib/karakeep -> /srv/appdata/karakeep. Systemd 260 rejects symlinked StateDirectory with ELOOP. tmpfiles L doesn't replace existing symlinks -- only Karakeep got new link; browser and meilisearch kept stale targets.

Attempt 3 (WORKING): Bind mounts via fileSystems. Declare state directories as real filesystems:
```nix
fileSystems = {
  "/var/lib/karakeep" = { device = "/srv/appdata/karakeep"; fsType = "none"; options = ["bind"]; noCheck = true; };
  # same for karakeep-browser and meilisearch
};
```
Lands in /etc/fstab as none bind entries. systemd-fstab-generator creates .mount units. Service keeps plain relative StateDirectory. systemd creates directory, chowns mount root to service user, everything beneath really /srv/appdata.

Ordered services after mounts:
```nix
systemd.services.karakeep-init.after    = [ "var-lib-karakeep.mount" ];
systemd.services.karakeep-init.requires = [ "var-lib-karakeep.mount" ];
```

Wrinkle 1: DynamicUser units can't mount their own state. Meilisearch and karakeep-browser (DynamicUser=true) failed with EEXIST -- systemd 260 mounts internal special execution directory over StateDirectory path, can't do that over existing mountpoint. Fix: static system users for these two:
```nix
users.users.meilisearch = { isSystemUser = true; uid = 1015; group = "meilisearch"; };
users.groups.meilisearch = { gid = 1015; };
systemd.services.meilisearch.serviceConfig = { DynamicUser = lib.mkForce false; User = "meilisearch"; Group = "meilisearch"; };
```
Karakeep already had static user (uid 995). Pinned uids (1015/1016), pre-chowned /srv/appdata trees before switch.

Wrinkle 2: Unit names escape hyphens. Browser mount /var/lib/karakeep-browser -> mount unit var-lib-karakeep\x2dbrowser.mount (systemd escapes literal hyphen as \x2d). after/requires referenced unescaped name -> "Unit var-lib-karakeep-browser.mount not found". Fixed with escaped name. requiresMountsFor unavailable in this nixpkgs.

Result: All services active. State directories bind mounts onto /srv/appdata, owned by stable users, data survives root reformat. Fix in modules/media/karakeep.nix, single fix(media) commit.

### 4.2 LiteLLM: Systemd-Native to Podman Container
LiteLLM moved to Podman container 2026-07-18. Container runs with ai.podmanLitellm.enable = true, ai.litellmConfig.enable = true. Database: PostgreSQL on 127.0.0.1:5432, LiteLLM database/role created at activation.

Database password generated at activation via openssl rand -hex 16, written to /srv/appdata/litellm-container/database.env (0600, owned by sigit). Container mounts via environmentFiles. Oneshot litellm-db-password.service runs after postgresql-setup, re-syncs role password with ALTER ROLE.

P1000 auth bug: LiteLLM with master key treats non-master API key requests as DB-managed, requiring PostgreSQL. Without connected DB, login succeeds but session creation fails (login_utils.py only creates session key if DATABASE_URL defined). litellm-db-password.service originally lacked wantedBy=multi-user.target and when executed as User=postgres couldn't read 0600 database.env owned by sigit. Fix: run service as root using runuser -u postgres for psql, add wantedBy=multi-user.target.

### 4.3 openNDS: Five Regressions Repaired
Diffing each modules/network/ap/*.nix against known-working nix-lab originals:

1. opennds.nix: Type="forking" with openNDS -b and setupScript symlinking /usr/local/bin (NixOS has no /usr/local/bin, aborted activation). Fix: Type="exec" + openNDS -f (foreground), resources copied once in activation script, /usr/local/bin symlinks removed.

2. openNDS package: ndsctl wrapper only coreutils on PATH; C binary shell deps (gawk, gnugrep, procps, iptables, nftables, curl) not visible. Fix: unwrapped binaries in libexec, PATH-complete wrappers in bin, libmicrohttpd as build-time-only nativeBuildInput.

3. hostapd.nix: auth_server_shared_secret = "testing123" baked into store. Fix: drop from settings, use dynamicConfigScripts.eapSecret to append sops radius-secret at runtime.

4. freeradius.nix: secret + user password hardcoded; EAP certs generated at BUILD TIME (private key world-readable in /nix/store). Fix: sops secrets (radius-secret, radius-users), certs generated at activation into /srv/appdata/freeradius/certs owned by radius, runtime clients.conf/users seeded in preStart wrapped in lib.mkBefore.

5. router.nix: NAT flushed SHARED nixos-nat-pre/nixos-nat-post chains, destroying other module rules. Fix: dedicated opennds-pre/opennds-post chains, flushing only ours.

### 4.4 TLS SAN Coverage
pki.nix used mkIf(pathExists) for runtime CA paths, causing builds to fail with FileNotFoundError when CA existed -- nss-cacert sandbox can't read absolute host paths. Fix: commit CA cert as modules/security/homelab-ca.crt, use static list security.pki.certificateFiles = [ ./homelab-ca.crt ]. Added extraDomains list so homelab cert always includes SANs for darkstat, LiteLLM, BitRouter, wallabag, localai.home.arpa independent of enabled services.

### 4.5 Boot Failure
Generations 28-31 all die at: "switch root target contains no usable init". Proved NOT: AP bundle (disabled gen 31), BitRouter/LiteLLM (present in working gen 27 and failing gen 28), initrd (identical), kernel params, store integrity, SATA flakiness. Netconsole capture empty -- e1000e driver module not builtin, if interface not link-up at module load or listener not reachable from initrd pre-root namespace, silence.

Per client directive: stopping active troubleshooting. Failure in boot/init path itself, not config. Next session: boot-recovery hypotheses (ESP vs GRUB entry correctness, grubenv saved_entry, reliable serial/VGA console dump).

## 5. Diagnosis

Systemd 260 StateDirectory rejects absolute paths and symlinked targets. Only reliable approach for persistent state: bind mounts via fileSystems with explicit mount-unit dependencies. Container DB auth requires strict service ordering. Headless netconsole in initrd fragile with module network driver. NixOS build sandbox can't read runtime host paths.

## 6. Preliminary Assessment

State relocations and container migration done. openNDS repair built and ready for live test. Boot failure filed for separate recovery session.

## 7. Solution Summary

Karakeep/Meilisearch state on persistent partition via bind mounts. LiteLLM on Podman+PostgreSQL with fixed auth. openNDS five regressions fixed. Boot failure documented for recovery session.

## 8. Verification Plan

Run rebuild. Test Karakeep/Meilisearch persistence. Verify LiteLLM auth. Test openNDS guest splash. Schedule boot-recovery session.

## 9. Pending Actions

Boot-recovery session per skill. Live test openNDS after rebuild.

## 10. Recommendations

- Use bind mounts for persistent state on NixOS, not StateDirectory overrides
- Static users for services with persistent state directories
- Verify mount unit names with systemctl list-unit-files (hyphens escaped)
- Pre-chown to pinned UIDs before switch
- Container password services: run as root with runuser, add wantedBy
- Commit CA certs for build-time access
- Dedicated nftables chains per module
