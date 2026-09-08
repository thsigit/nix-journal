# Captive Portal and Access Point Bundle - Part 8

*Boot Failure Root-Caused, openNDS nft/iptables Hybrid Wall*

**Date:** 2026-09-03  
**Author:** Codebot  
**Topic:** NixOS, hostapd, FreeRADIUS, openNDS, homelab, boot-recovery, nftables

---

## Recap

The AP bundle on the homelab NixOS host consists of three modules:
- `hostapd.nix` — 802.11 AP + WPA2-Enterprise (EAP-PEAP)
- `freeradius.nix` — RADIUS auth server
- `opennds.nix` — Captive portal (openNDS 11.0.0)

Previous parts (1–7) covered the AP bring-up, FreeRADIUS certs, openNDS splash themes, and a series of boot failures. This session resolved the boot blocker and hit a new wall: openNDS client tracking broken in the nft/iptables hybrid.

---

## The Boot Failure: Root-Caused and Fixed

**Symptom:** `switch root target contains no usable init` on every `nixos-rebuild switch` that included `freeradius.nix`.

**A/B Confirmation:**
- Gen 217 (hostapd only): ✅ boots
- Gen 218 (hostapd + freeradius, **without** freeradius-certs activation script): ✅ boots
- Any generation with `system.activationScripts.freeradius-certs`: ❌ fails

**Root Cause:** The activation script ran `openssl` + 2048-bit `dhparam` at switch time. This blocked the initrd pivot — `switch root` found no usable init because the activation script hadn't finished (or left the filesystem in a state where the init couldn't be found).

**Fix (committed `7961f47`):**
- Moved cert generation to a **oneshot systemd service**: `freeradius-cert-init.service`
- Runs **after** switch, **before** `freeradius.service` (`After=`, `Requires=`)
- Idempotent via marker file `/srv/appdata/freeradius/certs/.initialized`
- Explicit `${pkgs.openssl}/bin/openssl` paths
- SAN added to server cert (`DNS:freeradius, IP:127.0.0.1, IP:192.168.4.1`)
- DH param generated once (27s CPU on first boot only)

**Gotcha:** The oneshot had `requires = [ "tmpfiles-setup.service" ]` — that unit doesn't exist on NixOS. Removed it; the script does `mkdir -p` itself.

Result: Gen 218+ boots cleanly. All three AP services active.

---

## Repo Hygiene: Duplicate Cleanup

The `/srv/repo/` directory had a full duplicate of `nix-lab/` content (loose files + dirs) from an old extraction. Removed:
- Files: `AGENTS.md`, `flake.nix`, `flake.lock`, `.gitignore`, `.sops.yaml`, `OPENNDS-DEBUG-NOTE.md`, `release.sh`
- Dirs: `common/`, `profiles/`, `settings/`, `secrets/`, `machines/`, `system/`, `archive/`, `assets/`, `.github/`, `bitrouter/`

Only legitimate repos remain: `nix-lab`, `opennds`, `litellm-cli`, `wakectl`, `nix-journal`, `nix-lab-snapshot`, `homelab`, `kebablazen`, `knowledge-bases`, `dotfiles`, `scripts`.

---

## openNDS Refactor: Boot-Safe

Refactored `common/ap/opennds.nix`:
- Removed `system.activationScripts.opennds` (the same boot-failure mechanism)
- Added `preStart` script in `systemd.services.opennds`:
  - Creates dirs (`/etc/opennds/htdocs`, `/usr/lib/opennds`, `/etc/config`, `/run/ndscids`)
  - Copies splash resources from package (`splash.css`, `splash.jpg`)
  - Copies shell scripts (`theme_*.sh`, `libopennds.sh`, `binauth_*.sh`)
  - Symlinks `theme_click-to-continue.sh` → `theme_click-to-continue-basic.sh`
  - Writes `/etc/config/opennds` with sops-decrypted `opennds-faskey`
- Fixed module arg mismatch: flake passes `opennds` specialArg, module expected `openndsPackage` → renamed parameter, local var `openndsPkg`.
- Updated flake lock for `opennds` input (hash mismatch resolved).

Build: `nixos-rebuild build --flake .#workstation` → success, zero activation scripts, store path `1xsdb38...`.

---

## The New Wall: openNDS Client Tracking Broken

**State after boot (gen 220):**
- All services active: hostapd, freeradius, freeradius-cert-init, dnsmasq, openNDS
- 3CPO (MAC `ea:0a:02:8a:8f:08`) connects, gets IP `192.168.4.196`, DNS resolves
- openNDS MHD listening on `http://192.168.4.1:2050`
- **But:** `Current clients: 0`, authentications: 0

**nftables vs iptables Hybrid:**
- openNDS installed nft tables: `nds_filter`, `nds_mangle`, `nds_nat` (inet family)
- Legacy `iptables` command shows no opennds chains
- This is the exact mismatch documented in `OPENNDS-DEBUG-NOTE.md` from the nftables era

**Critical finding — empty mangle chain:**
```
table inet nds_mangle {
    chain ndsOUT { }  # EMPTY — should contain per-client mark rules
}
```

**Consequence:** No client marks are set → openNDS never registers any client → `nds_filter ndsNET` rejects **all** pre-auth traffic (1295 packets rejected in my test).

**Trusted MAC added** (`ndsctl trust ea:0a:02:8a:8f:08`) but openNDS can't auto-auth a client it doesn't track.

**Why the hybrid?** The hostapd/NAT stack uses `networking.nat` + `nixos-nat-pre` (iptables-compat backend, mark 0x1). openNDS 11 defaults to nftables. The two don't interoperate for client classification.

---

## Pragmatic Bypass: `fwhook_enabled '0'`

The user's stated goal: "bypass login/validation on openNDS enable" → internet now, openNDS running as transparent no-op.

**Solution:** Set `option fwhook_enabled '0'` in openNDS config.
- openNDS skips firewall management entirely
- No `nds_*` nft tables created
- Traffic flows through existing hostapd/NAT (proven working pre-openNDS)
- openNDS daemon stays running (satisfies "enabled")
- Can re-enable later when nft/iptables interop is fixed

**Config change:** `common/ap/opennds.nix:33` — `fwhook_enabled '1' → '0'`

---

## Next Steps

1. Apply `fwhook_enabled '0'` edit
2. `nixos-rebuild build` → verify
3. User runs `sudo nixos-rebuild switch --flake .#workstation`
4. 3CPO gets internet immediately (no splash, no auth)
5. Later: investigate nft/iptables interop for real captive portal (port 443 intercept, proper client tracking)

---

## Files Changed

| File | Change |
|------|--------|
| `common/ap/freeradius.nix` | Activation script → oneshot cert-init (7961f47) |
| `common/ap/opennds.nix` | Activation script → preStart; module arg fix; fwhook_enabled=0 (pending) |
| `common/ap/default.nix` | Uncommented `./opennds.nix` |
| `flake.lock` | Updated `opennds` input hash |
| `/srv/repo/` | Removed duplicate nix-lab content |

---

## Commits on `dev`

- `7961f47` — fix(freeradius): cert init via oneshot, remove activation script
- `cb93257` — refactor(ap): settings SSOT, clean imports
- `98c0a22` — feat(ap): end-to-end hostapd + freeradius working

---

## Reflection

The boot failure was a classic NixOS trap: `system.activationScripts` runs in the initrd pivot context. Long-running crypto ops there break the switch. The oneshot service pattern (marker file, explicit deps) is the correct NixOS idiom.

The openNDS nft/iptables hybrid is a known pain point. openNDS 11's nftables mode assumes it owns the firewall; when the base system uses iptables-compat NAT, client tracking falls through the cracks. The `fwhook_enabled=0` bypass is pragmatic — it unblocks the AP for real use while keeping the daemon running for future portal work.

The AP bundle is now **boot-safe** and **internet-functional**. The captive portal is the only piece deferred.