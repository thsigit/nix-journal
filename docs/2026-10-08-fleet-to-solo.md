---
nav:
  series: "Fleet to Solo"
  part: 1
  next:
    title: "Archiving the Fleet and Standing Up Debian (or: We Actually Deleted Things This Time)"
    slug: 2026-10-08-archiving-the-fleet-and-standing-up-debian
---

# From Three Hosts to Solo Fedora (or: We Built a Fleet by Accident, Then Wound Down)

**Date:** 2026-10-08  
**Author:** Codebot  
**Topic:** opencode, fleet, wsl, sync-opencode, mesh-bootstrap, solo-setup

---

## 1. Objective (or: What Are We Even Doing Here?)

Document the retirement of the three-host opencode deployment (FedoraWSL CLI + Windows Desktop + DebianWSL CLI) and the transition to a solo Fedora setup. Confirm the state of artifacts, sync mechanisms, and open carry-overs.

This journal post documents the evolution of our Opencode deployment strategy, from a multi-host fleet configuration to a simplified solo setup on FedoraWSL. After extensive experimentation with synchronization strategies, we've distilled our workflow into a streamlined approach that preserves functionality while reducing operational complexity.

## 2. Background (or: How We Got The Fleet)

Initially, we operated three Opencode instances across three machines: **Windows** hosted the canonical configuration (opencode.json, skills, plugins); **Fedora** ran Opencode CLI for local development; **Debian** initially ran CLI, later became an MCP server. This allowed cross-host synchronization testing, deployment model validation, and sync strategy experimentation.

We explored two primary synchronization approaches: **Universal (Windows-centric)** - Windows disk (`C:\Users\SIGIT\.config\opencode`) as single source of truth; rsync to Fedora/Debian; centralized config. Broken because Windows became the bottleneck. **Federated (hub-and-distros)** - Fedora hub (`/mnt/c/users/sigit/git/opencode-v2/`) with `homelab` mirror; per-distro `opencode.json`; distributed sync. Challenge: managing bidirectional sync and avoiding drift.

The journey started with FedoraWSL - the only working host - and grew by accident. `2026-08-29-three-distros-one-opencode-setup-part-1.md` records the origin: "I Built a Fleet by Accident." Debian arrived second (skills copied wholesale, SSH fixed, CA trust installed), then Windows (a June-12-vintage `opencode.json`, old `node_modules`, skills never pointed at anything). By `2026-09-29-three-sync-domains-and-the-unified-fleet-sync-plan.md` three hosts shared 24 active skills byte-identical across all, with `archive/` at 15 - a synchronized fleet in fact.

Two sync architectures were tried:

- **Universal (Windows-centric):** Windows disk at `C:\Users\SIGIT\.config\opencode` as single source of truth; rsync to Fedora/Debian. Broken because Windows and Linux paths diverge (`npx -y @dguido/google-workspace-mcp` fails on Windows; direct `node <abs>` needed).
- **Federated (hub-and-distros):** Fedora hub (`/mnt/c/users/sigit/git/opencode-v2/`) with `homelab` remote mirroring to `/srv/repo/opencode-v2/config.git`; per-distro `opencode.json` with `mcp` key differences allowed. This converged - 26 commits pushed, `0 0` divergence - but still required SSH mesh maintenance, `mesh-bootstrap.sh`, and constant parity checks.

## 3. Problem (or: Why We Stopped)

After extensive testing, maintaining the multi-host fleet was unnecessary. Key reasons: (1) **Operational Complexity** - SSH configs, key distribution, network policies; (2) **Limited Benefits** - most functionality achievable with a single host; (3) **Simplicity** - one host reduces management overhead.

The fleet was a successful experiment that outlived its usefulness. Reasons (in order of weight):

| Problem                                | Evidence                                                                                                                                                                                                                                    |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Port conflict                          | `49374` held by Fedora CLI; Debian's service saw it via WSL loopback relay, could not bind, filled log with retry loop. Fixed to `49475` (Sept 25); later refined to `49375` for Fedora CLI, freeing `49374` for Windows desktop.           |
| Service is session-scoped, not systemd | No `systemctl` unit; service dies when last session closes. Confirmed `2026-09-29-false-verifications-and-the-v1-question.md`.                                                                                                              |
| `npx` wrapper breaks MCP stdio         | `2026-09-30-mcp-npx-to-node-invocation.md` - direct `node <abs>` required; relative paths fail because CWD != config dir.                                                                                                                   |
| Documentation drift                    | `skills/README.md` claimed byte-identical shared files - wrong for `opencode.json`, wrong for `mcp.gws.command`. `sync-opencode/SKILL.md` required a `Rewritten 2026-09-30` warning label (`2026-10-05-seven-rounds-about-a-whitelist.md`). |
| Mesh bootstrap needs SSH keys + sshd   | Debian reset = no `id_ed25519`, sshd `inactive`, `ssh-keygen` missing. `mesh-bootstrap.sh` at `e137f60` handles this but requires pre-install of `openssh-client`.                                                                          |

The operational overhead (SSH keys, `mesh-bootstrap.sh`, parity scripts, `wsl.exe` vs real SSH) exceeded the value of having Debian + Windows as active Opencode hosts.

## 4. Work Performed (or: What Actually Happened This Session)

### 4.1 Port conflict resolved

Fedora CLI moved to `49375` (`opencode service set port 49375` verified; `service.json` confirmed; `127.0.0.1:49375` LISTEN). Windows desktop runs independently on `49374` - no conflict, both verified working.

### 4.2 Mesh-bootstrap script committed

`mesh-bootstrap.sh` committed at hub `e137f60`. `--check` passes (9/9 reachable); full build requires Debian with `openssh-client` and sshd active (not yet done - Debian is freshly installed with no programs).

### 4.3 Hub remote to homelab

Remote `homelab` added (`sigid@192.168.1.3:/srv/repo/opencode-v2/config.git`). 26 commits fast-forwarded; divergence `0 0`. Mirror at `/srv/repo/opencode-v2/config.git` is canonical.

### 4.4 Write-to-blog reconciled 4-way

`write-to-blog` skill reconciled across all four hosts (FedoraWSL, Windows, DebianWSL, hub): 4-way manifest `8fd85aa8...`; archive = 15; `skills/README.md` updated with warning label against destructive "fix".

### 4.5 User-directed manual steps deferred

- Windows: `scoop uninstall versions/opencode2`; delete `C:\Users\SIGIT\.config\opencode` (preserves hub at `git/opencode-v2`) - already cleaned per user note.
- Debian: reset to clean WSL; plan to use only as MCP server (not Opencode host).

## 5. Diagnosis (or: Why Solo On Fedora)

- **Single host eliminates sync surface.** No `fleet-sync`, no `sync-opencode`, no parity script, no SSH hop.
- **Port conflict disappears** - one listener, one port.
- **MCP server needs only `node` invocation**, not `npx`; with one host this is a local config choice, not a cross-host divergence.
- **Hub remains canonical source** - `homelab` mirror keeps backup; Fedora pulls from it on demand.
- **Windows desktop is experimental** - not connected to Fedora's config at all.

## 6. Solution Summary (or: The New Architecture)

| Component        | Before (Fleet)                                              | After (Solo)                                            |
| ---------------- | ----------------------------------------------------------- | ------------------------------------------------------- |
| Opencode CLI     | Windows + Fedora + Debian                                   | Fedora only                                             |
| Opencode Desktop |                                                             | Windows standalone (experiment only)                    |
| Debian WSL       | Opencode CLI (identical config with Fedora WSL and Windows) | MCP server only (reset, clean install)                  |
| Config sync      | `fleet-sync` plugin, `rsync` hub->distro, SSH mesh          | None - manual pull from hub on demand                   |
| Port             |                                                             | `49375` on Fedora CLI; `49374` on Windows (independent) |
| Service          | Session-scoped on all three                                 | Session-scoped on Fedora only                           |
| Mesh             | `mesh-bootstrap.sh`, SSH keys, sshd                         | Not needed                                              |
| Hub              | Windows disk (`C:\Users\SIGIT\.config\opencode`)            | `git/opencode-v2` with `homelab` remote                 |

We're now operating with a single FedoraWSL instance as the primary Opencode host:

- **Fedora**: Runs Opencode CLI and serves as the primary development environment
- **Windows**: Runs Opencode Desktop (separate instance) for experimentation only
- **Debian**: Completely reset to function as an MCP server, not as an Opencode host

This simplified architecture provides: cleaner configuration management, reduced maintenance overhead, clearer separation between development and deployment environments, and no need to maintain synchronization between multiple hosts.

## 7. Verification Plan (or: How We Know It Works)

- [x] Fedora CLI responds on `127.0.0.1:49375`
- [x] Windows desktop responds independently (no conflict)
- [x] `opencode cli` and `opencode desktop` run side by side
- [x] Hub `e137f60` pushed; `0 0` divergence
- [x] `mesh-bootstrap.sh` committed; `--check` passes
- [ ] Debian SSH mesh rebuilt (blocked - fresh install needs `openssh-client`, sshd, keygen)
- [ ] `mesh-bootstrap.sh` full build (blocked - depends on Debian fix above)
- [ ] Phase 3 retire `sync-opencode`/`fleet-sync` skills and archive stale tasks (independent session)

## 8. Pending Actions (or: What's Still On The Table)

From `TASK-finish-and-archive-sync-distro-tasks.md`:

1. **Archive sync-related skills/plugins** - `sync-opencode`, `fleet-sync` plugin, and related archive files when we're certain no host needs them.
2. **Fix SSH mesh** - Debian needs `apt-get install openssh-client openssh-server`, key generation, sshd start, authorized_keys distribution via `mesh-bootstrap.sh`.
3. **Windows scoop** - user confirmed already cleaned; no further work.

**Update (Part 2, 2026-10-08):** items 1-2 are resolved by `2026-10-08-archiving-the-fleet-and-standing-up-debian.md` - the sync skill/plugin were archived (not deleted) and the SSH mesh was rebuilt by hand, with `mesh-bootstrap.sh` retired instead of run.

## 9. Recommendations (or: What To Do Next)

1. **Keep the hub, don't abandon it.** The `homelab` mirror is the only backup of 26 commits; don't delete the hub after retiring the fleet.
2. **Don't restore the fleet unless there's a reason.** The cost (SSH mesh, parity, port management, `npx` fixes) exceeds the value of a second CLI host.
3. **Treat Debian as infrastructure, not app.** If it becomes an MCP server, manage it like a service (systemd, not session-scoped), and don't try to run Opencode on it.
4. **Write-to-blog stays reconciled.** If the skill diverges again, fix at source (hub) and propagate - don't try to fix three copies independently.
5. **When retiring finally:** archive `TASK-repair-unavailable-skills-sync-opencode-wsl-reset.md` and `TASK-test-sync-opencode.md` to keep the ledger honest.

---

Generated with Hy3 (Free) by Kenari (free tier)
