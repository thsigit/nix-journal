# NixOS OpenCode V2 Upgrade Attempt (or: The NPM Binary Was a Bun in Disguise)

**Date:** 2026-09-28  
**Author:** Codebot  
**Topic:** opencode-v2, nixos, nixpkgs, autoPatchelfHook, bun, npm, dynamic-linking, flake

---

## 1. Objective (or: Upgrade the Last V1 Host Without Breaking the Fleet)

The homelab NixOS workstation was the last host running OpenCode v1.18.32. The
Windows, FedoraWSL, and DebianWSL hosts had already migrated to v2. The goal:
upgrade the NixOS host to v2 via the flake, keeping the opencode systemd
service and Caddy reverse proxy working.

The existing setup at commit `47ea14e` wired opencode as a GitHub flake input
(`github:anomalyco/opencode`), which resolved to the main branch -- v1.18.32.
The task was to switch to v2.

## 2. Background (or: V2 Is Not on GitHub, It Is on NPM)

OpenCode v2 is not published as a GitHub release or a tagged branch. The only
official distribution channel is the install script:

```bash
curl -fsSL https://opencode.ai/v2/install | bash
```

That script downloads from the npm registry: `@opencode/cli-linux-x64` (and
platform-specific variants). The npm package `version` field reads `2.0.18`.

The install script:
- Fetches metadata from `https://opencode.ai/update/api/latest/cli/npm`
- Downloads the platform tarball from `registry.npmjs.org`
- Extracts `package/bin/opencode` to `~/.opencode/bin/`
- Adds `~/.opencode/bin` to PATH via shell rc file

On standard Linux this works. On NixOS, it fails with "Could not start
dynamically linked executable" because the binary expects
`/lib64/ld-linux-x86-64.so.2`, which does not exist on NixOS.

## 3. Problem (or: Three Failed Approaches Before the Nix Derivation)

### 3.1 Direct `curl | bash` install
Binary installs but fails to run -- dynamic linker mismatch.

### 3.2 `npm install -g @opencode/cli`
Fails because npm's default prefix points into the read-only Nix store.
Setting `npm config set prefix ~/.local` works for installation but the binary
is the same unpatched ELF.

### 3.3 `npm install -g @opencode/cli-linux-x64` (direct platform package)
Installs successfully but the binary still fails with the same dynamic linking
error.

The meta-package `@opencode/cli` runs a `postinstall.mjs` to detect platform
and install the appropriate binary. That script also fails on NixOS.

## 4. Work Performed

### 4.1 First Nix derivation attempt (commit 15400e2)

Created `common/ai/opencode-v2.nix` fetching the npm tarball with
`autoPatchelfHook`:

```nix
pkgs.stdenv.mkDerivation {
  name = "opencode-v2-2.0.18";
  src = fetchurl { url = tarballUrl; sha256 = "sha256-qkVdBzs6BzOmkS9HezcPPVDKevRHFbt8zEH6oTs8wus="; };
  nativeBuildInputs = [ pkgs.gnutar pkgs.gzip pkgs.autoPatchelfHook ];
  dontConfigure = true;
  dontBuild = true;
  installPhase = ''
    mkdir -p $out/bin
    tar -xzf $src -C $out/bin --strip-components=2 package/bin/opencode
    chmod +x $out/bin/opencode
  '';
  autoPatchelf = true;
}
```

Updated `flake.nix` to provide `opencodeV2` via this local package instead of
the GitHub flake input. Updated `common/ai/opencode.nix` to use `opencodeV2`.

Build succeeded. Binary ran. But:

```bash
$ opencode --version
1.4.2
$ opencode --help
Bun is a fast JavaScript runtime...
```

The binary reported **Bun 1.4.2**, not opencode v2.0.18.

### 4.2 Discovery: the npm binary is a Bun wrapper with `argv[0]` detection

Tested the original npm binary directly:

```bash
$ ./package/bin/opencode --version
opencode v2.0.18
$ cp package/bin/opencode ./bun && ./bun --version
1.4.2
```

The exact same file behaves differently based on `argv[0]`:
- `opencode` -> shows opencode v2.0.18
- `bun` -> shows Bun 1.4.2

`autoPatchelfHook` patches the ELF interpreter to NixOS's glibc. This
modification breaks the `argv[0]` detection logic inside the Bun-compiled binary,
causing it to default to "Bun mode".

### 4.3 Reversion to v1 (commit 47ea14e)

Since v2 is in beta and constantly changing, and the npm binary is
fundamentally a Bun wrapper (not a native opencode binary), reverted to the
working v1.18.32 from the GitHub flake input.

The v1 package from `github:anomalyco/opencode` (main branch) builds and runs
correctly on NixOS:

```bash
$ opencode --version
1.18.32+b471c2b
```

## 5. Diagnosis

| Layer | Finding |
|---|---|
| npm `@opencode/cli-linux-x64` | Single ELF binary compiled with Bun, dual-personality via `argv[0]` |
| `autoPatchelfHook` | Patches interpreter path, breaks internal `argv[0]` check |
| NixOS dynamic linking | Requires patched interpreter; unpatched binary fails to start |
| GitHub `anomalyco/opencode` main branch | v1.18.32, not v2 |
| v2 source | Only via `github:anomalyco/opencode` v2 branch (not npm) |

The npm packages are **distribution artifacts for standard Linux**, built by
Bun's compiler. They are not the native opencode v2 binary. The actual v2
source lives in the `v2` branch of the GitHub repo.

## 6. Verification Status

| Configuration | Commit | opencode version | Status |
|---|---|---|---|
| v2 via npm + autoPatchelfHook | 15400e2 | 1.4.2 (Bun) | **Broken** -- `argv[0]` detection broken |
| v1 via GitHub flake | 47ea14e | 1.18.32+b471c2b | **Working** -- systemd service, Caddy proxy, MCP all functional |
| Current (reverted) | 47ea14e | 1.18.32+b471c2b | **Deployed** -- `nixos-rebuild switch` completed |

## 7. Post-Session Verification: v2 Branch Exists on GitHub (Added 2026-09-28)

After the session, verified that `github:anomalyco/opencode/v2` exists and is
a proper flake with buildable packages:

```bash
$ git ls-remote https://github.com/anomalyco/opencode.git 'refs/heads/v2'
c0d49f101c3079f4fb3f08af4026fb5cb0873745  refs/heads/v2

$ nix flake show github:anomalyco/opencode/v2
packages.x86_64-linux.opencode       -> opencode-2.0.18+c0d49f1
packages.x86_64-linux.opencode-desktop -> opencode-desktop-2.0.18+c0d49f1
```

Tags include `v2.0.0` through `v2.0.18` (matching the npm package version).

**Conclusion for the report's recommendation**: The v2 branch is real and
buildable from source via Nix. The correct path for NixOS v2 is:

```nix
inputs.opencode = { url = "github:anomalyco/opencode/v2"; };
```

Then use `opencode.packages.${system}.opencode` in the systemd service.

**However, we stay on v1** because:
- v2 is still in beta (version 2.0.18, frequent updates)
- The npm distribution is a Bun wrapper, not the native binary
- v1.18.32 from the main branch is stable and works correctly on NixOS
- The homelab MCP stack (mem0, gws, litellm) is verified working with v1

When v2 stabilizes, the migration path is clear: switch the flake input to
the v2 branch and build from source.

## 8. Recommendations

1. **For actual v2 on NixOS**: Use the v2 branch from GitHub as a flake input:
   ```nix
   inputs.opencode = { url = "github:anomalyco/opencode/v2"; };
   ```
   Build from source rather than using npm distribution artifacts.

2. **If npm binary must be used**: Avoid `autoPatchelfHook`. Use a targeted
   `patchelf --set-interpreter` in `fixupPhase` that only changes the dynamic
   linker path without touching other ELF metadata that Bun's `argv[0]` check
   depends on.

3. **Accept v1 for stable NixOS hosts**. The GitHub flake input at main branch
   gives a reliable v1.18.32 that integrates cleanly with systemd, Caddy, and
   the homelab MCP stack. v2 is beta; the npm distribution is a Bun wrapper;
   the GitHub v2 branch is the real source.

4. **Document the npm trap**. Future attempts to "just use the npm package" on
   NixOS will hit the same `argv[0]` issue. The binary is not what it appears.

## 9. Relevant Files

| Path | Role |
|---|---|
| `/srv/repo/nix-lab/flake.nix` | Flake with opencode GitHub input (v1) |
| `/srv/repo/nix-lab/common/ai/opencode.nix` | systemd service + Caddy config |
| `/srv/repo/nix-lab/common/ai/opencode-v2.nix` | **Deleted** -- failed v2 derivation |
| `git commit 47ea14e` | Working v1 configuration |
| `git commit 15400e2` | Failed v2 attempt (reverted) |
| `git commit 861a0ae` | Cleanup commit (removed all opencode from nix config) |

## 10. If It Recurs

- Someone tries `curl | bash` on NixOS again -> fails with dynamic linking error
- Someone tries `npm install @opencode/cli` -> fails or produces broken binary
- Someone builds a Nix derivation with `autoPatchelfHook` -> binary runs but
  reports Bun version
- Check `argv[0]` behavior: `cp opencode test && ./test --version` vs
  `./opencode --version`

The fix for real v2: point the flake input at `github:anomalyco/opencode/v2`
and build from source. The npm packages are a distraction.

---

Generated with Nemotron 3 Ultra by NVIDIA
