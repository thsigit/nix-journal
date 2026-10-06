# Splitting nix-lab pkgs into Standalone Repos and Setting Up Multi-Machine GitHub Auth

**Date:** 2026-08-13  
**Author:** Codebot  
**Topic:** NixOS, migration, workflow, homelab, SSH, WSL2, refactor, housekeeping  

---

## 1. Objective

Consolidate the homelab packaging layout and GitHub presence in one pass:

- Extract the monolithic `pkgs/` directory out of `nix-lab` into four independent, GitHub-tracked repositories.
- Rename the `consolectl` Go tool to `wakectl`.
- Document each binary, push everything to GitHub, prune stale repos, and add LICENSE, .gitignore, and CI.
- Establish a clean, per-machine GitHub authentication topology for WSL2, Windows Git Bash, and homelab.

## 2. Background

`nix-lab` (the NixOS system configuration at `/srv/repo/nix-lab`) consumed three locally-built tools via relative `callPackage` paths under `pkgs/`:

- `bitrouter` - Nix packaging for the BitRouter LLM router (prebuilt release binary).
- `opennds` - Nix packaging for the openNDS captive portal (built from source).
- `litellm-cli` - a pure bash CLI plus NixOS module for a LiteLLM gateway (already its own git repo).

A fourth tool, `consolectl`, lived separately under `/srv/repo/scripts` as a Go keyboard injector for headless consoles. The goal was to make each package its own repo so they could be developed and pushed independently of the system config.

## 3. Work Performed

### 3.1 Split pkgs/ into four standalone repos

Moved each package to its own directory under `/srv/repo`:

- `/srv/repo/bitrouter` (git init, initial commit)
- `/srv/repo/opennds` (git init, initial commit)
- `/srv/repo/litellm-cli` (moved with its existing `.git`)
- `/srv/repo/wakectl` (formerly `/srv/repo/scripts/consolectl`; see 3.2)

Updated `nix-lab/flake.nix` to reference all three as `path:` inputs and pass them as `commonSpecialArgs` (`litellmCli`, `bitrouter`, `opennds`). The two `callPackage` references were repointed:

```nix
bitrouterPackage = pkgs.callPackage bitrouter { };
opennds         = pkgs.callPackage opennds { };
```

Dropped the stale `pkgs/litellm-cli/` entry from `.gitignore` and `git rm`'d the moved paths from `nix-lab`. Verified the system still evaluates with a dry-run build of `nixosConfigurations.server`.

### 3.2 Rename consolectl to wakectl

Renamed the directory and all identifiers: the Go `module consolectl` became `module wakectl`, the binary `consolectl` became `wakectl`, the lock file `consolectl.pid` became `wakectl.pid`, and the default binding config path moved from `~/.config/consolectl` to `~/.config/wakectl`. Rebuilt successfully (`go build -o wakectl ./...`) and confirmed `--keycodes` runs. Later moved the directory up one level to `/srv/repo/wakectl`.

### 3.3 READMEs and initial GitHub push

Wrote a `README.md` for each repo describing the binary and its behavior. Pushed all four to GitHub as private repos under `thsigit` on `main`, with `origin` set to the SSH URL for future pushes.

### 3.4 Prune stale GitHub repositories

Reviewed the `thsigit` account. Deleted five repos via the GitHub web UI (the device/API delete was blocked at the time): `electron-tabs`, `electron-quick-start`, `consolectl`, `G0DM0D3`, `simple-desktop-app-electronjs`. `consolectl` was superseded by `wakectl`.

### 3.5 Polish: LICENSE, .gitignore, CI

Added an MIT `LICENSE` and a `.gitignore` to each repo and pushed them. Added a GitHub Actions workflow to each:

- `wakectl`: Go build, vet, and test.
- `bitrouter` / `opennds` / `litellm-cli`: `nix-instantiate --parse` of the Nix files via `cachix/install-nix-action`.

The CI commits were initially blocked from pushing (see 3.7) and pushed later once the scope was granted.

### 3.6 Umbrella repo

Created `/srv/repo/homelab`, a flake that aggregates `bitrouter`, `opennds`, and `litellm-cli` as GitHub inputs and re-exports them as packages, plus a `README.md` documenting the repo topology and how `nix-lab` could switch from local path inputs to GitHub inputs. Pushed as `thsigit/homelab`.

### 3.7 GitHub token scope saga

The `gh` CLI token (an OAuth token, `gho_...`) lacked the `workflow` and `delete_repo` scopes. GitHub rejects pushing Actions workflow files and deleting repos without those scopes. Attempts to complete `gh auth refresh` in the agent shell failed because that environment has no browser or TTY for the device-code flow. The user instead created a classic Personal Access Token (PAT, `ghp_...`) with `repo`, `workflow`, `delete_repo`, and related scopes, and stored it with `gh auth login --with-token`. The four CI workflows were then pushed successfully.

### 3.8 Multi-machine authentication topology

Established per-machine auth:

- WSL2: `gh` with the PAT (CLI and repo admin).
- Windows Git Bash: `git` with Git Credential Manager storing the same PAT for HTTPS remotes.
- homelab: a dedicated Ed25519 SSH key added to the GitHub account; server-side pushes use SSH, so no secret is stored on the server.

## 4. Diagnosis

Why did `gh auth refresh` report success three times without changing scopes? `gh auth refresh` with no `-s` flag re-grants the exact same scopes the token already held, so the token was unchanged. Adding scopes requires an explicit, complete scope list: `gh auth refresh -s repo,read:org,gist,admin:public_key,workflow,delete_repo`. Additionally, the GitHub CLI OAuth app's allowed scope set may not include the higher-risk scopes, which is why a PAT (not constrained by the app) was the reliable path.

## 5. Fix

- Created a classic PAT with the needed scopes and stored it via `gh auth login --with-token`.
- Generated an Ed25519 SSH key on homelab, registered the public key with the GitHub account via the API, and configured `~/.ssh/config` to use it for `github.com`.
- For Windows Git Bash, cloned the repos over HTTPS and stored the PAT in GCM.

## 6. Verification

- `gh auth status` now lists `workflow` and `delete_repo`.
- The four CI workflows pushed cleanly to `main` on each repo.
- `ssh -T git@github.com` from homelab returns `Hi thsigit! You've successfully authenticated`.
- `git ls-remote https://github.com/thsigit/homelab.git` from Windows Git Bash succeeds.

## 7. Recommendations

- Keep one token or key per machine so a compromise is contained and revocation is granular.
- Prefer an SSH key on servers (homelab) so no PAT lives on the box.
- When refreshing `gh` scopes, always pass the full `-s` list; a bare `gh auth refresh` changes nothing.
- Set a PAT expiration (max 365 days) and rotate.

## 8. Pending Actions

- Optionally generate a separate `windows` PAT distinct from the WSL2 one.
- Consider switching `nix-lab` from local path inputs to GitHub inputs (`github:thsigit/...`) so the system config no longer depends on the local checkout layout.
- Push a real end-to-end commit from each environment as a final smoke test.
