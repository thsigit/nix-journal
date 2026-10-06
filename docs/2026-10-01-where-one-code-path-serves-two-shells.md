# Command Delivery Across the SSH Hop: Where One Code Path Serves Two Shells

**Date:** 2026-10-01  
**Author:** Codebot  
**Topic:** opencode, fleet-sync, ssh, command-execution, argv-quoting, cross-host, false-verification

---

## 1. Objective

Extend the `fleet-sync` plugin to orchestrate over a live SSH mesh, proving the design with an idempotent run that converges stores and verifies config without manual intervention. The orchestrator must: (a) work on all three hosts over passwordless SSH, (b) respect platform differences in tooling (MD5, Python), and (c) avoid silent failures that masquerade as success.

## 2. Background

The SSH mesh unifies Windows (`Vantage-V14G4`), DebianWSL (`debianWSL`), and FedoraWSL (`fedoraWSL`) so any host can SSH to any other using short names and port-disambiguation (`fedora`:2223, `debian`:2222, `windows`:22). The mesh is passwordless via distributed ed25519 keys. Prior verification showed 9/9 directions working, but durability requires a keepalive task (`WSL keep distros running`) to hold distros open.

`fleet-sync` previously converged only the local host. This session adds cross-host steps by wiring `viaFor(self, target)` to `["ssh", target.token]` and looping steps 2--4 over `[self, ...peerHosts(self)]`.

## 3. The Discovery: Same Code, Three Outcomes

Instrumentation revealed that `runCmd`--the plugin's universal process launcher--behaves differently depending on the target host and whether an SSH hop is involved. The same argv shape led to three classes of outcome over the hop:

| Target & Shape | Result | Why It Matters |
|---|---|---|
| **Windows + joined argv** (`ssh windows "certutil -hashfile X MD5"`) | Exit 0, **empty stdout** (silent no-op) | The command runs but produces no output. A hash comparison would see no difference and falsely report success. |
| **Windows + split argv** (`ssh windows certutil "-hashfile" "X" "MD5"`) | Exit 0, **correct hash** | The expected behavior: the tool runs and returns usable output. |
| **Windows + shell-quoted argv** (`ssh windows "'certutil' '-hashfile' 'X' 'MD5"'`) | Exit 1, `''certutil'' is not recognized` | `shellQuote`d args arrive literally to `cmd.exe`, which does not strip quotes. |

On Linux hosts (Fedora, Debian) the joined shape works over the hop; on Windows it does not. The prior code unconditionally shell-quoted every argument (for local `bash -c` safety), so a Windows-targeted `runCmd` produced the silent no-op case--exactly the class of false verification this journal has warned against.

## 4. Solution: Split Quoting Regimes

`runCmd` now branches on whether a hop prefix is present:

- **Local (no prefix)**: arguments are shell-quoted and handed to `bash -c "<quoted cmd> <quoted args>"`. Needed because the local shell interprets metacharacters (spaces, backslashes, colons) in Windows paths.
- **Across a hop (non-empty prefix)**: arguments are passed **as separate, unquoted elements** to the first element of `prefix` (e.g. `ssh`). The SSH client rejoins argv with spaces before executing on the remote side. This avoids the double-quoting problem and lets the remote shell see the true command shape.

All callsites now work:
- `verifyConfig`: Linux uses `md5sum [file]`; Windows uses `certutil -hashfile <file> MD5`.
- `syncStoreOn`: Linux uses `runCmd("bash", [scriptPath])`; Windows uses `runCmd("pwsh", ["-File", scriptPath])`.
- All git invocations (store parity) use split argv and work uniformly.

Hash output is comparable: `certutil` and `md5sum` both print lowercase hex hashes on their own line, so a Windows hash can be compared byte-for-byte to a Linux one.

## 5. End-to-End Verification

A real `fleet_sync` run (non-dry) proceeds:
1. **buildPlugins**: compiles all TS plugins from the hub (`fleet-sync`, `model-whitelist`, `opencode-task-plugin`, `self-improving-skills`).
2. **verifyConfig (per host)**: confirms shared files (`machines.md`, `CONTEXT.md`, `package.json`, `README.md`) match the hub; reports legitimate drift in `README.md` (expected, as config is verify-only by design).
3. **diffConfigKeys**: confirms `opencode.json` differs only in the expected `mcp` key (host-local by design).
4. **syncStores (plan, mem0)**: runs each host's hardened `sync-*.sh` / `sync-*.ps1` script ON that host over SSH; each reports convergence.
5. **verifyStore (plan, mem0)**: reads each host's `git rev-parse HEAD` ON that host over SSH; confirms all three hosts share the same commit for each store.
6. **report**: writes a JSON file to `~/.opencode/fleet-sync-report.json` for the next session.

A second run is idempotent: no mutating step (build, syncConfig, syncStores) records changes; only the report file is rewritten.

## 6. Pending Actions

- **Debian keepalive durability**: the `WSL keep distros running` task (AtLogOn, `wsl.exe -d Debian --exec sleep infinity`) shows `LastTaskResult = 0xC000013A` (`STATUS_CONTROL_C_EXIT`). It survives while the launching session is alive but is killed when that session ends, leaving Debian stopped and its sshd down. Until a session-resistant long-running mechanism is in place (e.g. a service-style principal or a native Windows loop), the SSH mesh is not reboot-proof. Operators should confirm `wsl.exe -l -v` shows both distros *Running* before relying on `ssh debian`.

## 7. Lessons

- **Check which binary a name resolves to** before trusting its output. On Windows, `bash` is `WindowsApps\bash.exe` (the WSL launcher stub) which executes inside Fedora--so a native Windows path fails with "No such file or directory", masquerading as a missing file.
- **Never assume argv shape is uniform** over heterogeneous targets. Measure the real hop, not the local shell.
- **A silent no-op is the worst failure mode**. Treat exit 0 with empty output as a failure, never as agreement.
- **State what you mean**: split the notions of "did every host answer?" and "are the answers the same?" into two explicit checks.

The fleet-sync orchestrator now runs cross-host, respects platform differences, and avoids the silent-failure traps that have plagued prior verification attempts.

--- 

**Verification**  
- Effective config confirmed on each host via fresh process: `mcp servers: ['gws','mem0']`, `username: sigit`.  
- All three hosts: 5 plugins resolve from `index.ts`; `dist/index.js` md5-identical on Linux and comparable via certutil on Windows.  
- Both stores converge across bare repo, Fedora, Debian and Windows.  
- `fleet_sync` dry-run and real run both `ok`; the real run created **no new commits**, confirming idempotency.  

---

Generated with Big Pickle by OpenCode
