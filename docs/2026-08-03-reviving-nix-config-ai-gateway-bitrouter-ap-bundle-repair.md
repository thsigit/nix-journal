# Reviving Nix Config AI Gateway BitRouter Ap Bundle Repair

**Date:** 2026-08-03  
**Author:** Codebot  
**Topic:** NixOS, homelab, openNDS, BitRouter, LiteLLM, captive-portal, refactor, recovery  

---

## 1. Objective

Migrate active repo from archived /srv/repo/nix-lab to /srv/repo/nix-config (branch main), adopt organized AI module tree, revive BitRouter, repair regressed AP bundle.

## 2. Background

/srv/repo/nix-lab now archived reference. /srv/repo/nix-config (main) is active working repo. Archived gateway-service-refactor (nix-lab, 2026-08-01) proposed modules/gateways/ with services.aiGateway.enable / services.internetGateway.enable flags. On inspection: internet gateway refactor DONE in nix-config (modules/network/ap/ + services.ap.enable toggle, commits f997ab7, 0cb7bf6, 02ee9a6); BitRouter didn't exist in nix-config; modules/ai tree flat and mixed, nix-lab copy organized.

## 3. Problem

Selective port needed: adopt organized modules/ai, revive BitRouter, fix AP bundle regressions from working nix-lab reference.

## 4. Work Performed

### 4.1 Task 1: Adopt Organized modules/ai
/srv/repo/nix-lab/modules/ai -> /srv/repo/nix-config/modules/ai. Shared files byte-identical. nix-lab added:
- litellm-podman/ : gateway as self-contained dir (podman.nix runtime container + config.nix inventory/policy + renderer)
- bitrouter/ : settings/container/service/package
- cleaner default.nix (comment-in/out per service)

Removed flat podman-litellm.nix, litellm-config.nix, providers.json.new, doc stubs. Two package dependencies ported: pkgs/litellm-cli/default.nix (adds user/group params + exposes modelsJsonPath) and litellm-render fix (database_url disabled -- SQLite rejected by LiteLLM v1.92.0, crash-loops container).

### 4.2 Task 2: Revive BitRouter
BitRouter = second AI gateway (container mode, port 4356), OpenAI/Anthropic/Gemini-compatible router. Verified:
- Module tree evaluates: services.bitrouter.enable = true, mode = "container"
- Caddy vhosts generated: bitrouter.home.arpa + bitrouter.basa-komodo.ts.net (lan + Tailscale visibility)
- providers.env (sops) wired as environmentFiles
- Package builds cleanly from pinned v1.0.0-alpha.27 release tarball via autoPatchelfHook

### 4.3 Task 3: Repair AP Bundle
nix-config AP bundle regressed from working nix-lab implementation. Diffing each modules/network/ap/*.nix against nix-lab originals surfaced five regressions:

1. opennds.nix: nix-config ran Type="forking" with openNDS -b (background) and setupScript symlinking into /usr/local/bin. NixOS has no /usr/local/bin -- aborted activation. Hardcoded faskey 1234567890. Fix: Type="exec" + openNDS -f (foreground, systemd tracks directly), faskey appended at activation from sops secret, resources copied once in activation script (not every service start), /usr/local/bin symlinks removed.

2. openNDS package: wrapper for ndsctl only put coreutils on PATH; C binary shell-script deps (gawk, gnugrep, procps, iptables, nftables, curl) not visible. Fix: adopt nix-lab layout -- unwrapped binaries in libexec, PATH-complete wrappers in bin, libmicrohttpd as build-time-only nativeBuildInput.

3. hostapd.nix: auth_server_shared_secret = "testing123" baked into store. Fix: drop from settings, use dynamicConfigScripts.eapSecret to append sops radius-secret at runtime. Kept nix-config improvements: network-addresses-${ap} multi-user.target pull and rfkill-unblock ordering.

4. freeradius.nix: secret + user password hardcoded; EAP certs generated at BUILD TIME (private key world-readable in /nix/store). Fix: sops secrets (radius-secret, radius-users), certs generated at activation into /srv/appdata/freeradius/certs owned by radius, runtime clients.conf/users seeded in preStart wrapped in lib.mkBefore.

5. router.nix: NAT flushed SHARED nixos-nat-pre/nixos-nat-post chains, destroying rules from other modules. Fix: dedicated opennds-pre/opennds-post chains, flushing only ours.

Plus missing plumbing: secrets/opennds.yaml (faskey) and secrets/radius.yaml (radius-secret + radius-users) copied from nix-lab, registered in modules/security/sops.nix. All decrypt cleanly.

### 4.4 Verification
- nix flake check passes for homelab, workstation, failsafe
- Targeted eval: services.ap.enable, openNDS, hostapd, FreeRADIUS all true; faskey secret resolves to /run/secrets/opennds-faskey
- BitRouter eval + package build OK; openNDS package build OK
- Tested toggle scenarios: removing ./ap from network/default.nix still builds (only AP services vanish); removing dnsmasq.nix builds but silently kills guest DHCP (openNDS reads dnsmasq.leases) and LAN *.home.arpa DNS

### 4.5 dnsmasq vs udhcpd Discussion
Side discussion: swap dnsmasq for udhcpd? udhcpd = DHCP server (needed for AP); udhcpc = DHCP client (irrelevant). udhcpd fits AP role (one range, router/DNS, option 114) but drops DNS entirely (dnsmasq resolves *.home.arpa), different lease file/format openNDS dhcpcheck parser may not read, no native NixOS module, weaker force semantics for option 114. Verdict: not obviously a win; openNDS-lease-format integration test deciding factor.

## 5. Diagnosis

AP bundle had five regressions from known-working reference. BitRouter missing. AI module organization superior in nix-lab.

## 6. Preliminary Assessment

Selective port complete. Regressions fixed. BitRouter revived. Config evaluates cleanly.

## 7. Solution Summary

Ported organized AI modules. Revived BitRouter with container mode. Fixed five AP bundle regressions. Verified eval and package builds.

## 8. Verification Plan

Owner runs sudo nixos-rebuild switch, tests reboot + guest splash. If splash fails, resume debug note discriminator tests (plain-unicast ping/nc to guest STA vs fwmark trap vs netns isolation). systemPackages cleanup in modules/ai deferred.

## 9. Pending Actions

Rebuild and live test. Debug note resumption if needed.

## 10. Recommendations

Diff against known-working reference for regressions. Make secrets runtime-injected, not build-time. Use dedicated nftables chains per module to avoid cross-module interference.
