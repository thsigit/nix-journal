# One Repo, One Main, and a Pruned Snapshot (or: The Git Archaeology Nobody Asked For)

**Date:** 2026-09-08  
**Author:** Codebot  
**Topic:** homelab, git, NixOS, workflow, maintenance, refactor, documentation

---

## 1. Objective (or: Untangling a Repo Situation That Made Everyone Squint)

The homelab's repository situation had quietly grown three heads. The owner's
mental model was: work on `/srv/repo/nix-lab` as the dev repo, occasionally
merge into `/srv/repo/nix-config`, push the result to GitHub. Then somewhere
along the line the cast changed - no `nix-config` anymore, just `nix-lab` and
`nix-lab-snapshot`, two branches (`main` and `dev`), commits landing on either
side, and GitHub showing both branches.

This report documents the untangling: the diagnosis, the tree surgery, and the
newly simplified workflow that survived the purge. Plus a bonus archaeology
section on stale comments that had been lying about their own addresses for a
while.

## 2. Background (or: The Legend of a Repo That Was Also a Folder)

The history, condensed:

| Phase | Repos involved | Layout |
| --- | --- | --- |
| Original | `nix-lab` + `nix-config` | Dev repo, release repo, manual `git rm -r` + copy to publish |
| Migration | `nix-lab` | One repo, two branches (`dev` + `main`); `nix-lab-snapshot` kept as a leftover snapshot |
| Now | `nix-lab` | One repo, `dev` local-only + `main` pushed; snapshot gone |

Two past reports bookend this saga: the original 2026-08-05 migration report
("Archiving Nix Lab And Restoring Nix Config As The Active Repo") and, spoiler
alert, this one. Along the way the flake absorbed everything else - AP bundle,
LiteLLM, open-webui - and the repo kept its two-branch workflow. Nobody had yet
noticed that the two-branch workflow itself was now the confusingly redundant
part.

## 3. Problem (or: Two Clones, One GitHub, Zero Clarity)

The symptoms, as reported:

- Only two directories exist now: `nix-lab` and `nix-lab-snapshot`.
- Local branches `main` and `dev` both exist in `nix-lab`, and commits land
  on either one.
- GitHub has both `main` and `dev`.

The three questions that matter:

1. What actually is `nix-lab-snapshot`, and does it need to exist?
2. Why does nothing add up to a clear publish path?
3. Is anything going to be lost when we stop guessing?

## 4. Work Performed

### 4.1 Diagnosis: two clones, one remote (no surprises, just dread)

The first reveal: **both** `/srv/repo/nix-lab` and `/srv/repo/nix-lab-snapshot`
point at the same GitHub repo, `git@github.com:thsigit/nix-config.git`. There
is no third repo. The "occasionally merge to nix-config" step had silently
become "occasionally get confused by a second clone."

In `nix-lab`, the local `dev` branch was tracking `origin/main` instead of
`origin/dev` - a classic "just following orders to the wrong address" setup.
Both remote branches sat at the same commit `228da7d`, so content-wise nothing
had diverged. The confusion was purely a topology problem.

| Branch | Before | After |
| --- | --- | --- |
| `dev` | tracked `origin/main` | tracks `origin/dev` (then unset) |
| `main` | no upstream | tracks `origin/main` |

### 4.2 Loving the snapshot to death (they said no backup)

`nix-lab-snapshot` was an occasional snapshot left over from the old
`nix-config` release method, clean at `eba912a`. Its history was already
preserved in `main`. Decision: delete it. The owner was asked and answered:
Option B, remove, **no backup**. The folder, her feelings, and its 10 GiB of
NixOS history left together.

```
rm -rf /srv/repo/nix-lab-snapshot
```

### 4.3 GitHub loses a branch (dev stays home)

GitHub held both `main` and `dev` at the same commit. Since `dev` is only ever
meant to be a local workspace, the remote `dev` was pushed into oblivion:

```
git push origin --delete dev
git remote prune origin
git branch --unset-upstream dev
```

Result: GitHub has exactly one branch (`main`), the local `dev` has no upstream
to drift toward, and nobody can push to a ghost branch accidentally.

### 4.4 Stale .md references (the docs confess)

Three docs carried old-world assumptions:

| File | Stale content | Fix |
| --- | --- | --- |
| `WORKFLOW.md` | described the two-branch-published-to-GitHub setup, mentioned the removed snapshot | rewritten for `dev` local-only + `main` published |
| `AGENTS.md` | referenced `nix-lab-snapshot` as a live path | line updated |
| `AGENTS.md` | missing the publish command | added explicit publish flow |

Plus: the opencode `boot-management` skill still said "`/srv/repo/nix-config`
is archived - never edit it." That repo does not exist anymore. Updated to
"one repo, consolidated."

### 4.5 Stale .nix header comments (the comments confess too)

An automated sweep of first-line comments against actual file paths turned up
six files whose headers claimed an address they no longer lived at:

| File | Old header | Fixed |
| --- | --- | --- |
| `system/sudo.nix` | `common/security/sudo.nix` | `system/sudo.nix` |
| `system/kernel.nix` | `common/core/kernel.nix` | `system/kernel.nix` |
| `system/firewall.nix` | `common/security/firewall.nix` | `system/firewall.nix` |
| `system/boot.nix` | `common/core/boot.nix` | `system/boot.nix` |
| `system/ssh.nix` | `common/security/ssh.nix` | `system/ssh.nix` |
| `system/bluetooth.nix` | `common/media/bluetooth.nix` | `system/bluetooth.nix` |

And the failsafe profile's header still swore it kept `/srv/repo/nix-orig` as
reference. `nix-orig` is also long gone. That sentence was edited right out of
existence.

## 5. Diagnosis (or: It Was Two Clones the Whole Time)

The root cause of the mental muddle was never a git data problem - both remote
branches shared one commit (`228da7d`), no content was lost or diverged. The
muddle was **topology + tracking**:

- Two local clones of the same remote looked like two different repos.
- `dev` was told to track `origin/main`, so every status read lied about where
  it pointed.
- The workflow docs described a `nix-config` world that no longer existed,
  then described a two-branch world that no longer matched reality.

Everything else - stale comments, stale skill text, a phantom `nix-orig` - was
just sediment from the same pile-up.

## 6. Solution Summary (or: One Repo, One Pushed Branch, One Command)

The final shape is boring, in the best way:

```
nix-lab
 |-- dev   -> daily development (local-only, no upstream)
 '-- main  -> public release (pushed to GitHub)
```

Publishing is now a single chain, written down in `AGENTS.md` so future agents
cannot forget it:

```
git checkout main && git merge dev && git push origin main && git checkout dev
```

GitHub: one branch. Local: two branches, one of which never leaves home.

## 7. Verification (or: Proof, Not Vibes)

- `git branch -vv`: `dev  6e9b0aa` (no upstream), `main 228da7d [origin/main]`.
- `git ls-remote origin`: exactly one head (`refs/heads/main` at `228da7d`),
  plus the pre-existing `pre-ap-gateway` tag and one PR ref.
- `git status`: clean, on `dev`.
- No occurrences of `nix-orig`, `nix-config` as a live path, or the removed
  snapshot anywhere in `.nix` or fetchable `.md` text.

## 8. Pending Actions

None forced. The `boot-management` skill notes that a stale `SKILL.md.backup`
copy still holds the old `nix-config` line - it is a historical backup, left
alone on purpose.

## 9. Recommendations

1. **`dev` stays local forever.** If a push to GitHub ever asks about `dev`,
   the answer is no. Mirror the four-command publish flow everywhere it lives.
2. **Skills are code.** When paths or repos move, the `homelab-management`,
   `boot-management`, and startup context need the same sweep as the source
   files. This session did the sweep; future migrations should too.
3. **One clone beats two clones.** A second checkout of the same remote only
   ever causes "which repo am I in?" stories at parties.
4. **Probe first, panic later.** Nothing was actually lost here - checking the
   remote refs and tracking state before touching anything made the whole
   operation a set of small, reversible steps.
5. **Header comments owe their readers a true address.** If a file moves, the
   first line moves with it.

---

Generated by Big Pickle (OpenCode)