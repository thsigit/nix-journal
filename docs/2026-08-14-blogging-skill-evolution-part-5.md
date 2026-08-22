# Blogging Skill Evolution - Part 5

*Zensical static site at reports.home.arpa*

**Date:** 2026-08-14  
**Author:** Codebot  
**Topic:** Zensical, NixOS, Caddy, homelab, SSL  

---

## 1. Objective

Stand up the Zensical static site generator on homelab so the blog markdown becomes a proper website, served at `reports.home.arpa` over HTTPS via Caddy, with automatic rebuilds whenever the source markdown changes.

## 2. Background

The blog markdown previously lived as loose `*.md` files under `/srv/www/blog/public`. There was no build step and no clean URL structure. Zensical (pkgs.zensical, v0.0.43) builds a Material-style site from a `docs/` tree using a `zensical.toml` config. Caddy already terminates TLS for `*.home.arpa` using the Homelab Internal CA cert (`/etc/ssl/homelab/homelab.crt`).

## 3. Work Performed

### 3.1 Inspect Zensical build

Ran `nix run nixpkgs#zensical -- build -f` against a test project. Confirmed `docs_dir` (default `docs`) and `site_dir` (default `site`) are configurable; setting `site_dir = "reports"` made the build emit to `reports/`.

### 3.2 Move content and configure

- Moved 89 `*.md` files from `/srv/www/blog/public` to `/srv/www/codebot/docs`.
- Wrote `/srv/www/codebot/zensical.toml` with `docs_dir = "docs"` and `site_dir = "reports"`.
- Added a placeholder `docs/index.md` landing page.
- Ran the initial build; `/srv/www/codebot/reports` populated, including `index.html`.

### 3.3 nix-lab module

Created `common/web/codebot.nix` and wired it into `common/web/default.nix`:
- installs `pkgs.zensical`
- `systemd.services.zensical-build` (oneshot) runs `zensical build -f /srv/www/codebot/zensical.toml`
- `systemd.paths.zensical-build` watches `/srv/www/codebot/docs`
- Caddy vhost `reports.home.arpa` reuses `homelab.crt`

### 3.4 Switch and verify

Owner ran `sudo nixos-rebuild switch`. The system path unit came up active/enabled and was verified to auto-rebuild on a doc touch. The redundant user-level unit was disabled. `nix eval` confirmed the module was valid before the switch.

### 3.5 TLS debugging

The browser reported `ERR_CERT_COMMON_NAME_INVALID` for `reports.home.arpa`. Server-side inspection proved Caddy serves a valid cert (`CN=*.home.arpa`, SAN covers `*.home.arpa` and therefore `reports.home.arpa`). The real cause was the client resolver: the browser reached a different host than `192.168.1.3`. Added `reports.home.arpa` to `extraDomains` in `system/pki.nix` so the cert carries an explicit SAN (per repo convention for manually-referenced vhosts).

### 3.6 Polish

Added a Polish task list to `Pending--zensical.md`: fix 11 unresolved-link-reference warnings, improve the landing page, clean up leftover `/srv/www/blog/public`, commit staged nix-lab changes, optional theming.

## 4. Diagnosis

The `ERR_CERT_COMMON_NAME_INVALID` was not a missing SAN (the wildcard already covered the name) but a name mismatch from the browser connecting to the wrong endpoint. `nslookup` from WSL2 returned `192.168.1.3` (WSL2 forwards to homelab dnsmasq, which wildcards `*.home.arpa`), but the browser own resolver returned a different address.

## 5. Fix

- Added `reports.home.arpa` to `extraDomains` in `system/pki.nix` (staged, regenerates the cert on next switch with an explicit SAN).
- Client-side: ensure `reports.home.arpa` resolves to `192.168.1.3` on the machine running the browser (add to `hosts`, or point DNS at `192.168.1.3`).

## 6. Verification

After the DNS correction the site loads at `https://reports.home.arpa/`. Editing any file under `/srv/www/codebot/docs` triggers a successful rebuild via the systemd path unit.

## 7. Pending Actions

- Run `sudo nixos-rebuild switch` to apply the pki cert regen.
- Commit the staged nix-lab changes.
- Complete the Polish items.

## 8. Recommendations

- Keep `reports.home.arpa` in `extraDomains` whenever the Caddy vhost is a hand-written `virtualHosts` entry rather than an auto-generated `services.caddy.services` entry, so the cert SAN stays correct.
- For any new `*.home.arpa` service, verify the client resolver (not just the host) returns `192.168.1.3`, or TLS errors will look like cert problems when they are really DNS problems.
