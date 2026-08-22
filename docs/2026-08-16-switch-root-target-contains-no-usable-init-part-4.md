# "switch root target contains no usable init" - Part 4

*Workstation wave (gens 136-142)*

**Date:** 2026-08-16  
**Author:** Codebot  
**Topic:** NixOS, homelab, troubleshooting, recovery, boot  

---

## 1. Objective

Document the fourth investigation session into the recurring "switch root target contains no usable init" boot failure on the homelab NixOS box (portege-r30c laptop). Parts 1-3 (2026-08-10/11/12, profile `.#server`) diagnosed a stage-1 timing race and confirmed the `common/ap` bundle as a trigger (gens 101-105). This session works on the **workstation** profile (`.#workstation`, hostname `homelab`), where a new wave of generations (136-139, 141) fails with the same message.

Three outcomes:

1. The failure is an **activation-script abort**, not a stage-1 timing issue. The litellm-cli module's unguarded `chown ... health.json` on a fresh tmpfs state dir aborts `/nix/store/<gen>/activate` before the stage-2 handoff, so switch_root finds no usable init.
2. Proven by a **warm-boot A/B on the hardware**: gen141 (bare chown) fails; gen142 (prep snippet) boots. The only delta between the two `activate` scripts is the prep snippet.
3. Fixed in nix-lab via an activation prep script, **without re-locking** the litellm-cli input (the locked source is unguarded, and re-locking to HEAD would break nix-lab eval because HEAD dropped `dataDir`).

## 2. Background

### 2.1 Machine and profile

- Hardware as Parts 1-3: Toshiba Portege R30-C, systemd-boot, kernel 6.18.36, NixOS 26.05.20260627.714a5f8.
- Flake: `/srv/repo/nix-lab`, attribute `.#workstation` (this session), not `.#server`. Both import `../../common`.
- litellm-cli was decoupled into its own flake repo (see `2026-08-13-litellm-cli-decouple.md`) and is pinned as a `path` flake input in nix-lab's `flake.lock`.

### 2.2 The litellm-cli module and its activation script

The module defines `system.activationScripts.litellm-cli-config`, which runs under `set -euo pipefail` and ends with:

```bash
if [ ! -f ${cfg.stateDir}/health.json ]; then
  echo '{}' > ${cfg.stateDir}/health.json
fi
chown ${cfg.user}:${cfg.group} ${cfg.stateDir}/health.json
```

- `stateDir` defaults to `/run/litellm-cli` (a tmpfs) - **empty on every boot**.
- `health.json` is only created by the `doctor` subcommand on first run, so on a fresh boot it does **not** exist.
- The **locked** source (build input) contains the **unguarded** version of the above (bare `chown`, no creation guard). On a fresh boot the `chown` fails (`set -e` aborts the snippet) before `/run/current-system` is created.

### 2.3 The stale-lock wrinkle

- The locked input (narHash `sha256-vhd0u3K66voVeNEzS7e18nplJK2xhtvesJxmxnZ4tRw=`, recorded 2026-08-15) is what builds actually use.
- It exposes `services.litellm-cli.dataDir` but **not** `stateDir` (verified: `nix eval .#nixosConfigurations.workstation.config.services.litellm-cli.dataDir` works; `.stateDir` does not exist).
- The worktree HEAD (`e50d2b2`) did the opposite: it introduced `stateDir` and **dropped `dataDir`**, so re-locking the input would break nix-lab's eval (nix-lab references `dataDir`). Hence the fix had to be made in nix-lab, against the locked interface.

## 3. Generation and activation map

All gens are `nixos-system-homelab-26.05.20260627.714a5f8`. "Guard" = the health.json creation guard present in the **built** `activate` script (grep of the store artifact, not the source).

| Gen | System store path suffix | LiteLLM in built activate | Boot result |
|-----|--------------------------|---------------------------|-------------|
| 135 | `p9gpp8k6qhqppnq4arfpi7qq5lkkh78a` | guarded | boots (known-good at session start) |
| 136 | `1akjzmhrwg8brj66ajw1zd7wzj3x0qql` | guarded - **identical** to 135 | reported fail (no journal; anomaly, see 6.2) |
| 137 | `j69nh9v5mqn1nhq9p1878008xl4wxkm5` | bare chown (no guard) | reported fail |
| 138 | `mwz3qcjiwpcz5ll46s7vpb4275biyxq7` | not inspected | reported fail |
| 139 | `37hvra9mpl0drl3lkr8k7814f9h0f0fn` | bare chown (no guard) | reported fail |
| 140 | `zq5qabchnp3k4vxgdag1pwh9jz5ijhl4` | no LiteLLM modules (all 3 disabled) | boots |
| 141 | `8mz1id7l3vi24dir9813vrywypiazpjf` | bare chown (no guard) | **FAILS** (warm boot, directly observed) |
| 142 | `fn0wwrw97s4rid84rjc9fn0c0l1f8gp6` | bare chown + nix-lab prep snippet | **boots** (current) |

Journal boot map (`journalctl --list-boots`): `-7`=gen129, `-6`=gen130, `-5`=gen132, `-4`=gen135, `-3`=gen135, `-2`=gen140, `-1`=gen140, `0`=gen142. **Failing gens (136-139, 141) never appear in the journal** - they die at the switch-root handoff, before stage 2 can log. An empty journal gap for a generation is itself evidence of this failure mode.

## 4. Work Performed

### 4.1 Boot map and boot-entry timing

Boot `cmdline` (`init=/nix/store/<suffix>/init`) was read from each journal boot to identify which generation actually booted. Boot entries `nixos-generation-135.conf` .. `142.conf` all have mtime `2026-08-16 13:36:22` - they were all (re)written by the successful 13:36 switch. Consequence: during boot `-1` (13:17-13:46) `nixos-generation-141.conf` did **not** exist yet, so the "gen141 test" reboot at 13:17 actually booted gen140. Gen141 was first genuinely booted in the decisive A/B (4.6).

### 4.2 Built-artifact inspection

The ground truth is the built `activate`, not the source. `grep -n "health.json" /nix/store/<gen>-.../activate` across gens showed:

- gen135: guard present (lines 136-141).
- gen136: guard present, LiteLLM lines **identical** to gen135 (verified with `diff`).
- gen137/139: bare `chown sigit:users /run/litellm-cli/health.json`, no guard.
- gen142: bare chown (line 145) plus the new nix-lab prep snippet (line 114).

### 4.3 sudo/rebuild mechanics

`sudo -n nixos-rebuild ...` requires a password (a specific `sudoers` rule for the `nixos-rebuild` path), but `NOPASSWD: ALL` covers bash:

```text
User sigit may run the following commands on homelab:
    (ALL : ALL) SETENV: ALL
    (ALL : ALL) NOPASSWD: ALL
    (ALL : ALL) /run/current-system/sw/bin/nixos-rebuild
```

Working form: `sudo -n bash -c 'cd /srv/repo/nix-lab && nixos-rebuild switch --flake "/srv/repo/nix-lab#workstation"'`.

### 4.4 The 13:22 failed switch vs the 13:36 successful switch

- 13:22 (as `sigit`): build **succeeded** (gen142 store path exists), but `nix-env --set` failed: `Permission denied creating /nix/var/nix/profiles/system-142-link.tmp`. No generation was registered. The machine kept running gen140 throughout - **a failed switch does not kill the running system**.
- 13:36 (as root via `sudo bash -c`): **success**. gen142 registered (13:36:21), activated cleanly with health.json pre-created (`litellm-cli render: wrote /run/litellm-cli/config.yaml with 108 models, 4 aliases, 1 fallbacks`), boot entries written (13:36:22).

### 4.5 The gen141 warm-boot A/B (decisive)

- Set the boot default to gen141: `bootctl set-default nixos-generation-141.conf` and wrote `loader.conf` with `default nixos-generation-141.conf`, `timeout 10`.
- Warm reboot: **"switch root target contains no usable init"** (operator-confirmed on the console).
- Recovered: `bootctl set-default nixos-generation-142.conf`; `loader.conf` back to `timeout 3`, default 142. Current state verified: gen142 is `system-142-link`, marked `(default) (selected)`.
- `diff` of the gen141 vs gen142 `activate` scripts shows the **only** change is the added `litellm-healthjson-prep` snippet - a clean A/B isolating the prep snippet as the difference between fail and boot.

### 4.6 The fix

In nix-lab `common/ai/litellm-cli.nix`:

```nix
system.activationScripts.litellm-healthjson-prep = {
  deps = [ "users" ];
  text = ''
    mkdir -p /run/litellm-cli
    [ -e /run/litellm-cli/health.json ] || echo '{}' > /run/litellm-cli/health.json
  '';
};
system.activationScripts.litellm-cli-config.deps = [ "users" "litellm-healthjson-prep" ];
```

Notes:

- `deps` (not `stringAfter`) because NixOS `system.activationScripts` supports only `deps`/`text`/`supportsDryActivation`. Ordering matters: `textClosureList` walks entries alphabetically, and `litellm-cli-config` < `litellm-healthjson-prep`, so without the explicit dep the prep would run **after** the module snippet.
- `/run/litellm-cli` is hardcoded because the locked module does not expose `stateDir` to nix-lab (section 2.3). It matches the locked module's internal default.
- The guard was also restored in the worktree `/srv/repo/litellm-cli/module.nix` (uncommitted, ` M module.nix`); it is inert until the input is re-locked, which is deliberately not done (section 2.3).

## 5. Diagnosis

| Gen | guard in built activate | LiteLLM modules | boot result | verdict |
|-----|--------------------------|-----------------|-------------|---------|
| 135 | yes | on | boots | baseline |
| 136 | yes (== 135) | on | reported fail | unexplained by chown |
| 137/139 | no | on | reported fail | consistent with chown abort |
| 140 | n/a | off | boots | consistent |
| 141 | no | on | **fails (A/B)** | chown abort |
| 142 | prep snippet | on | **boots (A/B)** | chown abort fixed |

The directly-observed A/B (141 vs 142) is the strong evidence; the earlier 136-139 reports were from a bisect whose switch-time console errors were easy to conflate with boot failures (see 6.2).

## 6. Root Cause

### 6.1 The causal chain (settled by the A/B)

1. `/run/litellm-cli` is a tmpfs, empty on every boot; `health.json` does not exist.
2. The locked module's `litellm-cli-config` activation snippet runs under `set -euo pipefail` and performs an unguarded `chown sigit:users /run/litellm-cli/health.json`. The `chown` fails, the snippet aborts.
3. The abort happens before the final activation step that completes the stage-2 handoff (`/run/current-system`). switch_root's init resolution depends on that completed handoff; with it missing, switch_root reports "switch root target contains no usable init".
4. Direct observation: gen141 (bare chown) fails to boot warm; gen142 (prep snippet) boots. The activate diff is only the prep snippet.

### 6.2 Why the intermediate code trace misled (and the gen136 anomaly)

Mid-session the code was re-traced: `prepare-root` runs `$systemConfig/activate` but has no `set -e`, and the init path is passed explicitly (`init=/nix/store/<top>/init`, a hardlink that always exists) - so it *looked* like a script failure could not block switch_root. This doubt was settled empirically: the gen141 warm-boot test fails, gen142 boots. Direct observation overrides the incomplete code trace.

The gen136 anomaly stands: its built `activate` is byte-identical to gen135's in every LiteLLM line (both guarded), yet the earlier bisect reported it failing. Two honest readings, both unresolved: (a) it was a misattribution - a switch-time chown error on the console was mistaken for a boot failure (a real conflation risk this session exposed, since `Failed to run activate script` is a nixos-rebuild console message, present in **zero** journal boots), or (b) it failed for a different, unexamined reason. It was never booted during a journaled window either way.

### 6.3 What "Failed to run activate script" is

It is a **switch-time console message from nixos-rebuild**, not a boot-time event, and it does **not** imply the running system is failing: boot `-1` (gen140) ran for 29 minutes *through* the failed 13:22 switch. The failing generations themselves never show it in the journal because they die at switch-root, before journaling begins.

## 7. Resolution

1. nix-lab prep script (section 4.6) - makes the activation robust regardless of the pinned module content. Done.
2. Upstream guard restored in `/srv/repo/litellm-cli/module.nix` worktree - committed there, inert until the nix-lab lock is refreshed, which is deferred because HEAD dropped `dataDir`. Done locally.
3. gen142 built and booted; it is the current generation and the boot default. Verified post-recovery: `system-142-link` -> `fn0wwrw97...`, loader.conf default 142, bootctl shows `(default) (selected)`.
4. The boot journal of gen142 is clean (no activation failure); `is-system-running` is `degraded` only due to the pre-existing, unrelated `mrtg.service`.

## 8. Verification status

- A/B complete: gen141 fails warm, gen142 boots warm; activate delta is only the prep snippet (diff shown in 4.5).
- Built-artifact greps match the guard model for gens 135/137/139/141/142 (gen138 not inspected).
- Remaining follow-ups: re-enable `common/ai/litellm-podman-helper.nix` (disabled during the bisect; believed innocent - it is a `systemd.path` watcher with no activation snippet) and rebuild to prove it was not a co-factor; move the hardcoded `DATABASE_URL` password in `common/ai/litellm-podman.nix:124` into a sops-managed `litellm.env`; commit the nix-lab fix and the upstream guard.

## 9. Recommendations

- Activation scripts must be idempotent and guarded against fresh-tmpfs state. Any file the script creates/chowns must be created before the chown. `stateDir` on a tmpfs is empty on every boot by design.
- Inspect the **built artifact**, not the source. The pinned input differs from the worktree; the `activate` in the store is the only ground truth.
- Do not conflate switch-time errors with boot failures. `Failed to run activate script` at `nixos-rebuild` time does not affect the running system.
- A generation that leaves no journal entry died before stage 2 (i.e. at switch_root). An empty journal gap is evidence of this failure mode, not of a non-booted generation.
- Order activation scripts with `deps`, not `stringAfter`; only `deps`/`text`/`supportsDryActivation` are supported.
- A/B test an exact generation with `bootctl set-default <gen>.conf` plus `loader.conf`; keep a known-good fallback selected before rebooting.

## 10. Relevant files

- `/srv/repo/nix-lab/common/ai/litellm-cli.nix` - the prep fix (activation script + `deps`).
- `/srv/repo/nix-lab/common/ai/default.nix` - `litellm-podman-helper.nix` disabled during bisect.
- `/srv/repo/litellm-cli/module.nix:176` - unguarded `chown ... health.json` in the locked source; guard restored in worktree.
- `/srv/repo/nix-lab/flake.lock` - pinned litellm-cli input (narHash `sha256-vhd0u3K...`, recorded 2026-08-15).
- `/srv/repo/nix-lab/common/ai/litellm-podman.nix:124` - hardcoded `DATABASE_URL` (follow-up).
- `/boot/loader/loader.conf` + `/boot/loader/entries/nixos-generation-14{1,2}.conf` - boot default management.
- `$GENERATION/activate` in `/nix/store/<suffix>-nixos-system-homelab-26.05.20260627.714a5f8/` for each gen - the built-artifact evidence.

## 11. If It Recurs

1. Recover first: from the systemd-boot menu boot a known-good generation (gen142-style, or gen140 = LiteLLM off). The box becomes reachable and diagnosis proceeds safely.
2. Check the boot default actually matches intent: all boot entries get rewritten on every switch (mtime 13:36:22 for the entire 135-142 range here), so an old `loader.conf` default can silently point at a stale generation.
3. Locate the failing generation and inspect its **built** activate: `grep -n "health.json" $GEN/activate`. A bare `chown` without a preceding creation guard on a tmpfs `stateDir` is the signature of this failure class.
4. Classify from the journal: if the generation has no journal boot entry, it died at switch_root - an activation/handoff problem, not stage-1 device timing.
5. Prefer a nix-lab-side prep script over re-locking a `path` input whose locked interface your config depends on (`dataDir` here). Re-lock only when the input HEAD is compatible.

## 12. Open questions and follow-ups

- Re-enable `litellm-podman-helper.nix` and rebuild: does gen142-with-helper still boot? (Expected: yes; it is a `systemd.path` watcher, no activation snippet.)
- Gen136 anomaly (6.2): misattribution or independent failure? A re-boot of a rebuilt 136-equivalent generation would settle it.
- Move the hardcoded `DATABASE_URL` password into sops `litellm.env`.
- Commit: nix-lab `common/ai/litellm-cli.nix` + `common/ai/default.nix`, and the guard in `/srv/repo/litellm-cli/module.nix`.
