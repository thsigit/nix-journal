# Two-Channel Repo Strategy: nix-config (Stable) and nix-lab (Rolling)

**Date:** 2026-08-16  
**Author:** Codebot  
**Topic:** NixOS, homelab, architecture, git, workflow, migration, refactor  

---

## 1. Objective

Document the current repository strategy that has evolved since the 2026-08-05 report "Archiving Nix Lab And Restoring Nix Config As The Active Repo" (left untouched as history):

1. **nix-config** is the main/stable channel. **nix-lab** is the rolling channel where all experiments are conducted.
2. Eventually the two are merged, and the resulting nix-config is pushed to GitHub.

This report records the current status, the two-channel architecture, how changes flow between the channels, and the merge/publish plan.

## 2. Background

The 2026-08-05 report was accurate at the time: nix-lab was archived **temporarily** because it caused the first "switch root target contains no usable init" boot failure (the incident documented in "Boot Recovery - Part 1", 2026-08-03). While nix-lab was archived, builds and development continued from nix-config. The work was eventually merged back into nix-lab, which is again the live rolling channel: the running system (generation 142) is currently built from `nixos-rebuild switch --flake /srv/repo/nix-lab#workstation`. The two repos now coexist as separate channels of the same configuration.

## 3. Current status

Verified from the repositories on 2026-08-16:

| Repo | Channel | Layout | Files | Git state | Origin |
|------|---------|--------|-------|-----------|--------|
| `/srv/repo/nix-config` | stable | `modules/{ai,caddy,core,media,monitoring,network,security,storage}`, `profiles/{failsafe,server,workstation}`, `pkgs/`, `machines/` | 118 | `main`, ahead 9 of origin/main | `github.com/thsigit/nix-config.git` |
| `/srv/repo/nix-lab` | rolling | `common/{ai,ap,db,mail,media,monitoring,network,packages,storage,web}` (mrtg-style leaves), `profiles/{failsafe,server,system,workstation}`, `system/`, `sessions/` | 105 | `main`, ahead 54 of origin/main, uncommitted WIP | `github.com/thsigit/nix-config.git` |

Key facts:

- Both repos declare the **same GitHub origin** (`github.com/thsigit/nix-config.git`), but their histories are **unrelated** (no common ancestor): `git merge-base` between the two HEADs fails. A merge is a real reconciliation, not a fast-forward.
- nix-lab carries **uncommitted work in progress** from this session: `common/ai/litellm-cli.nix` (boot-fix activation prep), `common/ai/default.nix` (litellm-podman-helper disabled during bisect), `ssl/homelab-ca.crt` (deleted).
- nix-lab is the **live build source** (current system generation 142) and the home of recent refactors: the mrtg-style `common/` leaf layout, the LiteLLM CLI decouple, and the access-point bundle work.
- nix-config keeps the older `modules/` layout and is ahead of origin by only 9 commits (mostly `auto: update model inventory` commits), i.e. close to the published state.
- Both `WORKING.md` files still open with the header "nix-lab operating notes", and nix-config's copy still describes the `modules/` layout while nix-lab has moved on to `common/` - stale markers that the merge will have to reconcile.

## 4. Architecture

```
experiments ----------> nix-lab (rolling)
  (litellm-cli decouple,
   common/ leaf refactor,     |  when stable
   AP bundle, boot fixes)     v
                      nix-config (stable) --> pushed to GitHub
                                              (github.com/thsigit/nix-config)
```

- **nix-config**: the main, stable channel. Its tree is close to what is published (ahead 9). Work lands here only after it has proven itself.
- **nix-lab**: the rolling channel. All experiments are conducted here - new module layouts, package splits, boot/activation fixes, service relocations - and the box is built from it while those experiments stabilize.
- **GitHub**: both channels track the same remote, but the **published result is nix-config**. nix-lab's 54 unpushed commits are experiment history, not intended for publication as-is.

## 5. Workflow

1. Conduct experiments in `/srv/repo/nix-lab` (mrtg-style `common/` leaves, standalone `/srv/repo` inputs, boot/activation fixes). Verify on the hardware with `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation`.
2. Once stable, promote to `/srv/repo/nix-config` (port the change into the `modules/` layout and commit).
3. Rebuild from nix-config to confirm parity on the live box.
4. Push nix-config to GitHub.

## 6. Plan: merge and publish

- Eventually the two channels are merged into a single repository. The merge must reconcile: (a) the unrelated histories, (b) the `modules/` vs `common/` layout divergence, (c) nix-lab's unpushed experiment commits (which become the rolling history), and (d) stale docs (`WORKING.md` headers, layout references).
- After the merge, nix-config is pushed to GitHub (`https://github.com/thsigit/nix-config.git`) as the canonical published configuration.
- Before merging, the open nix-lab WIP (uncommitted boot-fix from this session) must be committed or carried over, and `ssl/homelab-ca.crt` handling decided.

## 7. Verification status

- Repo facts above verified against the working trees on 2026-08-16 (`git status --branch`, `git remote -v`, `git ls-files`, `git merge-base`).
- The running system (generation 142) is confirmed to have been built from `/srv/repo/nix-lab#workstation`.
- The merge itself has not been performed; this is the forward plan.

## 8. Recommendations

- Keep nix-lab's uncommitted work in progress committed and clearly documented before any merge work begins.
- Perform the merge as a port of nix-lab's stable `common/` leaf layout into nix-config, deciding the canonical layout once (recommend the mrtg-style `common/` leaves, since it is the newer, self-enabling convention).
- Update the stale `WORKING.md` headers and layout references as part of the merge.
- Decide the GitHub publish scope: nix-config becomes the public stable tree; keep nix-lab's experiment history out of it or fold it in deliberately.

## 9. Relevant files

- `/srv/repo/nix-config/` - stable channel (flake.nix, modules/, profiles/, pkgs/, machines/, secrets/).
- `/srv/repo/nix-lab/` - rolling channel (flake.nix, common/, profiles/, system/, sessions/).
- `/srv/repo/nix-config/README.md` - describes the stable config and its machines/profiles.
- `/srv/repo/nix-config/WORKING.md`, `/srv/repo/nix-lab/WORKING.md` - operating notes (headers/layout stale).
- `2026-08-05-archiving-nix-lab-and-restoring-nix-config-as-the-active-repo.md` - the historical report on the temporary nix-lab archive, kept for history.
