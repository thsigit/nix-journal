# The Cleanup That Bit Back: How an Aggressive Cache Wipe Broke OpenCode on Fedora WSL and Spawned a Debian Backup

**Date:** 2026-08-29  
**Author:** Codebot  
**Topic:** wsl, fedora, debian, opencode, bun, cleanup, troubleshooting

---

## 1. Objective (or: Why Do We Suddenly Own a Second Linux?)

The goal of this session was simple on paper and embarrassing in practice: install a secondary WSL distribution (Debian) because FedoraLinux-44, the primary WSL distro, could no longer start OpenCode. The failure was widely attributed to the day's earlier "aggressive cleanup" session, which had reclaimed gigabytes of disk while (allegedly, circumstantially, suspiciously) clipping the OpenCode binary down to exactly 16,777,216 bytes. This report documents the full arc: the cleanup session that bit back, the Bus error that followed, and the parable about why you should never let an AI agent turn your home directory into a demo of *find -delete* without supervision.

## 2. Background (The Lay of the Land)

The Windows host runs two WSL distributions:

| Distro | Role | Notes |
|--------|------|-------|
| FedoraLinux-44 | Primary | Long-lived, tooled, home to the OpenCode daily driver and the only SSH key for the homelab |
| Debian | New backup | Freshly installed this session, starting from nearly nothing |

Related infrastructure:

- The homelab (NixOS, `192.168.1.3`) hosts this journal and the AI gateway that OpenCode talks to; the gateway is not named here for security reasons.
- OpenCode is distributed as a self-contained binary powered by Bun, the JavaScript runtime. Bun mmaps its own executable at launch - a detail that becomes very relevant in section 3.
- WSL distros share the Windows filesystem (`/mnt/c`) but each keeps its own ext4 root, userland, package manager, and `~/.config`. This is both a feature and a trap.

## 3. Problem (And Then It Went "Bus Error")

Launching OpenCode on Fedora produced:

```
Bus error
```

...and nothing else. No stack trace, no help text, just two words and a dead prompt. A Bus error (SIGBUS) is what happens when a process tries to read memory mapped to a file that is shorter than expected - the classic Bun footgun, since Bun maps its own executable binary into memory.

Inspection told the real story. The binary at `~/.opencode/bin/opencode` weighed in at exactly:

```
16,777,216 bytes  (this is 2^24 - suspiciously round)
```

while a healthy copy is:

```
184,682,624 bytes  (openCode v1.18.25)
sha256 d91e0d33676d0839f7cde87924cd4127ea88c9d6784eea9f009a7d08bdc60eeb
```

The binary had been truncated. Truncation to a power of two smells like an interrupted copy, a cleanup tool that clipped instead of deleting, or a filesystem squeezing a file into a smaller cluster. The leading suspect was the aggressively thorough cleanup session earlier that day (documented below), which had been deleting files all over `$HOME`.

## 4. Work Performed (The Fun Part, and Lots of It)

### 4.1 The Cleanup Session Recap (The Imported Summary)

Earlier the same day, Fedora hosted an OpenCode session titled **"Cleanup FedoraWSL Windows Host temp cache"** (`session ses_fb3da2e7affeERGCVebzObEydA`, agent `reason`, model `nvidia/nemotron-3-super-120b-a12b`, 2026-08-29 14:12:22 to 17:35:02, tokens in/out/cache 1,018,725 / 20,356 / 1,575,552). That session's victory lap, in order:

| Time | Act |
|------|-----|
| 14:12 | Surveyed the mess: `~/.cache` at 4.8 GB, `/tmp` 19 MB, Windows user `Temp` 653 MB; recommended `dnf clean all`, Disk Cleanup, Storage Sense |
| 14:45 | Installed `ncdu` + BleachBit; BleachBit aborted on `system.memory` (WSL swap is Windows-managed - skipping it is correct) |
| 14:56 | `windows.*` cleaners failed with `KeyError: 'windows'` - BleachBit's Windows backend does not run inside Linux |
| 15:00 | Q&A on shrinking the dynamic `ext4.vhdx` (trim + zero-fill + `Optimize-VHD` from PowerShell) |
| 17:18 | Removed ollama, claude, and codex: binaries and data dirs (`~/.ollama`, `~/.claude`, `~/.codex`, `/var/lib/ollama`) - reclaimed about 8 GB (20 G to 12 G used) |
| 17:23 | Deleted leftover `/usr/local/lib/ollama` models (2.1 GB) after a backup |
| 17:28-17:30 | `delete all .py/.sh/.tmp/.log/.bak in $HOME`, plus OpenClaws and Hermes leftovers. Yes, all of them. Everywhere. |
| 17:31 | "All caches": BleachBit (~489 MB, 15,555 files), pip/npm/dnf caches, thumbnails, `journalctl --vacuum-time=3days` (~792 MB). Disk now 7.0 GB used, ~15 GB reclaimed in total |
| 17:33 | "Make this session a skill" - created `~/.config/opencode/skills/fedorawsl-cleanup/SKILL.md` containing the whole recipe |

The session was a masterpiece of disk hygiene and a horror movie of self-preservation. Somewhere in that 17:28-17:31 window, the OpenCode binary appears to have been collateral damage.

### 4.2 Diagnosing the Bus Error on Fedora

From the new Debian box, Fedora was reached via:

```
wsl.exe -d FedoraLinux-44 --cd / -- <command>
```

Diagnosis steps:

- Confirmed the binary size was exactly 16,777,216 bytes vs the known-good 184,682,624 bytes and mismatched sha256.
- Confirmed `~/.local/share/opencode/opencode.db` (614 MB) passed `PRAGMA integrity_check` - sessions survived even if the launcher did not.
- Reinstalled OpenCode; the binary came back intact and OpenCode launched. Fedora was saved.

### 4.3 Ollama Removal Again - But Properly

Earlier in this session Fedora also had a lingering ollama install cleaned up properly: stopped and disabled `ollama.service`, removed the stale unit `/etc/systemd/system/ollama.service`, removed `/usr/lib/ollama`, and deleted the `ollama` system user/group (which `sigit` was still a member of). Then Fedora was restarted with `wsl.exe -t FedoraLinux-44` (which produced a benign "failed to start systemd user session" warning from a corrupted journal).

### 4.4 Debian: The Backup Distro Comes Online

The new Debian WSL instance started from almost nothing - no git, no node, no python, no package manager cache of consequence. The toolchain was provisioned with `apt` (run manually by the user, since Debian `sigit` requires a sudo password, unlike Fedora):

| Tool | Debian version |
|------|----------------|
| git | 2.47.3 |
| node | v20.19.2 |
| python | 3.13.5 |
| sqlite3 | 3.46.1 |
| jq / unzip / wget | present |
| bun | 1.4.0 (installed via `curl -fsSL https://bun.sh/install \| bash`; the first attempt failed with "unzip is required to install bun" until unzip existed) |

Fedora got parity on tooling too: `python3-pip` (pip 26.0.1), `pipx` 1.15.0 (note: the package is `pipx`, not `python3-pipx`), and bun 1.4.0.

### 4.5 Work-Style Guardrails on Both Distros

Having watched an agent wield `find -delete` like a hedge trimmer, the obvious next step was protection. A fail-fast, ask-first work-style was defined and applied to **both** distros:

| Setting | Value |
|---------|-------|
| `permission.bash` | `"*": "ask"` with a read-only allowlist (`ls`, `pwd`, `whoami`, `which`, `git status/diff/log/branch/remote`, `df -h`, `du`, `find`, `stat`, `uname`) |
| `experimental.continue_loop_on_deny` | `false` |
| agent `steps` | `8` (fail fast instead of looping forever) |
| `instructions` | `workstyle.md`: give up after a few attempts, propose alternatives, ask before changing system state |

Debian config lives in `~/.config/opencode/opencode.jsonc`; Fedora's in `~/.config/opencode/opencode.json` (backed up to `opencode.json.pre-workstyle`). The whole reason this exists is that cleanup session. The guardrail has a scar story.

### 4.6 Sharing Sessions Across Distros (The Experiment)

To avoid divergent histories, cross-distro session sharing was probed:

- SQLite WAL on `/mnt/c` (9p/drvfs): all tests passed - the shared store idea is viable.
- Mounting `\\wsl.localhost\Debian\...` from Fedora: failed - drvfs mount helper does not support mounting another WSL distro's VHD.
- Recommended pattern: symlink `~/.local/share/opencode` on both distros to a single Windows folder such as `/mnt/c/wsl-opencode/opencode`, keeping configs and binaries local.

### 4.7 Reading Fedora Sessions From Debian

Fedora's OpenCode history was exported without disturbing the running instance: `sqlite3` was run read-only (via `file:...?mode=ro` / `URI` mode) against Fedora's `~/.local/share/opencode/opencode.db`, walking the `session`/`message`/`part` tables (JSON `data` columns, timestamps in epoch milliseconds) to produce the session summary behind section 4.1. This worked cleanly from Debian through `wsl.exe`, proving the backup distro can always interrogate the primary.

## 5. Diagnosis (What Actually Broke)

The OpenCode executable on Fedora was truncated to exactly 2^24 bytes. Because Bun maps its own binary, any read past the clipped end delivers SIGBUS - hence the terse "Bus error". Whether the aggressive cleanup did the clipping directly or whether a failed copy elsewhere did, the strong circumstantial evidence (a session that serialized threshold-legal deletions of `.sh/.py/.log/.bak` files plus full cache purges, minutes before the breakage) makes the cleanup the prime suspect. The session database itself was unharmed - only the launcher was crippled.

Culturally, two failures compounded: an agent that deletes without human gates, and a session that immortalized the whole procedure into an auto-loading skill (`fedorawsl-cleanup/SKILL.md`). That skill, a compendium of `rm -rf` verdicts, was reviewed and deleted by the owner during this session. The memory lingers as this report.

## 6. Preliminary Assessment (Is the Backup Worth It?)

Yes, with caveats:

- A second, independent WSL distro is a genuine rescue environment: even when Fedora's OpenCode is bricked, Debian can interrogate Fedora, export its sessions, reinstall its tools, and generally hold the flashlight.
- But the backup starts cold: Debian has no SSH key for the homelab (the only `id_ed25519` lives on Fedora), and its sudo requires a password. Transferring credentials to the backup is the obvious gap.
- The guardrails (work-style config) buy time for human review before any future cleanup can go full-lawnmower.

## 7. Solution Summary (What We Did)

- Diagnosed and fixed Fedora's Bus error: reinstalled the correct OpenCode binary (184,682,624 bytes, sha256 matched, v1.18.25); DB verified intact and untouched.
- Cleaned up ollama's lingering traces on Fedora (unit, `/usr/lib/ollama`, user/group) and restarted the distro.
- Brought the new Debian distro up to parity: git, node, python, sqlite3, jq, unzip, wget, bun; Fedora gained pip/pipx/bun.
- Applied the fail-fast, ask-first work-style to both distros (with a backing config backup on Fedora).
- Mapped the shared-session path (symlinked data dir on `/mnt/c`) and proved read-only session export across distros via sqlite.
- Reviewed and deleted the dangerous auto-generated cleanup skill.

## 8. Verification Plan (How We Know It Works)

- OpenCode v1.18.25 launches on both distros; the sha256 of the restored binary matches the known-good value.
- `opencode.db` on Fedora passes `PRAGMA integrity_check` (614 MB intact, sessions readable).
- Toolchain spot-checks on Debian: git 2.47.3, node v20.19.2, python 3.13.5, sqlite3 3.46.1, bun 1.4.0.
- SSH with `ssh homelab` verified from FedoraWSL (host key ED25519 accepted, `192.168.1.3`); `docs/` in `/srv/repo/nix-journal` is owned by `sigit`, so no sudo needed for publishing.
- Work-style deny-loop behavior confirmed by config inspection on both distros.

## 9. Pending Actions (What's Left)

- Seed Debian's `~/.ssh` with a homelab key (or one deliberately generated for the backup) and an `~/.ssh/config` entry so `ssh homelab` works natively from the backup.
- Decide and implement the shared-session symlink (`/mnt/c/wsl-opencode/opencode`) if a unified history is desired.
- Keep backups of `opencode.db` before any future cleanup spree: 614 MB of conversational history is not replaceable; 16 MiB of launcher is.
- Commit this report and publish via `/srv/repo/nix-journal/scripts/publish.sh` when the owner approves.

## 10. Recommendations (The Mandatory Closing Section)

1. **Beware the really convenient cleanup sessions.** The moment an agent proposes deleting "just logs, scripts, and temp files, all at once, recursively", require human approval on a per-directory level. That is now enforced by config, not vibes.
2. **Never enshrine destructive flows into auto-loading skills.** The `fedorawsl-cleanup` skill was pure, concentrated `rm -rf` dressed up as knowledge. Any skill that can destroy state should be opt-in, reviewed, and probably named something un-memorable on purpose.
3. **Keep a warm spare.** A second WSL distro is cheap insurance. Fedora lost its OpenCode for an evening; with a Debian backup, the writer carries on regardless.
4. **Verify binaries like a paranoid sysadmin.** Reference sizes and hashes whenever possible. If your runtime-mapped launcher is ever 2^24 bytes, that is not a coincidence, it is a crime scene.
5. **Hashes are cheap, history is priceless.** Back up `opencode.db` before any large-scale hygiene pass. The database survived this round; plan as if it will not next time.
6. **Give the backup distro keys too.** A rescue environment that cannot SSH to the homelab is a fire extinguisher filled with water. Fix that gap before it matters.

The cleanup of 2026-08-29 reclaimed ~15 GB and, in the process, taught a lesson that no `dnf clean all` could ever provide: sometimes the file you delete is the one you are running. Famous last words, indeed.

Generated by Big Pickle (OpenCode)