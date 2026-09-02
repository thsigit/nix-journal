# Architecture Conformance Pass: Punching Up nix-lab's Single Source of Truth

**Date:** 2026-09-02  
**Author:** Codebot  
**Topic:** nix, nixos, architecture, refactor, settings, secrets

---

## 1. Objective (or: Who Left This Hardcoded Everywhere?)

The homelab nix-lab flake had grown organically. Just about every leaf module knew the user's name (`sigit`), the LAN interface (`enp0s31f6`), the static IP (`192.168.1.3`), and the domain (`home.arpa`) by heart. They were committed to the config like an elderly relative committed to an opinion.

This session was a systematic **architecture-conformance sweep**: audit every leaf module in `common/*`, `profiles/`, `system/`, plus `settings/` and `secrets/`, against the application-architecture principles (single source of truth, machine-specific config at the edge, no duplication), fix the violations, and remove values nobody was consuming anymore.

Rules of engagement: never run `nixos-rebuild` myself (owner does that), verify with `nix flake check` + `nix build --dry-run`, commit only after the build is clean, and keep every rendered value byte-identical so the changes are pure de-duplication.

## 2. Background

### 2.1 The Architecture We're Measuring Against

Two standing documents define the targets:
- `principles.md` - "12. Keep machine-specific configuration at the edge", "11. Single Source of Truth", avoid duplication, small cohesive modules.
- `nix.md` - leaf modules are self-contained and always-on when imported; a directory `default.nix` is a pure importer.

`settings/default.nix` is the canonical home for `user`, `directories`, `ai`, and (now) `network` and `security`. The idea: a value lives in exactly one place, and every module that needs it derives it.

### 2.2 The Pain

Multiple modules duplicated the same machine/user facts:

| Fact | Duplicated in |
|------|---------------|
| `sigit` / `users` | sops, vsftpd, codebot, users, failsafe, xfce4 autologin, home-manager |
| `enp0s31f6`, `192.168.1.3` | networking, dnsmasq, samba, failsafe |
| `home.arpa` | pki, caddy, codebot, networking, dnsmasq, failsafe |
| `/etc/ssl/homelab` | pki, caddy, codebot |
| `Asia/Makassar` | locale, failsafe |

And `settings/` itself carried values nothing referenced.

## 3. Problem

The hallmarks of an over-fat, hardcoded config:
1. **Hardcoded user/machine values** scattered across leaf modules - change the user name and you're editing ten files, not one.
2. **No settings entry** for network/LAN or the cert directory, so modules invented their own.
3. **Orphaned settings** (`baseEnv`, `qbittorrentEnv`, `ai.root`, `ai.repo`) and **orphaned secrets** (`infra.yaml`, `opencode.env`) that nothing consumed - dead weight that invites confusion.

The goal was to consolidate every duplicatable value into `settings/`, make modules read from it, and delete what nobody used.

## 4. Work Performed

### 4.1 network + packages (commit a14cd94)

Added a `network` section to `settings/` (single source of truth):

```nix
network = {
  lanInterface = "enp0s31f6";
  lanIp = "192.168.1.3";
  lanPrefix = 24;
  lanCidr = "192.168.1.0/24";
  gateway = "192.168.1.1";
};
```

Then:
- `system/networking.nix` and `common/network/dnsmasq.nix` both consume it - the static WAN IP, interface, and domain are no longer typed out in two places.
- Split `common/packages/default.nix` (was part package list, part system config):
  - `programs.bash` shell prompt/completion -> `system/shell.nix`
  - `powerManagement.cpuFreqGovernor = "performance"` -> `system/power.nix`
  - `packages/` is now software/programs only.

### 4.2 security, storage, web (commit 34735aa)

- `security/pki.nix` - cert SAN domains and `sslDir` derived from settings (root CA/wildcard cert generation now follows `settings.domain`).
- `security/sops.nix` - `age.keyFile` and secret owner/group derived from `settings.user`.
- `web/caddy.nix` + `web/codebot.nix` - `sslDir`, user/group, domain from settings.
- `storage/samba.nix` - netbios/wsdd hostname from `config.networking.hostName`; LAN CIDR + user from settings.
- `storage/vsftpd.nix` - `userlist` from `settings.user` (kept FTP at owner's request; package dedup deferred).

### 4.3 machines (commit 14f63a4)

- `profiles/failsafe/default.nix` - the recovery profile deliberately does NOT import `../../system` (so a broken base config doesn't take down recovery), but it can still safely read standalone `settings/`. Its re-hardcoded LAN values now come from `settings.network`.
- `machines/vantage-v14g4/` is an unreferenced placeholder (no hardware yet) - left as-is intentionally.

### 4.4 profiles (commit f7c6a2c)

- `workstation/default.nix` - `home-manager.users.sigit` -> `users.${user.name}`.
- `workstation/home.nix` - `username` + `homeDirectory` from `settings.user`; dropped `enableCompletion` (duplicated by `system/shell.nix`'s `completion`).
- `workstation/xfce4.nix` - `autoLogin.user` from settings.
- `failsafe` - `users.users.sigit` -> `users.${user.name}`.

### 4.5 system (commit 83dd333)

- `system/users.nix` - user + `getty.autologinUser` from settings.
- `system/locale.nix` - `time.timeZone` from `settings.timezone`.
- Noted (deferred): the root filesystem UUID is duplicated in `boot`/`grub-failsafe` and `hardware-configuration.nix`. It's a machine-hardware fact with no natural settings home, and `hardware-configuration.nix` is auto-generated - left alone to avoid over-engineering.

### 4.6 secrets + settings cleanup (commit 5f84708)

Verified then removed orphaned entries:

| Removed | Reason |
|---------|--------|
| `settings.baseEnv` (PUID/PGID/TZ) | no consumer; only self-reference |
| `settings.qbittorrentEnv` (WEBUI_PORT) | no qbittorrent service remains |
| `settings.ai.root`, `settings.ai.repo` | only `ai.models` is used (llama-cpp) |
| `secrets/opencode.env` | encrypted but never referenced by any sops declaration |

**Kept**:
- `settings.user.gid` - for possible future use.
- `secrets/infra.yaml` - holds cloudflare id/token + github token; user wants to verify whether it's live before touching it.

## 5. Diagnosis

The config was not broken - it was **healthy but undisciplined**. The core issue was duplication of stable facts instead of a single reference, plus accumulated dead settings/secrets. Nothing was mis-provisioned; the risk was purely maintenance and drift (edit the user in one place, forget the other nine).

## 6. Solution Summary

A clean layering:

```
settings/  -> user, timezone, directories, ai, tailnet, domain, security.sslDir, network
   |
   v
derived by every leaf module (common/*, profiles/*, system/*) via `import ../settings`
```

- Machine identity (hostname, hardware UUID) stays at the edge: `machines/` + `system/networking.nix`.
- Recovery (`failsafe`) reads standalone `settings/` but not `system/`.
- Every changed value rendered byte-identical to the old hardcoded one - pure consolidation, zero behavioral change.

## 7. Verification Plan

For each change, on `homelab`:
1. `nix flake check --no-build` - all four configs green (system, server, workstation, failsafe).
2. `nix build .#nixosConfigurations.<host>.config.system.build.toplevel --dry-run`.
3. Probe rendered values with `nix eval` to confirm they match the previous hardcoded ones (e.g. timezone `Asia/Makassar`, autologin `sigit`, dnsmasq listen `["127.0.0.1","192.168.1.3"]`, pki SAN all under `home.arpa`).

## 8. Pending Actions

- Owner ran the final rebuild; current generation on `homelab` is `system-207` (store `...yva2pbjd6cc8...`), confirmed clean.
- `secrets/infra.yaml` - verify the cloudflare/github tokens it holds are live/in use, then keep or remove.
- Root UUID de-dup in boot/grub-failsafe - deferred, low priority.

## 9. Recommendations

- **Establish one settings section per domain next** (e.g. extend `security`/`network` before adding another `service` value to a leaf). The pattern now exists; use it.
- **Revisit package ownership** (the deferred item): a handful of leaves and `common/packages/default.nix` both list the same package in `environment.systemPackages`. Decide per-leaf ownership so a package is declared in exactly one place.
- **Do not wire `vantage-v14g4`** until it has a real `hardware-configuration.nix`. Keep it a placeholder.
- For any future machine: put LAN/hardware facts in `settings/network` (extend as needed) and keep `hardware-configuration.nix` generated.

## 10. Conclusions

This was the rare refactor where the diff shrank the config - removing the duplication, not swapping one form for another. If the whole point of "single source of truth" is that you change the user once and the whole fleet follows, nix-lab is now much closer to that ideal. The next time someone asks "where does the LAN IP live?", the answer is one file, not a scavenger hunt.

Generated by Big Pickle (OpenCode)
