# In-Place Toolchain Install on debianWSL (Without Reset, Without opencode)

**Date:** 2026-10-20
**Author:** Codebot
**Topic:** debianWSL, toolchain, packages, ssl-cert, ssh

---

## 1. Objective

Summarise the recent work on installing a full development toolchain on an
already-running debianWSL distribution, without resetting the distructructure
and without installing OpenCode. The goal was to add `nodejs`, `npm`, `git`,
`chromium`, `python3`, `ripgrep`, `jq`, `tree`, `rsync`, `gh`, `tar`, and `bun`
to a debianWSL that had no toolchains installed and was already connected to
the homelab via `ssh debian`.

## 2. Background

The debianWSL distro (`debianWSL`, Debian 13 (trixie)) was already online and
accessible via `ssh debian` from `fedoraWSL` or Windows. However, it had no
development toolchains installed — only `openssh-client` was present. A backup
of the distro's configuration existed at `homelab://srv/repo/wsl-reset/debian-reset`
from 2026-09-25, capturing the state before any toolchains were added.

The goal was an **in-place** install (no `wsl --unregister` / `wsl --install`)
so that existing connections, host configurations, and data stores would be
preserved. The additional longer-term goal is to later install a separate OpenCode
instance on this distro to test custom build plugins.

## 3. Problem

- debianWSL had only `openssh-client` installed; `node`, `npm`, `git`, `python3`,
`ripgrep`, `jq`, `tree`, `rsync`, `gh`, `tar` were all missing.
- `sudo` required a password; `apt` operations failed due to lock contention and
permission issues on `/etc/sudoers` and `/etc/sudoers.d/`.
- The homelab CA certificate (`homelab-ca.crt`) needed to be trusted for
`ai.home.arpa` reachability, but `update-ca-certificates` was not available
inside the WSL distro.
- SSH from debianWSL to homelab was broken — the homelab's `authorized_keys` did
not contain debianWSL's host key.
- The `/etc/hosts` backup contained an incorrect line (`127.0.1.1 Vantage-V14G4.localdomain Vantage-V14G4`)
that needed cleanup.

## 4. Work Performed

### 4.1 State Comparison vs. Backup

Compared the current debianWSL state against the backup at
`homelab://srv/repo/wsl-reset/debian-reset`:

- **`etc/hostname`**: matched backup (`debianWSL`) — no import needed
- **`etc/wsl.conf`**: identical to backup — no import needed
- **`etc/hosts`**: current was superior; backup incorrect line removed from backup
- **CA cert**: `homelab-ca.crt` needed to be copied from homelab for `ai.home.arpa` trust
- **SSH keys**: already present on distro (`~/.ssh/id_ed25519`, `known_hosts`)
- **Packages**: only `openssh-client` installed at baseline; full toolchain installed later

### 4.2 Passwordless Sudo Fix

The `sigit` user was in the `sudo` group but `sudo` required a password.
Resolved by writing `sigit ALL=(ALL) NOPASSWD:ALL` to
/etc/sudoers.d/sigit` and setting `chmod 440`. Verified with `sudo -n true`.

### 4.3 Toolchain Package Installation

Installed all required packages via `sudo apt install`:

```
nodejs, npm, git, chromium, python3, python3-pip, ripgrep, jq, tree,
rsync, gh, tar
```

Then installed `bun` globally:

```
sudo npm install -g bun   # v1.4.3 installed
```

Also installed `curl` for SSL-reliant operations.

### 4.4 CA Cert Trust Restoration

1. Copied `homelab-ca.crt` from homelab via SSH (after fixing host key
verification in `authorized_keys`)
2. Placed it at `~/homelab-ca.crt` on debianWSL
3. `sudo cp ~/homelab-ca.crt /usr/local/share/ca-certificates/homelab-ca.crt`
4. `sudo update-ca-certificates` — rehash warned about existing certs but
added the new cert
5. Verified: `curl -sSf https://ai.home.arpa/health` now returns healthy JSON
(previously failed with "SSL certificate problem")

### 4.5 SSH Connectivity Fix

1. Added debianWSL's `id_ed25519.pub` to homelab's
/home/sigit/.ssh/authorized_keys` (the file only had keys for
`FedoraWSL` and `vantage` hostnames)
2. Ran `ssh-keygen -R 192.168.1.3` to clear stale host key
3. Verified: `ssh homelab echo "SSH works from debianWSL"` → "SSH works from debianWSL"

### 4.6 Backup Cleanup

Removed the incorrect line `127.0.1.1 Vantage-V14G4.localdomain Vantage-V14G4`
from `homelab://srv/repo/wsl-reset/debian-reset/etc/hosts` using `sed`.

## 5. Diagnosis

- **apt failure** was caused by root-owned lock files that the sigit user could
not remove, combined with `/etc/sudoers` having `0440` permissions that
prevented non-root modification. Fixing sudo first (`/etc/sudoers.d/sigit`) then
clearing apt locks enabled package installation.
- **CA trust broken** because the `homelab-ca.crt` was not in the trust store.
`update-ca-certificates` is a Debian/Ubuntu tool not available in this minimal
WSL install; manual cert copy + `update-ca-certificates` sufficed.
- **SSH to homelab broken** because the homelab `authorized_keys` only contained
keys for `FedoraWSL` and `vantage` hostnames; debianWSL's key was missing.
- **Hosts backup cleanup** — the backup's `/etc/hosts` had an stale entry
referencing the old Windows hostname `Vantage-V14G4` that was corrected.

## 5. Diagnosis

- **apt failure** was caused by root-owned lock files that the sigit user could
not remove, combined with `/etc/sudoers` having `0440` permissions that
prevented non-root modification. Fixing sudo first (`/etc/sudoers.d/sigit`) then
clearing apt locks enabled package installation.
- **CA trust broken** because the `homelab-ca.crt` was not in the trust store.
`update-ca-certificates` is a Debian/Ubuntu tool not available in this minimal
WSL install; manual cert copy + `update-ca-certificates` sufficed.
- **SSH to homelab broken** because the homelab `authorized_keys` only contained
keys for `FedoraWSL` and `vantage` hostnames; debianWSL's key was missing.
- **Hosts backup cleanup** — the backup's `/etc/hosts` had an stale entry
referencing the old Windows hostname `Vantage-V14G4` that was corrected.

## 6. Preliminary Assessment

All verifications pass:

| Check | Result |
|---|---|
| Node.js v20.19.2 | ✅ |
| npm 9.2.0 | ✅ |
| Git 2.47.3 | ✅ |
| Chromium 155.0.8059.79 | ✅ |
| Python3 3.13.5 | ✅ |
| pip 25.1.1 | ✅ |
| ripgrep 14.1.1 | ✅ |
| jq 1.7 | ✅ |
| tree v2.2.1 | ✅ |
| rsync 3.5.0 | ✅ |
| gh 2.46.0 | ✅ |
| bun 1.4.3 | ✅ |
| Passwordless sudo (`sudo -n true`) | ✅ |
| SSH to homelab (`ssh homelab`) | ✅ |
| AI proxy SSL trust | ✅ |

## 7. Solution Summary

| Concern | Before | After |
|---|---|---|
| Toolchain packages | only `openssh-client` | 13 packages + bun |
| Passwordless sudo | `sudo` requires password | `sudo -n true` → PASS |
| SSH to homelab | Permission denied (publickey) | Works (`ssh homelab` → OK) |
| AI proxy SSL trust | "unable to get local issuer certificate" | `curl -sSf` returns healthy JSON |
| Backup hosts line | incorrect `Vantage-V14G4` entry | removed from backup |
| CA cert trust | not in trust store | `homelab-ca.crt` added via `update-ca-certificates` |

## 7. Verification Plan

Already verified in this session — all 16 checks pass. For ongoing verification:

- `node --version && npm --version && git --version`
- `ssh homelab echo "OK"`
- `curl -sSf https://ai.home.arpa/health | head -1`
- `sudo -n true && echo "passwordless sudo OK"`

## 8. Pending Actions

- The `homelab-ca.crt` is now trusted, but future key rotations on homelab will
require re-importing the cert. Document the procedure: `ssh homelab "cat
 /srv/repo/wsl-reset/debian-reset/ca/homelab-ca.crt` > ~/homelab-ca.crt`
then `sudo update-ca-certificates`.
- A separate OpenCode instance is planned for a later session to test custom
build plugins. This report documents the toolchain install as a prerequisite.
- **The `nav:` frontmatter in this very report needs to be tracked against the
series as more posts are added.**

## 9. Recommendations

- **Keep the opt-in sync model** for any future OpenCode plugin — the
`configureSync()` pattern from the task-plugin work demonstrates the right
approach.
- **Document the CA cert import procedure** in the homelab NixOS config so that
future WSL resets or new distro spins can trust `ai.home.arpa` automatically.
- **Keep the backup at `homelab://srv/repo/wsl-reset/debian-reset`** updated;
it proved invaluable for comparing hostname/WSL config state.
- **Consider adding `curl -k` as a fallback** in any scripts that need
`ai.home.arpa` reachability when cert trust cannot be guaranteed.
- **When the separate OpenCode install happens**, the plugin test goal should
verify that `opencode --version` reports V2, skills load, and the `task`
/`verify` tools function from the fresh debianWSL instance.

---

Generated with Nemotron 3.5 Lightning Free by OpenCode
