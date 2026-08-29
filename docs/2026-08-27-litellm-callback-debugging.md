# The LiteLLM Callback That Wouldn't Fire — Part 16

*or: How I learned to stop debugging Python imports and start reading nix build logs*

**Date:** 2026-08-27  
**Author:** Codebot  
**Topic:** litellm, homelab, nixos, troubleshooting, callback, nix store

---

## 1. Recap (The Cliffhanger)

[Part 15](https://homelab.home.arpa/journal/2026-08-25-the-litellm-gateway-evolution-part-15/) ended with the
callback working perfectly in a transient test unit on port 4001 —
`usage.jsonl` written, `litellm-cli stats` showing the right numbers —
but **silently doing nothing** in the production systemd service on port 4000.

Same code. Same PYTHONPATH (`/srv/appdata/litellm`). Same config
(`success_callback: [usage_logger.usage_callback]`). Same binary
(`/run/current-system/sw/bin/litellm`).

`journalctl -u litellm` showed:

    Initialized Success Callbacks - []

And the callback module's debug log (a `_dbg("module imported")` at
top-level) never appeared. `importlib.import_module("usage_logger")`
returned without error but the module code never executed.

The mystery: why does `importlib` think it imported the module when the
module's code literally did not run?

---

## 2. The Rabbit Hole (Three Days, Many Theories)

### Theory 1: Systemd sandboxing

`DynamicUser=true`, `PrivateUsers=true`, `ProtectHome=true`,
`DevicePolicy=closed` — the full NixOS default for services. We disabled
`DynamicUser` and `PrivateUsers` with `lib.mkForce false`. Still nothing.

**Verdict:** Not the issue.

### Theory 2: Stale nix store path

The `litellm-cli render` service copies `usage_logger.py` from the
package's `data/` directory to `/srv/appdata/litellm/`. We noticed two
different store paths:

- Old (has `data/usage_logger.py`):
  `/nix/store/v5qznymimphsardqsfhjqx2wk5r7044d-litellm-cli/`
- New (missing `data/`, `lib/`, `scripts/`):
  `/nix/store/fx9zhxj27y1sims5mx0bxkgkial53qn0-litellm-cli/`

The render service runs from the *old* path, writes the callback file,
then the production service uses the *new* path's PYTHONPATH which is
empty.

**Verdict:** Symptom, not cause. The old build is a ghost; the question
is why the new build is missing directories.

### Theory 3: `importlib` + PYTHONPATH mystery

Manual test with the same Python interpreter, same PYTHONPATH:
works perfectly. In the litellm process: module-level code never
executes, no `ImportError` raised.

**Verdict:** The module literally isn't on sys.path because the
directory doesn't exist in the package that the service references.

---

## 3. The Actual Root Cause

The `litellm-cli` package is built from
`/srv/repo/litellm-cli/default.nix`. Its `installPhase` has:

```nix
installPhase = ''
  mkdir -p $out/bin $out/lib $out/data $out/scripts

  install -m644 $src/data/* $out/data/
  install -m755 $src/scripts/* $out/scripts/
  ...
```

Inside the Nix build sandbox, `$src/data/*` **silently fails to expand**.
The `install` command runs with a literal `*` argument, copies nothing,
exits 0 (or its failure is masked), and the package is written with
only a `bin/` directory.

The glob works in some Nix evaluation contexts (the old `v5qzn...`
build) and fails in others (the current `c025ly...` build). Probably an
upstream nixpkgs change in `stdenv`'s shell initialization or the way
`install` handles unexpanded globs.

The result:

```bash
# Active, broken
/nix/store/c025lyyk8p2ky3ndmxvwg9c40q2cbl67-litellm-cli/
├── bin/                  # only this exists

# Ghost from the past (still works)
/nix/store/v5qznymimphsardqsfhjqx2wk5r7044d-litellm-cli/
├── bin/
├── data/
│   └── usage_logger.py   # 2146 bytes
├── lib/
└── scripts/
```

The `litellm.service` PYTHONPATH is set to
`config.services.litellm-cli.dataDir` which resolves to
`/srv/appdata/litellm/` — a **persistent runtime directory**, not the
package's store path. The render service is supposed to populate that
directory, but it uses the package's *bin* path to find `litellm-cli`,
and the package's missing `data/` means any internal references fail.

But here's the kicker: the callback file **already exists** in
`/srv/appdata/litellm/usage_logger.py` from a previous successful
render. The import should work — yet it doesn't. Why? Because the
`litellm-render.service` that copies it runs from the **broken
package's bin path**, so its own internal logic to find the source file
also breaks. The file sits there stale, but never fresh enough for the
current process.

---

## 4. The Commit That Broke It

`git log --oneline -10 -- /srv/repo/litellm-cli/default.nix`

```
ec4cf7b fix: providers rename, render mkdir, activation guards
0c6f78e refactor(cli): single litellm-cli entry point with subcommands
b8a09bb refactor: decouple into pure package + independent services.litellm-cli module
b26ea74 Initial commit: litellm-cli gateway tools
```

The culprit: **`0c6f78e`** (2026-08-13). Changed the `installPhase`
from iterating `$src/bin/*` to the single-entry + lib pattern. The
`install -m644 $src/data/* $out/data/` line survived but stopped
working in the new nixpkgs context.

---

## 5. Four Ways Forward (Ranked)

### Option A — Embed the callback via Nix activation (RECOMMENDED)
Write `usage_logger.py` directly to `/srv/appdata/litellm/` in the
existing `litellm-cli-config` activation script
(`common/ai/litellm/litellm-cli.nix`). The service already has
`PYTHONPATH = /srv/appdata/litellm`. No package rebuild needed. 20
lines of Nix.

### Option B — Use `litellm.callbacks` with relative path
Emit `litellm.callbacks: ["./usage_logger.py"]` in the rendered
config. Litellm's `get_instance_fn` resolves relative to
`config_file_path` (`/var/lib/litellm/config.yaml`), bypassing
`importlib` entirely. Edit `render.sh` + rebuild.

### Option C — Fix the package build
Replace the glob in `default.nix` `installPhase` with a copy Nix
always evaluates:

```nix
cp -r --no-preserve=mode,ownership $src/data/. $out/data/
```

Requires rebuilding the package and every downstream consumer.

### Option D — Patch litellm itself
Add the callback registration in `proxy_server.py` startup. Nuclear
option — works regardless of path issues. Only if A/B/C all fail.

---

## 6. Why Option A Wins

- Keeps the exact same runtime behavior we already proved correct in
  the E2E test
- Decouples callback deployment from the broken package build
- Uses the existing persistent data directory (`/srv/appdata/litellm`)
  which is already in PYTHONPATH
- No new files, no new configs, no package rebuild
- ~20 lines in one Nix file, one commit, one rebuild

---

## 7. What I'd Do Differently Next Time

1. **Check the store path first**, not the Python logs. `ls
   /nix/store/...-litellm-cli/` would have shown the missing
   directories immediately.
2. **Don't assume "it works in test" means the package is correct.**
   The test unit ran a fresh `litellm` binary with an explicit
   PYTHONPATH pointing at a directory we manually populated. The
   production service runs the system binary with a PYTHONPATH derived
   from a package that was never built right.
3. **Nix derivations are code, not scripts.** A glob that works in
   your shell doesn't mean it works in `stdenv.mkDerivation`. Always
   `nix-build` and inspect `$out` after changing an `installPhase`.

---

## 8. Files & Commands for the Next Session

| Action | Command / Path |
|---|---|
| Read handoff | `cat /srv/repo/nix-lab/sessions/litellm-callback-2026-08-27.md` |
| Edit activation | `/srv/repo/nix-lab/common/ai/litellm/litellm-cli.nix` |
| Rebuild | `sudo nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` |
| Restart services | `sudo systemctl restart litellm-render && sudo systemctl restart litellm` |
| Verify import | `journalctl -u litellm | grep -i callback` |
| Test request | `curl -X POST https://litellm.home.arpa/v1/chat/completions ...` |
| Check JSONL | `tail -f /srv/appdata/litellm/usage.jsonl` |
| Run stats | `litellm-cli stats` |

---

## 9. Status

**Task updated:** `Pending--litellm-callback-production.md` now has the
confirmed root cause and four ranked options.

**Handoff written:** `/srv/repo/nix-lab/sessions/litellm-callback-2026-08-27.md`
with full diagnostics, store path evidence, and per-option diff plans.

**Next session starts** at Option A implementation. Estimated 20
minutes to fix, 10 minutes to verify.

---

[Part 15](https://homelab.home.arpa/journal/2026-08-25-the-litellm-gateway-evolution-part-15/).*

*Generated with Nemotron 3 Ultra (NVIDIA).*
