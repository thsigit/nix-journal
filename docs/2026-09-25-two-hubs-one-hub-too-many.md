# DebianWSL Reset and the Canonical V2 Hub (or: Two Hubs Was One Hub Too Many)

**Date:** 2026-09-25  
**Author:** Codebot  
**Topic:** wsl-reset, debianwsl, opencode-v2, hub-consolidation, bootstrap, managed-service-port, manual-auth

---

## 1. Objective (or: Reset Debian, Fix Everything Around It)

Reset DebianWSL to a clean Debian 13 with OpenCode v2, the same dance the Fedora
reset series performed (see `2026-09-21-fedora-wsl-reset-opencode-restore.md` and
`2026-09-24-fedora-wsl-reset-opencode-restore-part-2.md`), while fixing three
structural problems that the Fedora reset left behind:

1. Two half-valid V2 "hubs" on the homelab, neither of them authoritative.
2. A reset skill that only knew Fedora, and lied about one path.
3. A bootstrap approach where every distro needed its own hand-rolled script.

The Debian run doubles as the live validation of all three fixes.

## 2. Background (or: A Tale of Two Hubs, Both Wrong)

After the Fedora reset, two V2 hub candidates existed on the homelab:

| Artifact | `/srv/repo/opencode-hub/v2` | `/srv/repo/opencode-v2` | live FedoraWSL |
|---|---|---|---|
| git | none (not a repo at all) | repo, no remote | - |
| `opencode.json` | Sep 22, stale, pre-prune | Sep 23, pruned | **Sep 24, newest** (cloudflare 17 models) |
| `skills/` | 33 dirs, V1 set | 20 dirs, V2 set + archive | mixed |
| `tasks/` | V1 flat files, invalid for v2 | absent | V2 format (active/ + archive/) |
| `machines.md`, `CONTEXT.md` | **newest** (Sep 24 19:3x) | absent | same copies |
| `plugins/` | absent | absent (README says per-host) | 4 V2 plugins |
| `package.json` | absent | gitignored | `@opencode/plugin@2.0.16` |

Two additional facts sealed their fate as reference-only: `/srv/repo/opencode-v2`
had `service.json` **committed in git history** (it contains a `password` key),
and `opencode-hub/v2/` kept `auth.json` and `service.json` lying in a plain,
unversioned directory.

## 3. Problem

The Debian reset needs a restore source. Restoring from a hub with a Sep 22
config (pre-prune whitelists, dead models) or from a skills tree that mixes V1
and V2 would recreate the exact drift the Fedora reset just cured. Meanwhile
`TASK-debian-wsl-reset.md` referenced a `bootstrap-debian-v2.sh` that did not
exist, and its embedded draft script installed `chromium-browser`, a package
that (spoiler) does not exist on Debian 13.

## 4. Work Performed

### 4.1 The canonical hub: `/mnt/c/users/sigit/git/opencode-v2/`

A new local git repo (`core.fileMode false`, because drvfs reads everything as
777) with a homelab mirror at `/srv/repo/opencode-v2-hub/` (non-bare,
`receive.denyCurrentBranch=updateInstead`, so pushes update the readable working
tree). Curated merge, one source per artifact:

| Took | From | Why |
|---|---|---|
| `opencode.json`, `package.json` | live FedoraWSL | newest (pruned whitelists + 17 cloudflare models) |
| `skills/` (20 live + archive) | `/srv/repo/opencode-v2` | the only V2-compliant tree |
| `machines.md`, `CONTEXT.md` | `/srv/repo/opencode-hub/v2` | newest copies |
| `tasks/` | `~/.opencode/tasks/` | V2 task-manager format |
| `plugins/` (4) | live FedoraWSL | backup so fresh hosts install, not hand-copy |

`.gitignore` was written **before anything else** (secrets never touch git):
`service.json`, `auth.json`, `tokens.json`, keys, `node_modules/`, `*.pre-*`,
`__pycache__/`. The nested `.git` inside the google-workspace plugin was
stripped. Initial commit `fa1b3ad`: 136 files, 13847 insertions, verified clean
by filename scan and content scan (the only "auth" hit was a task file named
`TASK-litellm-test-curl-auth`). Key files sha256-verified against the homelab
mirror (`opencode.json` `3f10a964...`).

### 4.2 The skill: `fedora-wsl-reset` -> `wsl-reset`

Renamed and rewritten distro-agnostic (`276f5f3`). The Fedora narrative left;
the concrete binaries stayed, as a verified matrix:

| Thing | FedoraWSL | DebianWSL |
|---|---|---|
| WSL distro name | `FedoraLinux-44` | `Debian` |
| Hostname inside | `fedoraWSL` | `debianWSL` |
| CA trust | `/etc/pki/ca-trust/source/anchors/` + `update-ca-trust extract` | `/usr/local/share/ca-certificates/` + `update-ca-certificates` |
| SSH client package | `openssh-clients` | `openssh-client` |
| Chromium package | `chromium` | `chromium` (**`chromium-browser` does not exist**: `apt-cache policy` says `Candidate: (none)`) |

Also fixed a genuine lie in the old skill: gws tokens restore to
`~/.config/google-workspace-mcp/tokens.json`, not under `~/.config/opencode/`.

### 4.3 The bootstrap: `scripts/bootstrap-wsl.sh`

One script, distro-detecting via `/etc/os-release` (`8cffe30`). Design rules
that survived contact with reality:

- DNS `/etc/hosts` fix runs **before any homelab contact** (the old script tried
  to rsync `homelab` before it could resolve the name).
- Config comes from the hub on `/mnt/c` (no SSH needed); secrets come from the
  per-distro backup repo on the homelab (one password prompt, then keyless).
- `wsl.conf` restores early so systemd (Debian) comes up for `hostnamectl`.
- Ends with a 10-check verification suite and exit 1 with a `wsl --shutdown`
  hint, because some failures are restart artifacts.

### 4.4 The backup: 125 files, committed

`/srv/repo/wsl-reset/debian-reset/` on the homelab (commit `5687c02` for the
secrets gitignore, `4832416` for the backup). Contents: SSH keys, CA cert,
`/etc` configs, the V1 opencode config (plus the `~/.local/share` auth.json in
its correct v2 location, and the V1 leftover as `v1-config-auth.json`), 32
skills, V1 flat tasks, gws tokens, and the `dpkg -l` list. Everything in the
backup script ran without sudo; all sources were world-readable.

### 4.5 The reset itself

User ran the PowerShell rites (`wsl --unregister Debian`, `wsl --install -d
Debian`), created user `sigit`, passwordless sudo, then the bootstrap. The
opencode installer failed with "Failed to fetch version information"; manual
install via `https://opencode.ai/v2/install` produced a working `opencode
v2.0.16`. The script URL is patched since (`241076b`), and the failure mode is
now a documented gotcha (`22ba37d`).

### 4.6 Post-reset: five bugs, all patched

See Diagnosis. One deserves its own paragraph: the WSL loopback relay makes
another distro's localhost listeners visible inside a distro, and OpenCode v2's
managed background service defaults to port 49374. Fedora's service (serving a
live session, no less) held 49374; Debian's opencode could see it, could not
bind it, and "failed to run silently" while its log filled with a serve->fail->
retry loop every five seconds. The fix the error message itself suggests:
`opencode service set port 49475` on Debian, restart, done.

## 5. Diagnosis (or: What Actually Broke, Ranked by Embarrassment)

1. **rsync `-o` is not ssh's `-o`**: passing `-o BatchMode=yes` to rsync makes
   rsync try to transfer a file named `BatchMode=yes` (`-o` is `--owner`). SSH
   options ride inside `-e "ssh ..."` (`3075c86`). This bug was in the backup
   script and the bootstrap both.
2. **The verify line wrote `ssh -q BatchMode=yes`**: ssh treats it as a hostname,
   fails to resolve `batchmode=yes`, and reports FAIL while passwordless ssh
   works fine. The missing `-o` is patched (`241076b`).
3. **Non-idempotent `cp -r`**: re-running the bootstrap copied the plugins dir
   into itself (`plugins/plugins`). The check counted 5 entries and failed while
   the 4 real plugins were fine. Now the script rm's the target first and the
   check tests the 4 plugin dirs explicitly.
4. **Port collision via WSL loopback relay** (above). Debian pinned to 49475.
5. **The 401 that was not stale credentials**: after everything, `opencode run`
   on Debian returned `Provider request failed with HTTP 401` even though
   Fedora and Debian had **byte-identical** auth.json (sha256 `ca876535...`
   both). DNS was clean, same egress IP, same key. The answer, from the user's
   own v1->v2 migration memory: **copying auth.json is necessary but not
   sufficient; OpenCode v2 requires manual authentication on the fresh host**
   (`opencode auth` in bash or `/connect` in the TUI). After manual auth,
   everything works. This is now the loudest gotcha in the skill (`734be89`).

Also decided mid-flight: hostname case `DebianWSL` -> `debianWSL` (matching the
`fedoraWSL` pattern), applied everywhere the value appears: live Debian
(`/etc/hostname`, `wsl.conf`, `/etc/hosts`), `DEFAULT_HOSTNAME` in the script,
`machines.md`, the skill matrix, the task file, and the backup repo's restore
sources (`bc02a8e`) so future re-runs do not silently revert it.

## 6. Preliminary Assessment

The reset is successful. Debian 13 fresh, opencode v2.0.16, 4 plugins loaded
with the `@opencode/plugin` dependency present, gws tokens restored, tasks and
skills from the canonical hub, ssh passwordless (BatchMode-verified), CA trusted
(`ai.home.arpa` health pass), service env x4 transferred from Fedora via a
stdin pipe that never wrote a secret to disk, manual auth done. The verify
suite: **12 pass, 0 fail**.

## 7. Solution Summary (end state)

| Thing | Location |
|---|---|
| Canonical hub (local) | `/mnt/c/users/sigit/git/opencode-v2/` (git, main) |
| Canonical hub (mirror) | `homelab:/srv/repo/opencode-v2-hub/` (push target) |
| Legacy hubs | read-only reference, untouched |
| Per-distro backup | `homelab:/srv/repo/wsl-reset/debian-reset/` (3 commits) |
| Skill | `wsl-reset` (hub, FedoraWSL, debianWSL; sha256 `b6b0e28d...` all three) |
| Bootstrap | `scripts/bootstrap-wsl.sh` + mirror `/mnt/c/users/sigit/.config/bootstrap-wsl.sh` |
| Debian managed service | port 49475, pinned in host-local service.json |
| Debian hostname | `debianWSL` |

## 8. Verification Plan

- [x] ssh homelab passwordless (BatchMode)
- [x] CA trusted for ai.home.arpa
- [x] opencode v2.0.16 on PATH
- [x] `@opencode/plugin` dependency present
- [x] 4 plugins present, no nested dir
- [x] hostname files all say debianWSL
- [x] gws tokens present
- [x] tasks restored (V2 session-index)
- [x] skills restored (incl. wsl-reset)
- [x] auth.json present at the v2 location
- [x] service env keys: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_WORKSPACE_SERVICES, MEM0_API_KEY
- [x] service healthy on 49475
- [ ] first `wsl --shutdown` cycle: systemd activates, `hostnamectl` goes live
- [ ] `opencode plugin list` (4) + `opencode mcp list` (gws, mem0) in a fresh Debian session

## 9. Pending Actions

1. One `wsl --shutdown` from Windows when convenient (systemd + hostnamectl go
   live; everything is already correct in the files).
2. FedoraWSL's local `~/.config/opencode/skills/` still carries the 15 V1 skills
   the hub has archived; align to the hub's live list.
3. Windows native opencode is still v1 (1.18.32) -> the Phase 5 upgrade.
4. gws `get_status` returns a schema-validation error (`last_error` shape) even
   when auth is fine; upstream bug, harmless, test with real calls.
5. From the recovery task: rotate the Google OAuth credentials that leaked into
   an old transcript (still open, still recommended).

## 10. Recommendations

1. **The hub is git; treat it like git.** Push, pull, commit; never `rsync
   --delete` into it (that wiped a `.git` once).
2. **Secrets have three legitimate homes**: the per-distro ext4 home, the
   per-distro backup repo (gitignored, on-disk only), and `opencode service
   env`. Never `/mnt/c`, never committed, never printed in a transcript.
3. **After any v2 install or reset, run `opencode auth` manually.** A restored
   auth.json alone produces 401s that look like credential rot and burn an hour.
4. **Pin the managed service port per host** the moment a second WSL distro
   runs opencode; the loopback relay makes "port in use by another process" a
   cross-distro phenomenon.
5. The wsl-reset skill is now validated by two real runs (Fedora, then Debian).
   The next reset should be nearly boring. Boring is the goal.

Generated with GLM 5.3 by z-ai (NVIDIA NIM)
