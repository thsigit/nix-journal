# Addendum: more v2 findings — the downgrade question stays open

**Date:** 2026-09-30
**Supersedes nothing.** This *adds* to `2026-09-29-false-verifications-and-the-v1-question.md`.
That entry's verdict (**do not downgrade**) stands for the reasons given there. This
records four further v2-specific findings found on 2026-09-30, and keeps the question
open rather than closed.

## The question, restated

**Why stay on v2 rather than downgrade to v1?** Answered "no downgrade" on 2026-09-29.
The user is keeping v2, and is deliberately **not** re-litigating that today. The question
is retained because the new evidence bears on it — and because the prior entry itself said
what would change the answer:

> "The one thing that would change my answer: if the plugin 404s turn out to be a deep v2
> packaging problem rather than cosmetic noise. That is the open question worth carrying
> forward, and it is a small, cheap question to answer."

That remains unanswered. See finding 4, which is adjacent.

## Why the 2026-09-29 verdict still holds

Its core argument was that v2's discrepancies are **in our own layout, not in v2** — "an
overlay we wrote by hand, a package we installed with `--no-save`, a credentials file we
never created on two hosts, a plugin array referencing bare npm names." Downgrading to fix
those was compared to "demolishing the plumbing because the tap drips."

**That reasoning survives all four new findings**, with one caveat noted under finding 1.
Every finding below is still a configuration or documentation error on our side. None is
a v2 runtime defect, a data-loss bug, or a security issue. The homelab's long-running v1
service remains the only evidence that v1 "just works," and that too is a smaller, quieter
installation — not a controlled comparison.

**The caveat:** finding 1 means a *documented, intended* v2 feature does not work. That is
closer to "v2 limitation" than anything in the 2026-09-29 set. It is still not a reason to
downgrade a three-host fleet mid-task, but it should not be filed as "our mistake."

## Finding 1 — `OPENCODE_CONFIG` does not override config values (v2 feature appears inert)

**The most consequential new finding.** v2 documents `OPENCODE_CONFIG` as a config layer
that merges over the global config. Measured behaviour: it does not.

Three probes, each with a **fresh process** (see finding 3 — the running service lies):

| Probe | Result |
|---|---|
| Overlay sets `username: OVERLAY-WINS-TEST` | effective `sigit` — ignored |
| …and `username` also removed from shared config | effective `sigit` — **still ignored** |
| Overlay supplies `mcp.servers`; `mcp` removed from shared config | effective: **no MCP servers at all** |

The second row is the decisive one. With the key absent from the shared file *and* present
in the overlay, the effective value still did not come from the overlay. Reason: **`username`
is not read from config at all** — it is derived from the OS `$USER` (`sigit`). It is
therefore useless as a probe for override precedence, and its presence in the overlays
created a false impression that the overlay *was* being honoured.

The third row is the operational consequence: **per-host `mcp` paths cannot live in
overlays.** Moving them there and restarting the service would have left the host with no
gws and no mem0. This was staged, detected before restart, and reverted.

### This is a v2 limitation, not our error

Our layout is fine; the documented mechanism does not do what the docs say. Caveat to the
2026-09-29 argument, recorded above: this is the first finding that is arguably v2's
rather than ours.

**Unresolved:** whether this is a v2.0.20 regression, a misreading of merge order, or a
requirement we have not met (e.g. the service reading `OPENCODE_CONFIG` only from its
inherited environment). Not investigated, per the user's instruction to stop digging.

## Finding 2 — `hostname` and `group` are not v2 config keys; they never were

    $ grep -ro "hostname" node_modules/@opencode/schema/ | wc -l
    0

Zero occurrences in the entire `@opencode/schema` package. `username` *is* declared
(`config.d.ts`, `readonly username: Schema.optional(String)`). So the two keys were never
part of the config surface, and v2 discards them silently — no warning, no error.

All three overlays carried `hostname` and `group`. `machines.md` and the `sync-opencode`
skill both documented them as the mechanism giving each host its identity. **The per-host
identity mechanism has never worked.**

This is why the gws/MCP divergence went unnoticed: a config that *looks* wired up,
verified by a check that cannot detect the failure — the same class as the four
"false verifications" in the 2026-09-29 entry, and the reason
`TASK-per-host-config-mechanism` now exists.

Host identity is available only from the environment: `uname -n` (`fedoraWSL`),
`WSL_DISTRO_NAME` (`FedoraLinux-44`). The plugin API's `ctx.location` carries
`directory` / `workspaceID` / `project` but **no hostname**.

## Finding 3 — `opencode debug config` reads the running service, not disk

Nearly caused a fleet-wide outage during this session, and is the most transferable item
here.

Strip `mcp` from disk, then read the same file two ways:

    disk: mcp REMOVED
      [A] via the RUNNING SERVICE (default)    -> mcp present? True
      [B] via a FRESH PROCESS (isolated port) -> mcp present? False

The service (pid 470) had started at 08:29 and was reading a 2.5-hour-old config.
A junk `__probe__` key written to disk confirmed it independently: `debug config` never
saw it.

Two traps compound this:
- `--standalone` is listed in `opencode debug --help` but is **not accepted** by
  `debug config`; it prints help and **exits 0**. Exit 0 with no output reads as success.
- The only way to force a fresh read is `OPENCODE_SERVICE_PORT=1 opencode debug config`.

**Rule: never verify a config edit with a tool that reads the running process.** This is
the same failure class as the 2026-09-29 entries — `mcp list` reporting `connected` while
every call fails, `tools/list` returning 88 tools, `tokens.json` mtime bumping without a
refresh. A green signal from the wrong vantage point. On a host whose service stays up for
days, "debug config says the config is fine" proves only what was true at startup.

## Finding 4 — the schema shape changed: `mcp.servers`

v2 nests MCP servers under `mcp.servers`. All three overlay files and (before restore) the
shared config used the flat `mcp: { gws, mem0 }`. Under the current schema the flat form
is silently ineffective.

Adjacent to the 2026-09-29 "plugin 404s" open question and worth testing in the same pass:
both suggest **v2 packaging/config-shape drift that the fleet has been carrying silently**.
Still unverified whether the 404s are cosmetic.

## Disposition

**Stay on v2.** The 2026-09-29 reasoning is intact, and finding 1 — the only finding that
arguably indicts v2 rather than our layout — is a documentation/behaviour mismatch with a
workaround (keep `mcp` in the shared file, use environment variables for host identity),
not a blocker. Downgrading three hosts to escape a config-layer defect would be a large,
risky change with no evidence it would prevent a recurrence.

**Carry forward**, in order of value:
1. Is `OPENCODE_CONFIG` override genuinely broken in v2.0.20, or are we misusing it? (finding 1)
2. Are the plugin 404s cosmetic or a real v2 packaging problem? (2026-09-29, still open; test alongside #1)
3. Does v1 support *any* per-host config layer? If v1 has the same limitation, finding 1
   stops being a downgrade argument entirely. **Untested — the homelab's v1 config location
   is still unknown, so nobody can say what a v1 fleet config would look like.**

That third point is the one that would actually settle the question, and it remains the
cheapest untried experiment.
