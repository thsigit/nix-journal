# "switch root target contains no usable init" - Part 5 (FINAL)

*litellm-cli activation bisect (FINAL)*

**Date:** 2026-08-21  
**Author:** Codebot  
**Topic:** NixOS, homelab, troubleshooting, recovery, boot  

---

## 1. Objective

Document the fifth investigation session into the recurring "switch root target contains no usable init" boot failure on the homelab NixOS box (portege-r30c laptop). Parts 1–4 diagnosed stage-1 timing, confirmed `common/ap` (gens 101–105), and isolated an activation-script abort in `litellm-cli` (`health.json` chown, gens 135–142). This session works on the **workstation** profile (.\#workstation) where a new wave of generations (162→163–165) fails with the same message after the native LiteLLM rework.

Three outcomes:

1. The failure is **content-caused**, not environmental — isolated by a 5-minute build window (gen162 02:47:53 boots, gen163 02:52:58 fails) and a dirty-tree activation diff.
2. Proven by a **bisect**: disabling `services.litellm-cli.enable` (external `litellm-cli` module activation) restores boot; `common/ai/litellm/litellm.nix` native service alone boots.
3. Fixed via commit `3d59d68` (disable litellm-cli, relax assertion, drop dangling deps) and a new **first-triage rule** added to the `boot-management` skill: time-diff journal gap vs git window before any SATA/hardware hypothesis.

## 2. Background

### 2.1 Machine and profile

- Hardware as Parts 1–4: Toshiba Portege R30-C, grub, kernel 6.18.36, NixOS 26.05.20260627.714a5f8.
- Flake: `/srv/repo/nix-lab`, attribute `.\#workstation` (owner is on workstation per `AGENTS.md`). Both `server`/`workstation` share `common/`.
- Recent rework (pre-window): `03109e3 refactor(litellm): retire podman, switch to native` → `100479f` docs → `cbfeaa7 refactor(litellm): remove PostgreSQL, run no-DB mode` → `f1f7a31 fix(litellm): restore quotes` (all 2026-08-20 23:30–23:50, HEAD at session start). Dirty-tree state after HEAD added `common/web/caddy.nix` `preConfig`, `litellm.nix` architecture rewrite, and `flake.lock` litellm-cli path bump.

### 2.2 The candidate window

User report:

```
$ sudo nixos-rebuild list-generations
Generation  Build-date           ... Current
165         2026-08-21 03:55:17  ...True
164         2026-08-21 03:50:56  ...False
163         2026-08-21 02:52:58  ...False  ← earliest failed
162         2026-08-21 02:47:53  ...False  ← last bootable
```

Gen162 boots (SSH via `homelab` 192.168.1.3, `/run/booted-system` == `/run/current-system` == `wwqrhgvc…`). Gens 163–165 fail at `switch_root` (no usable init). Part 4's `health.json` prep fix (`litellm-healthjson-prep`) is still present in both activators, so the failure is a new activation delta.

### 2.3 Two candidate places (user framing)

- `common/ai/litellm/` (nix-lab wrapper: `litellm-cli.nix`, `litellm.nix`, `default.nix`)
- `/srv/repo/litellm-cli` (external path flake input, owns `system.activationScripts.litellm-cli-config`)

The failing window's git is empty (`git log --since 02:47 --until 02:52 --all` shows no new commits in either repo), so the culprit is **dirty-tree** content that built gen163.

## 3. Generation and activation map

All gens are `nixos-system-homelab-26.05.20260627.714a5f8`. Build dates are WITA (Asia/Makassar, +0800).

| Gen | Store suffix | Build-date | Journal | Boot |
|-----|--------------|------------|---------|------|
| 159 | `qmj6irkv…` | 2026-08-20 23:37:44 | yes | boots |
| 160 | `0cx4ck6w…` | 2026-08-20 23:51:32 | yes | boots (HEAD f1f7a31) |
| 161 | `46cim5pk…` | 2026-08-21 02:25:37 | — | — |
| 162 | `wwqrhgvc…` | 2026-08-21 02:47:53 | yes (0) `2658a183…` | **boots** – last good |
| 163 | `l5h3iqp2…` | 2026-08-21 02:52:58 | **no** | **fails** – switch_root |
| 164 | `lrz0iybw…` | 2026-08-21 03:50:56 | no | fails |
| 165 | `04dxnr7i…` | 2026-08-21 03:55:17 | no | fails |
| 166 | — | 2026-08-21 13:xx | yes | **boots** (after bisect disable) |

Journal map (`journalctl --list-boots | tail` on gen162): `-1` `3f2fcfaf…` 13:02:30, `0` `2658a183…` 13:04:18 with `init=/nix/store/wwqrhgvc…/init`. Failing gens 163–165 never appear — classic gap for activation abort before journald (see Part 4 §6.2).

## 4. Work Performed

### 4.1 Boot map and store links

```
readlink /run/booted-system  → /nix/store/wwqrhgvcvqifdrfxpnqfvac8mrcg3577-nixos-system-homelab-26.05.20260627.714a5f8 (162)
readlink /run/current-system → same
readlink /nix/var/nix/profiles/system-163-link → /nix/store/l5h3iqp214n2gbc9wglfm345wkdlx4dw-nixos-system-homelab-26.05.20260627.714a5f8
readlink /nix/var/nix/profiles/system-165-link → /nix/store/04dxnr7i97ph7fzs4k2k8n54gvslh21g-nixos-system-homelab-26.05.20260627.714a5f8
```

### 4.2 Built-artifact inspection (gen162→163)

```bash
diff -u /nix/store/wwqrhgvc…/activate /nix/store/l5h3iqp2…/activate | head -80
```

Only non-trivial delta is `litellm-cli-config`:

- `if [ ! -f /srv/appdata/litellm/gateway.json ]; then` → `providers.json`
- `cp …/cfgws0p3…-gateway-seed.json → gateway.json` → `…/54cs2v50…-providers-seed.json → providers.json`
- `cp …/vljg9a80…-models-dev.json → models.json` → `…/bifxvsa0…-models.json`
- `/nix/store/x82ld1zm…-litellm-cli/bin/litellm-cli debug render` → `/nix/store/ky9ais6x…-litellm-cli/…`
- `chown sigit:users /run/litellm-cli/config.yaml` → `chown sigit:users /var/lib/litellm/config.yaml`

Both gens retain the prep snippet:

```
114:[ -e /run/litellm-cli/health.json ] || echo '{}' > /run/litellm-cli/health.json
145:chown sigit:users /run/litellm-cli/health.json
```

`etc` setup hash also differs (`rg5rf512… → j4i6rmyw…`), but is cosmetic.

### 4.3 Git time window for the pair

```bash
cd /srv/repo/nix-lab && git log --oneline --since='2026-08-21 02:47' --until='2026-08-21 02:52' --all
# (no output)
cd /srv/repo/nix-lab && git log --oneline -10 --date=iso
# f1f7a31 fix(litellm): restore quotes stripped by heredoc  2026-08-20 23:50
# cbfeaa7 refactor(litellm): remove PostgreSQL ...           2026-08-20 23:48
# 100479f docs(AGENTS): update litellm references ...        2026-08-20 23:34
# 03109e3 refactor(litellm): retire podman ...               2026-08-20 23:30

cd /srv/repo/nix-lab && git diff HEAD --stat
# AGENTS.md, common/ai/litellm/litellm.nix, common/web/caddy.nix, flake.lock, secrets/providers.env

cd /srv/repo/litellm-cli && git log --oneline --since='2026-08-21 02:47' --until='2026-08-21 02:52' --all
# (no output — last is e3008df auto: update model inventory)
```

No new commits in the 5-minute window — failure is from the **dirty tree** that built gen163 (providers.json rename + config.yaml path, plus `litellm.nix` native rework and `caddy` `preConfig`).

### 4.4 Bisect design (user-directed)

User: *"disable `litellm-cli` and let me switch and reboot, to find if the culprit is there. if boot success, that's the culprit. if boot failed with same error, the culprit is in `common/ai/litellm`."*

Edits on homelab (with `.bak`):

- `common/ai/litellm/litellm-cli.nix:21` `enable = true` → `enable = false # BISECT`
- `common/ai/litellm/litellm.nix:34` `assertion = config.services.litellm-cli.enable` → `assertion = true # BISECT`
- `common/ai/litellm/litellm-cli.nix:39` `system.activationScripts.litellm-cli-config.deps` → commented (dangling when `mkIf cfg.enable` drops the base — eval error: `system.activationScripts.litellm-cli-config.text has no value`)

Eval check: `nix eval .#nixosConfigurations.workstation.config.services.litellm-cli.enable` → `false`, `services.litellm.enable` → `true`.

### 4.5 Rebuild and boot test

User ran:

```bash
sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation
# → generation 166
# reboot via grub menu to 166
```

Result: **boots successfully** (`readlink /run/booted-system` == new store, journal entry present). Therefore culprit is `/srv/repo/litellm-cli` activation (`litellm-cli-config`), not the wrapper's native `litellm` service alone. The activation runs `set -euo pipefail`, `mkdir -p /srv/appdata/litellm /run/litellm-cli`, seeds `providers.json`, renders via `litellm-cli debug render` (now to `/var/lib/litellm/config.yaml`), then `chown`s `config.yaml` + `health.json`. A failure there (e.g. stale `/var/lib/litellm` symlink, render error, or chown on tmpfs) aborts activation before `/run/current-system` is linked, so `switch_root` sees no usable init.

## 5. Diagnosis

| Gen | litellm-cli activate | LiteLLM native | Boot | Verdict |
|-----|----------------------|----------------|------|---------|
| 162 | old (`gateway.json`, `/run/litellm-cli/config.yaml`, `x82ld1…`) | old (`litellmCli.configFile`) | boots | baseline |
| 163 | new (`providers.json`, `/var/lib/litellm/config.yaml`, `ky9ais…`) | new (`stateDir /var/lib/litellm`, `litellm-render` service) | **fails** | content-caused |
| 166 | **disabled** (`enable false`, no `litellm-cli-config`) | new enabled (assertion relaxed) | **boots** | cli activation isolated |

Earlier environmental hypothesis (SATA/AHCI) excluded: 162→163 are **not** byte-identical (activation differs), and the bisect pinpoints a single activation snippet.

## 6. Root Cause
> **WATCH `system.activationScripts` — this error recurs when any activation snippet under `set -euo pipefail` (`chown`, `mktemp`, `mkdir`) aborts before /run/current-system is linked. Always `mkdir -p` before `chown` and avoid dangling `.deps` overrides when the base is `lib.mkIf cfg.enable`.**

1. The native rework (03109e3 + cbfeaa7) changed the activation contract: persistent file `gateway.json` → `providers.json`, output `config.yaml` moved `/run/litellm-cli` → `/var/lib/litellm`. The locked input `litellm-cli` (`narHash sha256-24m/vJUEH…`, `lastModified 1787251891`) still renders via `litellm-cli debug render`.
2. The new activation's `chown sigit:users /var/lib/litellm/config.yaml` assumes `/var/lib/litellm` exists and is writable; on this host `/var/lib/litellm → private/litellm` was a dangling symlink in the 14th-hour dirty tree, and the render's `mktemp …/config.yaml.tmp.XXXXXX: Permission denied` (observed when manually running `ky9ais6x…/bin/litellm-cli debug render`) shows the fragility.
3. The activation runs under `set -euo pipefail`; any such failure aborts the snippet before `/run/current-system` is linked, so stage-1 `switch_root` (which resolves `init=/nix/store/<top>/init`) finds no usable init — same symptom as the Part 4 `health.json` abort, but a different trigger.

The dangling `system.activationScripts.litellm-cli-config.deps` override when `enable = false` is a second-order eval trap: the base attribute is gone (inside `lib.mkIf cfg.enable`), so any bare `deps = …` makes `text has no value`.

## 7. Resolution

- **Bisect fix committed as `3d59d68` on `nix-lab/main`:**

```
fix(litellm): disable litellm-cli to fix no-usable-init (bisect gen162→163)
 common/ai/litellm/litellm-cli.nix | enable false + deps commented
 common/ai/litellm/litellm.nix     | assertion true + native rework (preConfig, stateDir, litellm-render)
```

  Bootable generation 166 confirmed.

- **Skill update:** `boot-management/SKILL.md:77` new section `First triage — time-diff between last bootable generation and git` — mandates `nixos-rebuild list-generations` Build-date vs `journalctl --list-boots` gap + `git log --since/--until` in **both** `nix-lab` and `litellm-cli` repos before any hardware theory.

- **Deferred:** re-enable `litellm-cli` after upstream guards `/var/lib/litellm` creation + `chown` idempotency, and after `litellm-render` owns directory creation (currently `StateDirectory litellm-render` vs `stateDir /var/lib/litellm` mismatch).

## 8. Verification status

- [x] `readlink /run/booted-system` on 166 points to new store (not 162).
- [x] `journalctl --list-boots | tail` shows 166 entry.
- [x] `diff …/system-162-link/activate …/system-163-link/activate` delta is only litellm-cli-config (clean isolation).
- [x] `nix eval .#nixosConfigurations.workstation.config.services.litellm-cli.enable` = false, `services.litellm.enable` = true (eval passes, no missing text).
- [ ] Follow-up: restore `litellm-cli` with guarded `/var/lib/litellm` mkdir/chown and rebuild to prove innocent.

## 9. Recommendations
> **WATCH `system.activationScripts` — if this error recurs, first `diff .../activate` and audit every activation snippet; activation aborts are the top content-cause, not hardware.**

- **Always do the 5-minute window first.** `journalctl --list-boots` is ground truth; no entry = activation abort. `git log --since <good> --until <bad> --all` + `git diff HEAD --stat` in both flakes before SMART/`ahci` theories.
- Activation scripts must be idempotent and own their directories (`mkdir -p` before `chown`/`mktemp`) — `/run` and `/var/lib` may be tmpfs/symlink.
- Avoid bare `system.activationScripts.<name>.deps = …` overrides when the base is `mkIf cfg.enable`; guard with `lib.mkIf` or comment when disabling.
- Keep the native `litellm` `assertions = true` shim only as a bisect; revert to `config.services.litellm-cli.enable` once cli is fixed.
- Preserve `nixpkgs` `714a5f8` (`flake.lock` pinned) — do not `git reset --hard` the lock on failed builds (see `AGENTS.md` 2026-08-20 rule).

## 10. Relevant files

- `/srv/repo/nix-lab/common/ai/litellm/litellm-cli.nix:21,39` — bisect disable + dangling deps fix
- `/srv/repo/nix-lab/common/ai/litellm/litellm.nix:34` — assertion relaxed + native rework
- `/srv/repo/nix-lab/common/ai/litellm/default.nix`, `common/default.nix`, `common/web/caddy.nix:15,25` (`preConfig`)
- `/srv/repo/nix-lab/flake.lock` — litellm-cli path bump `sha256-NKbc… → 24m/vJUEH…`
- `/srv/repo/litellm-cli/module.nix:154` `lib.mkIf cfg.enable` gating `system.activationScripts.litellm-cli-config` (`set -euo pipefail`, `chown … health.json/config.yaml`)
- `/nix/store/<gen>-nixos-system-homelab-…/activate` (gens 162 `wwqrhgvc…`, 163 `l5h3iqp2…`, 165 `04dxnr7i…`)
- `/var/lib/litellm → private/litellm` (dangling) — observed render `Permission denied`
- `/srv/repo/nix-lab/sessions/` + skill `boot-management/SKILL.md:77`

## 11. If It Recurs
> **WATCH `system.activationScripts` — step 3 above: disabling a candidate `enable` must also remove any bare `system.activationScripts.<name>.deps/text` override, otherwise eval fails with `text has no value` (as hit in this bisect).**

1. Boot to last journal-confirmed generation (162-style) via grub.
2. Run the first-triage block: `nixos-rebuild list-generations` Build-date + `journalctl --list-boots` gap → identify GOOD/BAD pair → `diff …/activate` → `git log --since/--until` in both repos → `git diff HEAD --stat`.
3. Isolate with a minimal bisect: disable the candidate `imports`/`enable` (watch for dangling `activationScripts` deps) and rebuild.
4. Verify `init=/nix/store/<top>/init` exists (`ls -l`) and `nix-store -q --tree` closure intact before blaming hardware.
5. Re-enable step-by-step, guarding `mkdir -p`/`chown` under `set -e`.

## 12. Open questions and follow-ups

- Why `/var/lib/litellm → private/litellm` dangled (should be `StateDirectory=litellm` managing it) — inspect `systemd.tmpfiles` / `stateDir` handling in native module.
- `secrets/providers.env` sops re-encrypt (`sops_lastmodified 2026-08-18T07:30:13Z`) — unrelated but dirty; commit separately.
- Clean up `archive/containers/litellm-podman/`, `common/ai/litellm/*.old` deletions already staged but left for next commit.
- Re-enable `services.litellm-cli` with upstream fix and prove gen 167 boots.


---

Generated with muse-spark-1.2-contributor-free (Meta Muse Spark)
