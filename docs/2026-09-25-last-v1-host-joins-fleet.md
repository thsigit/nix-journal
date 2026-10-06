# Windows OpenCode V2 Migration (or: The Last V1 Host Joins the Fleet)

**Date:** 2026-09-25  
**Author:** Codebot  
**Topic:** opencode-v2, windows, scoop, wsl, plugins, mcp, managed-service

---

## 1. Objective (or: Retire the Last V1 Outpost)

The objective was straightforward in theory: move Windows native OpenCode from
v1.18.32 to the V2 toolchain already running in FedoraWSL and DebianWSL.

In practice, "upgrade OpenCode" meant reconciling four different things at once:

- The Windows Scoop installation and its stale `versions` bucket.
- A V1 configuration layout that included a per-OS overlay.
- V1 plugin dependencies and task files that did not match the V2 layout.
- A Windows managed service that shared the localhost landscape with WSL.

The target was not a compatibility shim. It was a clean V2 installation using
the canonical hub at `/mnt/c/users/sigit/git/opencode-v2/` and its homelab
mirror at `/srv/repo/opencode-v2-hub/`.

## 2. Background (or: The Host at the End of the V1 Line)

Before the migration, the four-host fleet looked like this:

| Host | Before | Target |
|---|---|---|
| Windows native | OpenCode 1.18.32 from Scoop main bucket | OpenCode 2.0.16 from `versions/opencode2` |
| Windows config | V1 config plus `opencode.windows.json` | Canonical V2 config, no overlay |
| Windows tasks | V1 flat task files | `C:\Users\sigit\.opencode\tasks\` with `active/` and `archive/` |
| Windows plugins | V1 `@opencode-ai/plugin` dependency | V2 `@opencode/plugin` 2.0.16 |
| Windows service | Default managed-service behavior | Dedicated port 49576 |
| Shared config | Drift risk between hosts | Canonical V2 hub |

The Windows host was the last V1 member of the fleet. This is the sort of fact
that sounds like a status update but behaves like a final boss with a health bar.

## 3. Problem (or: Why Copying Files Was Not a Migration)

V1 and V2 share some filenames, which creates the dangerous illusion that a
folder copy is sufficient. It is not. The important pieces changed shape:

| Concern | V1 behavior | V2 behavior |
|---|---|---|
| Configuration | `opencode.json` plus `OPENCODE_CONFIG` overlay | Native V2 global configuration |
| Plugin dependency | `@opencode-ai/plugin` | `@opencode/plugin` |
| Plugin loading | Explicit V1 entry points | V2 plugin discovery and APIs |
| Tasks | Flat legacy files | `active/` plus `archive/` task tree |
| Service settings | Host-specific files and environment | Host-local service configuration |

There were also two Windows-specific traps:

1. The Scoop `versions` bucket was stale and had no usable local checkout.
2. Bun's default hardlink backend failed on the drvfs-mounted Windows config
   directory with `EPERM` errors. The dependency was present only after using
   Bun's copyfile backend.

A third trap was quieter: the WSL loopback relay made the default OpenCode
service port appear occupied on Windows. The service was not broken; it was
trying to occupy a number already claimed by the wider WSL networking picture.

## 4. Work Performed

### 4.1 Backup and scope control

A Windows V1 backup was not strictly required for the requested toolchain-only
migration, but it was inexpensive insurance and was created before removing
the old binary:

- `/srv/repo/wsl-reset/windows-reset/config/`
- `/srv/repo/wsl-reset/windows-reset/data/`
- Backup commits: `e42326b` and `e92cfac`

The backup repository excluded secrets from git. The backup was treated as a
rollback aid, not as a second source of truth.

### 4.2 Scoop toolchain migration

The installed Scoop version did not support the task's originally documented
`scoop bucket update versions` command. The broken bucket was therefore removed
and re-added from its canonical source:

```powershell
scoop update
scoop bucket rm versions
scoop bucket add versions https://github.com/ScoopInstaller/Versions
scoop uninstall opencode
scoop install versions/opencode2
```

The resulting Windows binary was:

```text
opencode v2.0.16
```

The command path now resolves to the Scoop V2 shim. A separate Cherry Studio
binary remains installed elsewhere in the Windows PATH, but the default
`opencode` command is the Scoop V2 binary.

### 4.3 Configuration and task migration

The canonical V2 files were copied from:

```text
/mnt/c/users/sigit/git/opencode-v2/
```

The Windows host received:

- Native V2 `opencode.json`
- `package.json`
- `machines.md` and `CONTEXT.md`
- Four V2 plugins
- V2 skills
- V2 task tree at `C:\Users\sigit\.opencode\tasks\`

The obsolete `opencode.windows.json` file and the user-level
`OPENCODE_CONFIG` variable were removed. The configuration and package hashes
were spot-checked against the hub.

### 4.4 Dependencies, service settings, and secrets

The first Bun install failed on drvfs while moving hardlinked temporary files.
The successful Windows-specific command was:

```powershell
Set-Location "$env:USERPROFILE\.config\opencode"
bun install --backend=copyfile --no-cache --cache-dir="$env:TEMP\opencode-bun-cache"
```

Afterward:

- `bun.lock` existed.
- `@opencode/plugin` 2.0.16 was installed.
- The four local plugins were active through the V2 API.

The four host-local service environment keys were transferred without printing
their values. The current gws token was synchronized from Debian, and the
temporary `.opencode-secrets.env` file was removed after the Windows service
and MCP connections were verified.

The Windows managed service was assigned port 49576. This avoids the default
port collision observed through the WSL relay.

### 4.5 Security handling during verification

A diagnostic API response expanded the environment-backed mem0 header and
printed its resolved value in the tool output. Separately, the Windows
`opencode service set env` command line was found to have recorded secret
arguments in the OpenCode log. No secret values are reproduced in this report.

The Windows log was cleared after the service environment was configured and
before the final service restart. The credentials should still be treated as
exposed and rotated; removing a log does not un-ring the bell.

### 4.6 Final interactive verification

The final verification was performed in a real Windows OpenCode session rather
than inferred solely from package files:

- gws connected.
- mem0 connected.
- The model list under `/models` was correct.
- The V2 skill list was correct.
- The task-manager plugin worked and returned the real task index.
- A real provider request using `nvidia/meta/muse-glimmer-30b` returned `pong`.
- The V2 API reported four active local plugins: `model-whitelist`,
  `google-workspace`, `opencode-task-manager`, and `self-improving-skills`.

The CLI command `opencode plugin list` reports npm-installed plugins and showed
none on this host. That is not a V2 plugin failure; the `/api/plugin` endpoint
and the interactive session are the authoritative checks for configured local
plugins.

## 5. Diagnosis (or: Four Failures, One Root Cause)

The migration failures were not mysterious. They were ordinary consequences of
crossing too many boundaries at once:

1. **Scoop bucket drift:** the `versions` bucket had no usable checkout, so the
   V2 manifest was unavailable.
2. **V1 layout leakage:** the overlay and V1 task tree were still present after
   the binary changed.
3. **drvfs filesystem behavior:** Bun hardlinks failed on the Windows-mounted
   filesystem, requiring the copyfile backend.
4. **Shared localhost networking:** the default managed-service port collided
   with a listener visible through WSL networking.

The V2 binary itself was healthy once the toolchain, config, dependency, and
service-port assumptions were aligned.

## 6. Preliminary Assessment

The migration is complete. Windows native is now a normal V2 host rather than
an archaeological site where V1 files sit beside a V2 executable.

The important result is not merely that `opencode --version` prints 2.0.16. A
real interactive session loaded the expected models, skills, MCP servers, and
task manager. That is the difference between a successful installer run and a
usable OpenCode installation.

## 7. Solution Summary

| Component | Final state |
|---|---|
| Windows binary | OpenCode v2.0.16 via Scoop `versions/opencode2` |
| Canonical config | `/mnt/c/users/sigit/git/opencode-v2/` |
| Windows config | `C:\Users\sigit\.config\opencode\` |
| Windows tasks | `C:\Users\sigit\.opencode\tasks\` |
| Plugin dependency | `@opencode/plugin` 2.0.16 |
| Local plugins | Four active V2 plugins |
| Managed service | `127.0.0.1:49576` |
| MCP | gws connected; mem0 connected |
| Temporary secrets file | Removed |
| Hub documentation | Updated in `README.md` and `machines.md` |
| Task record | Archived as `TASK-upgrade-windows-opencode-v1-to-v2_2026-09-25.md` |

The hub and documentation update was committed and pushed as:

```text
316a80b docs: complete Windows OpenCode v2 migration
```

## 8. Verification Plan

- [x] `opencode --version` is 2.0.16 on Windows.
- [x] The V1 overlay and `OPENCODE_CONFIG` export are absent.
- [x] Canonical V2 config and tasks are installed.
- [x] `@opencode/plugin` 2.0.16 and `bun.lock` are present.
- [x] The managed service is healthy on port 49576.
- [x] gws is connected.
- [x] mem0 is connected.
- [x] Models are correct in an interactive Windows session.
- [x] V2 skills are listed correctly.
- [x] The task-manager plugin returns the real task index.
- [x] A real provider request returns a response.
- [x] The completed task and hub documentation are committed and pushed.

## 9. Pending Actions

These are follow-up items outside the completed Windows migration:

1. Rotate the Google OAuth client credentials that were exposed earlier.
2. Rotate the mem0 credential as a precaution because diagnostic output exposed
   its resolved value.
3. Decide whether to explicitly whitelist the five `opencode/*` free models.
4. Keep the Windows V2 configuration synchronized through the canonical hub,
   not through a Windows-specific overlay.

## 10. Recommendations

1. Treat the canonical hub as a git repository and use commits and pushes for
   shared configuration. Do not use an ad-hoc directory copy as a migration
   strategy.
2. Keep secrets host-local in service configuration. Never put resolved secret
   values in the hub, logs, task files, or reports.
3. On drvfs, prefer Bun's copyfile backend and a local temporary cache when
   dependency installation reports `EPERM` or hardlink failures.
4. Pin a distinct managed-service port for every host that may be visible
   through WSL networking. A port collision is not always a local process
   problem.
5. Verify migrations in the actual interactive client. Package managers,
   configuration hashes, and API endpoints are useful, but a real session is
   the final smoke test.
6. Rotate anything that appeared in diagnostic output. Deleting the log is
   cleanup; rotation is the actual remedy.

Generated with Space Bunny Free by OpenCode
