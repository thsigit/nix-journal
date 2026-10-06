# Three Wrong Instruments, One Right Question (or: The Addendum That Retracted Itself)

**Date:** 2026-09-30  
**Author:** Codebot  
**Topic:** opencode, v2, v1, verification, config-normalization, mcp, overlays, self-correction

---

## 1. Objective

Four findings from a second pass at the v1/v2 downgrade question, recorded as an
addendum to `2026-09-29-false-verifications-and-the-v1-question.md` rather than as
a verdict. The prior entry's recommendation - **do not downgrade** - was left
standing, on purpose, with the reasoning it had been given.

Then, twenty minutes later, in the same session by the same author, one of those
four findings was retracted in public.

That retraction is the reason this post exists in rewritten form. The wrong
inference is part of the record, and a record that quietly edits its own mistakes
is not a record. So the structure below is deliberately built to keep both the
claim and its undo visible, in the order they actually happened.

## 2. Background

The fleet is three hosts. Windows native (`Vantage-V14G4`) and two WSL distros run
v2. The homelab runs v1.18.32 and was left there deliberately, per
`2026-09-28-nixos-opencode-v2-upgrade-attempt.md`.

On 2026-09-29 the session found four verifications that could not come back red,
the most serious being that **gws had been completely non-functional on both
distros since 2026-09-22** while every check run against it was structurally
incapable of noticing. The verdict was not to downgrade, on the grounds that the
discrepancies lived in our own hand-written layout rather than in v2:

> "an overlay we wrote by hand, a package we installed with `--no-save`, a
> credentials file we never created on two hosts, a plugin array referencing bare
> npm names"

Downgrading to fix those, it was argued, would be like demolishing the plumbing
because the tap drips.

That entry also left a specific condition attached - the sort of thing that is
written down precisely so it cannot be quietly forgotten:

> "The one thing that would change my answer: if the plugin 404s turn out to be a
> deep v2 packaging problem rather than cosmetic noise. That is the open question
> worth carrying forward, and it is a small, cheap question to answer."

Still unanswered. This addendum did not answer it either.

## 3. Problem

The 2026-09-29 set was all our own mistakes. This set was less comfortable,
because one of the four was not.

### 3.1 `OPENCODE_CONFIG` does not override config values

v2 documents `OPENCODE_CONFIG` as a config layer that merges over the global
config. Measured behaviour says it does not. Three probes, each with a **fresh
process** (see 3.3 - the running service lies):

| Probe | Result |
|---|---|
| Overlay sets `username: OVERLAY-WINS-TEST` | effective `sigit` - ignored |
| ...and `username` also removed from shared config | effective `sigit` - **still ignored** |
| Overlay supplies `mcp.servers`; `mcp` removed from shared config | effective: **no MCP servers at all** |

The second row is the decisive one, and the reason it is decisive is a nice trap:
with the key absent from the shared file *and* present in the overlay, the
effective value still did not come from the overlay. But `username` turns out not
to be read from config at all - it is derived from the OS `$USER`. So it is
useless as a probe for override precedence, and its presence in the overlays had
created a false impression that the overlay *was* being honoured.

The third row is the operational consequence, and the reason this mattered beyond
curiosity: **per-host `mcp` paths cannot live in overlays.** Moving them there
would have left a host with no gws and no mem0 after a restart. It was staged,
detected before the restart, and reverted.

This is the one finding that indicts v2 rather than our layout, and it is filed as
such. Unresolved at the time: v2.0.20 regression, misread merge order, or a
requirement we had not met (the service reading `OPENCODE_CONFIG` only from its
inherited environment, perhaps). Not investigated - the user said stop digging,
and stop digging is what happened.

### 3.2 `hostname` and `group` are not v2 config keys, and never were

```
$ grep -ro "hostname" node_modules/@opencode/schema/ | wc -l
0
```

Zero occurrences in the entire schema package. `username` *is* declared
(`config.d.ts`, `readonly username: Schema.optional(String)`). So the two keys
were never part of the config surface, and v2 discards them silently - no warning,
no error.

All three overlays carried `hostname` and `group`. `machines.md` and the
`sync-opencode` skill both documented them as the mechanism giving each host its
identity. **The per-host identity mechanism has never worked.**

This is the upstream cause of the gws/MCP divergence going unnoticed: a config
that *looks* wired up, verified by a check that cannot detect the failure. Same
class as the 2026-09-29 four, and the reason `TASK-per-host-config-mechanism`
came into existence.

Host identity is available only from the environment (`uname -n` -> `fedoraWSL`,
`WSL_DISTRO_NAME` -> `FedoraLinux-44`). The plugin API's `ctx.location` carries
`directory`, `workspaceID` and `project`, but **no hostname**.

### 3.3 `opencode debug config` reads the running service, not disk

Nearly caused a fleet-wide outage, and is the most transferable item here. Strip
`mcp` from disk, then read the same file two ways:

```
disk: mcp REMOVED
  A: via the RUNNING SERVICE (default)    -> mcp present? True
  B: via a FRESH PROCESS (isolated port) -> mcp present? False
```

The service (pid 470) had started at 08:29 and was reading a 2.5-hour-old config.
A junk `__probe__` key written to disk confirmed it independently: `debug config`
never saw it.

Two traps compound this. `--standalone` is listed in `opencode debug --help` but
is **not accepted** by `debug config` - and the failure mode is the nasty kind:
it prints help and returns success, so a script sees exit 0 and no output. (On
the v2.0.23 checked during this rewrite it now reports `Unrecognized flag` and
exits 1 - an improvement, but note the original observation was exit 0 on
v2.0.20.) The only reliable way to force a fresh read is
`OPENCODE_SERVICE_PORT=1 opencode debug config`.

**Rule: never verify a config edit with a tool that reads the running process.**
`mcp list` reporting `connected` while every call fails, `tools/list` returning 88
tools, `tokens.json` mtime bumping without a refresh - a green signal from the
wrong vantage point. On a host whose service stays up for days, "debug config says
the config is fine" proves only what was true at startup.

### 3.4 The claim that was wrong: a schema shape drift

This section is the one that got retracted, and it is kept intact because the
retraction is the lesson.

The claim was that v2 nests MCP servers under `mcp.servers`, that all three
overlays and the shared config used the flat `mcp: { gws, mem0 }`, and that the
flat form is "silently ineffective" under the current schema.

**It was wrong.** Both shapes were tested with a fresh process:

| Shape in the shared file | Effective servers read |
|---|---|
| flat `mcp: { gws, mem0 }` | `['gws', 'mem0']` |
| nested `mcp: { servers: { gws, mem0 } }` | `['gws', 'mem0']` |

v2 **accepts both and normalizes them.** The flat shape is correct as written.
`opencode debug config` only *displays* the normalized nested form - which is
exactly what made the drift look real.

The mistake was reading `debug config` output and mistaking the **display shape**
for the **on-disk requirement**. That is 3.3's error one level up: noticing a
difference in a tool's output and inferring a defect in the input. 3.3 stands;
this was a second, independent instance of the same class, caught only because the
shape was cheap to test.

**Net effect on the v1/v2 question: none.** No schema change is needed anywhere,
and this finding never bore on the downgrade decision. Findings 1, 2 and 3 stand.

*Process note:* the retraction was published 20 minutes after the original entry,
same session, same author. Its value is that it sits at the same place as the
claim rather than being edited out - the wrong inference is part of what we know.

## 4. Diagnosis

The four findings are not four unrelated defects. They share one shape:

| # | Finding | Whose fault | Blocker? |
|---|---|---|---|
| 1 | `OPENCODE_CONFIG` does not override | **v2** (documented feature inert) | No - workaround exists |
| 2 | `hostname` / `group` never were keys | ours (silently discarded) | No - use env vars |
| 3 | `debug config` reads the service, not disk | the tool's ergonomics | No - but nearly caused an outage |
| 4 | ~~`mcp.servers` schema drift~~ | **nobody - retracted** | No - no drift exists |

Only finding 1 is arguably v2's fault. Findings 2 and 3 are ours and the tool's
respectively, and finding 4 was a phantom.

## 5. Preliminary Assessment

The 2026-09-29 reasoning survives all of it, with one caveat carried forward:
finding 1 means a *documented, intended* v2 feature does not work, which is
closer to "v2 limitation" than anything in the previous set. It is still not a
reason to downgrade three hosts mid-task, but it should not be filed as "our
mistake" either.

The homelab's long-running v1 service remains the only evidence that v1 "just
works", and that too is a smaller, quieter installation rather than a controlled
comparison.

## 6. Disposition

**Stay on v2.** The 2026-09-29 reasoning is intact, and finding 1 - the only one
that indicts v2 - is a documentation/behaviour mismatch with a workaround (keep
`mcp` in the shared file, take host identity from environment variables), not a
blocker. Downgrading three hosts to escape a config-layer defect would be a large,
risky change with no evidence it would prevent a recurrence.

## 7. Open Questions

Carried forward in order of value:

1. Is the `OPENCODE_CONFIG` override genuinely broken in v2.0.20, or are we
   misusing it? (finding 1)
2. Are the plugin 404s cosmetic or a real v2 packaging problem? (from 2026-09-29,
   still open; test alongside #1)
3. Does v1 support *any* per-host config layer? If v1 has the same limitation,
   finding 1 stops being a downgrade argument entirely. **Untested** - the
   homelab's v1 config location was still unknown at the time of writing.

The third is the one that would actually settle the question, and it remains the
cheapest untried experiment. (Update during this rewrite: the homelab does have a
config at `~/.config/opencode/opencode.jsonc`, so the experiment is now
concrete rather than blocked on a missing file. Still untested.)

## 8. Recommendations

1. **A check that reads the wrong thing is worse than no check**, because it
   converts "unknown" into "green". `debug config` reading the live service is
   the sharpest instance; `mcp list` reporting `connected` is the memorable one.
2. **A tool's display shape is not its input contract.** Normalization is a
   feature, and mistaking it for a requirement cost a retracted finding. Compare
   what a tool *prints* against what it *accepts*, separately.
3. **Write the retraction where the claim is.** A record that edits its own
   mistakes teaches the reader that the remaining claims were also edited. This is
   why section 3.4 keeps the wrong version intact.
4. **Prove a probe can fail before trusting its verdict.** The `username` row in
   3.1 is the cautionary case: a probe using a key that is derived from `$USER`
   cannot detect an override problem no matter what it reports.
5. **Silence from a discarded key is not an error.** v2 dropping unrecognised
   config keys without a warning is the root cause behind finding 2, and it is why
   a plausible-looking identity mechanism sat in three overlays for months.
6. **When the user says stop digging, stop digging** - and write down what was not
   answered, precisely enough that the next session does not re-derive the same
   three hypotheses from scratch.
7. **If it recurs:** unset `OPENCODE_CONFIG` and restart before debugging a 500
   caused by a dangling overlay. Do not debug around it.

## 9. Relevant Files

- `node_modules/@opencode/schema/dist/config.d.ts` - where `username` is declared
  and `hostname` / `group` are not
- `TASK-per-host-config-mechanism` - created from finding 2
- `machines.md`, `sync-opencode` skill - both documented the identity mechanism
  that never worked (finding 2)

---

*Narrator: four findings, one retraction, twenty minutes apart. The question was
still open at the end, which is the correct place for it to be.*

Generated with Space Bunny Free by OpenCode