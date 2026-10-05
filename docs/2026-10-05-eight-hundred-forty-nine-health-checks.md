# Eight Hundred Forty-Nine Health Checks That Never Checked Anything

**Date:** 2026-10-05  
**Author:** Codebot  
**Topic:** litellm-cli, systemd, nix, yq, set-euo-pipefail, health-checks, flake-inputs, verification, self-correction

---

## 1. Objective

Retire a permanently red systemd unit that had been sitting in
`systemctl --failed` for over a month, and restore the ability to trust that
command's output.

The unit was `litellm-cli-doctor.service`. The obvious fix was to make the failing
check pass. The actual fix turned out to be to delete the check, fix a tool bug it
had been accidentally concealing, and learn that the check had never once run.

Famous last words: "it's just a timer, it'll be a five-minute change."

It was not five minutes. It was two switches, three commits, two repositories, and
a genuinely embarrassing misunderstanding of what `yq` was.

## 2. Background

The unit arrived as an incidental finding. During the ai-gateway profile
refactor on 2026-10-05, a post-switch verification looked at `systemctl --failed`
and found one unit waiting:

```
UNIT                       LOAD   ACTIVE SUB     DESCRIPTION
litellm-cli-doctor.service loaded failed failed LiteLLM provider health check
```

The task file written up afterwards recorded the numbers, and they were tidy in
the way that only a real problem is:

| Fact | Value |
|---|---|
| Starts | 849 |
| Failures | 595 |
| Successes | **0** |
| First failure | 2026-09-02T13:01:32+08:00 |

Eight hundred and forty-nine starts. Zero successes. A month of continuous,
scheduled, entirely useless work.

The first hypothesis in that task file was reasonable and completely wrong: a
missing config path, a missing environment variable, or a network call returning
nothing. All three felt plausible. None of them was true. This post is mostly
about that gap, because the gap is more interesting than the bug.

## 3. The Symptom (or: A Check That Says Nothing At All)

The complete output of a run, in its entirety:

```
Starting LiteLLM provider health check...
litellm doctor - provider health check (from config.yaml
=====================================
litellm-cli-doctor.service: Main process exited, code=exited, status=1/FAILURE
```

A header, a rule, and then nothing. Not an error message. Not a provider marked
unhealthy. Just... silence, and an exit code of 1.

This is the shape of a check that has **crashed**, not a check that has run and
found nothing. Those two look nearly identical in a systemd journal and mean
completely opposite things, and for a month nobody could tell them apart. It is
worth sitting with how much we trusted that silence: a red unit every hour for
four weeks, and the standing temptation was to read it as "the gateway is having
trouble" rather than "this script dies before it does anything."

## 4. Work Performed

### 4.1 Where the unit came from (it was not in the repo)

The obvious first probe found nothing at all:

```
$ grep -rn "litellm-cli-doctor" /srv/repo/nix-lab
(no matches)
```

Which is exactly the moment to stop trusting the tree and follow the symlink:

```
$ readlink -f /etc/systemd/system/litellm-cli-doctor.service
/nix/store/6isx494gnnyqx4mpz988ax017pyzfsni-unit-litellm-cli-doctor.service
```

The unit came from a package, as they so often do. But not nixpkgs - a *local*
repo, `/srv/repo/litellm-cli`, pulled in as a flake input with `flake = false`.
And the generator was a NixOS module, which is where the actual fix lived:

```nix
doctor = {
  enable = lib.mkOption { type = lib.types.bool; default = true; ... };
  interval = lib.mkOption { type = lib.types.str; default = "hourly"; ... };
};

systemd.services.litellm-cli-doctor = lib.mkIf cfg.doctor.enable { ... };
systemd.timers.litellm-cli-doctor  = lib.mkIf cfg.doctor.enable { ... };
```

A clean opt-out, defaulted on. That detail matters in section 7.

### 4.2 What the timer actually was

Before changing anything, the question of what kind of scheduled task this was
needed a straight answer, because the answer decides what the fix should look
like. It is neither a Windows Task Scheduler entry nor a cron job:

```
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=5m
```

A systemd timer on the homelab. `Persistent=true` means it also fires after
downtime, so a machine off for a week comes back and immediately runs a check
that has never worked. There is no cron on this host at all
(`crontab: command not found`), and nothing Windows-side.

### 4.3 Reading the thing that was actually failing

With the unit resolved to a store path, the real script was readable. The wrapper
was one hop, the implementation another:

```
/nix/store/xgdh7ic6...-litellm-cli/bin/litellm-cli     (wrapper, execs the next)
/nix/store/jdr6v8b...-litellm-cli/lib/doctor.sh         (the real thing)
```

Line 129 of `doctor.sh` is where the story turns:

```bash
yq -o=json '.' "$CONFIG_FILE" | jq -r '
  [.model_list[] | { prov: ..., base: ..., keyenv: ... }]
```

## 5. Diagnosis

`-o=json` is **mikefarah** `yq` syntax - the Go implementation. The `yq` in the
runtime PATH is **kislyuk's** python wrapper, which is a jq frontend and has no
`-o` at all. It passes unknown flags straight to `jq`, and jq does not care for
the argument:

```
$ yq -o=json '.' config.yaml
jq: Unknown option -o
Use jq --help for more information...
Exception ignored in: <_io.TextIOWrapper name=6 encoding='UTF-8'>
BrokenPipeError: [Errno 32]: Broken pipe.
yq: Error running jq: BrokenPipeError
$ echo $?
1
```

And `doctor.sh` line 11 is `set -euo pipefail`. So the pipeline dies at line 129,
which is three lines after the header at lines 122-124 prints, and four lines
before the first provider would have been checked.

That is the whole thing. The empty output was not a mystery condition, it was a
missing `-o` and a shell flag.

### 5.1 The finding that made the rest of the session worthwhile

**The health check had never once checked anything.** 849 executions, zero health
probes. It was not reporting a sick gateway; it was crashing four lines into a
loop that would have probed three providers.

Restated for the sake of anyone who draws a conclusion from a check later: a
month of silence from this unit carried exactly zero information about the health
of LiteLLM. Not "no news", not "probably fine". Nothing.

## 6. A Second Copy Of The Same Bug (or: The One Nobody Knew About)

Fixing the line the symptom pointed at would have been the tidy move, and would
have left a second identical bug exactly where it was. So: grep every call site
of the tool.

```
lib/debug.sh:25:    yq "$CONFIG_FILE"
lib/run.sh:30:    MODEL=$(yq -r '.model_list[0].model_name // ""' "$CONFIG_FILE")
lib/models.sh:32:MODELS=$(yq -o=json "." "$CONFIG_FILE" 2>/dev/null | jq '
lib/config.sh:23:  if ! yq -e '.model_list' "$CONFIG_FILE" >/dev/null 2>&1; then
...
```

Two hits. `models.sh:32` had the same `-o=json`, so:

```
$ litellm-cli models
$ echo $?
1
```

No output. `litellm-cli models` and `models --json` had **never worked** in this
deployment either - and this one was worse than the doctor, because line 32
discards stderr with `2>/dev/null`. The doctor at least shouted. `models` failed
completely silently, which is why nobody had noticed that either.

One candidate was checked and cleared rather than assumed: `config.yaml` contains
a literal `api_key: "sk-local"` with no `os.environ/` prefix, which looks like it
should break the `capture()` call. It does not - jq's `capture` yields empty and
the existing `// "none"` handles it. Left alone.

## 7. Solution Summary

Two repositories, three commits, and one deletion.

### 7.1 Fix the tool (`litellm-cli` @ `682415d`)

kislyuk's `yq` already emits JSON by default, so the fix is to simply drop the
flag:

```bash
- yq -o=json '.' "$CONFIG_FILE" | jq -r '
+ yq '.' "$CONFIG_FILE" | jq -r '
```

Both sites, with a comment recording why, so the next person (or the next
hallucinating code-completion model) does not helpfully put `-o=json` back:

```bash
# NOTE: `yq` here is kislyuk's python wrapper (jq frontend), not mikefarah's.
# It already emits JSON by default; `-o=json` is mikefarah-only syntax and gets
# forwarded to jq, which aborts with "Unknown option -o". Under `set -euo pipefail`
# that kills the script mid-run: `debug doctor` exited 1 after printing only its
# header, and `models`/`models --json` printed nothing at all. Do not re-add -o.
```

### 7.2 Delete the timer (`nix-lab` @ `3e5c28f`)

This is the part that deserves justification, because the obvious instinct was to
make the check pass instead.

```nix
doctor.enable = false;
```

Three reasons, in order of weight:

1. **The timer contradicted the tool's own documented design.** The `litellm-cli`
   header states it *"is purely MANUAL. It is never invoked by a rebuild, systemd
   unit, or activation script."* The module then defaulted `doctor.enable = true`.
   The code and its documentation disagreed, and the documentation described the
   better design.
2. **A provider being rate-limited or briefly unreachable is not a reason to page
   anyone.** Unattended health checks on flaky third-party APIs train you to
   ignore them.
3. **A permanently red unit destroys the signal you were trying to read.** Every
   future `--failed` result would train this operator to shrug. The check was
   actively harmful to the thing it existed to protect.

Scope turned out to be a non-issue. `ai-common/` is imported by both `ai-gateway`
and `workstation`, and `server`, `failsafe`, and `system` never had the CLI at
all (verified with `nix eval`: `services ? litellm-cli` is false in all three).
One override, both profiles, no `system/` change.

### 7.3 One extra switch, for a reason worth remembering

The first switch removed the units and **did not rebuild the CLI**. The new store
path was byte-identical, so the `yq` fix stayed theoretical for one more cycle.

Cause: the `litellm-cli` input is a plain path (`flake = false`), and Nix caches
its NAR hash against the input's **root directory mtime**. Editing `lib/` two
levels down does not touch the root's mtime, so Nix cheerfully re-hashed nothing
and reproduced the old output.

```
$ touch /srv/repo/litellm-cli && nix flake update litellm-cli
warning: updating lock file "/srv/repo/nix-lab/flake.lock":
  Updated input 'litellm-cli': ... (2026-10-02) -> ... (2026-10-05)
```

The lock diff was confined to that one node - `lastModified` and `narHash` only,
nixpkgs rev untouched - so no closure re-download was triggered, which matters
given this repo's standing rule about not disturbing `flake.lock` casually.

## 8. Verification

The litellm-cli one (`682415d`) is committed but **not pushed**; `main` is 8
commits ahead of `origin/main`.

| Check | Result |
|---|---|
| `systemctl --failed` | **0 loaded units listed** (was 1) |
| `systemctl list-timers --all` | no `litellm-cli-doctor.timer`; 4 timers remain |
| `list-unit-files \| grep litellm-cli-doctor` | none |
| `/etc/systemd/system/` symlinks | gone |
| Generation | 268 current |
| `nix eval` doctor option, all 5 profiles | absent everywhere |
| `command -v litellm-cli` | `/nix/store/jvcaw5mp...` (new) |
| `-o=json` in activated `lib/` | none |
| `litellm-cli debug doctor` | 3 providers, **exit 0** |
| `litellm-cli models` | 28 models / 3 providers, **exit 0** |
| `models --json \| jq length` | 28, exit 0 |
| `config validate`, `config list`, `debug status`, `models local` | all exit 0 |

For the record, the working output:

```
litellm doctor - provider health check (from config.yaml)
=====================================

  ? cloudflare       error (117ms) - Unexpected response (HTTP 405)
  OK local            healthy (14ms)
  OK nvidia           healthy (380ms)

State saved to: /run/litellm-cli/health.json
=====================================
Total: 3 | Healthy: 2 | No key: 0 | Errors: 1
```

## 9. Two Loose Ends (Neither Was Fixed)

### 9.1 The cloudflare 405 is a false alarm

Doctor reports cloudflare as `error`. Cloudflare is **healthy**. The doctor probes
`${api_base}/models`, and Workers AI rejects GET there:

```
GET  .../ai/v1/models -> 405 {"code":7001,"message":"GET not supported for requested URI."}
```

The real inference path works fine:

```
POST .../ai/run/@cf/meta/llama-3.2-1b-instruct -> 200 {"response":"Ok", ...}
```

So the probe is OpenAI-shaped and simply does not fit Cloudflare's API surface.
Left alone deliberately: the check is manual now, and a wrong reading is only a
problem if you act on it without reading. But it is worth stating the general
lesson, because it is the one that keeps:

**A working check is not a correct check.** This one exits 0 now, which was the
goal, and it still gets one provider wrong for a structural reason. Exit code and
accuracy are separate properties, and this session only ever tested the first.

### 9.2 Archived skills point at a unit that no longer exists

`litellm-render.service` is **gone** - `Unit could not be found`, absent from
every `.nix` in the repo. It was retired when the render step was dropped in
favour of a static `config.yaml`.

Fifteen references to it survive across four skills under `skills/archive/`,
including instructions to `systemctl restart litellm-render` and to check it for
log correlation. Following one would send an operator chasing a unit that cannot
appear. Cheap sweep next time those files are touched.

## 10. Recommendations

1. **A check that prints nothing and exits 1 has crashed, not found nothing.**
   Those read identically in a journal and mean opposite things. Get the script
   and read it before theorising about the thing it was checking.
2. **When a check has never succeeded, assume it has never run.** 849 starts and 0
   successes is not a flaky check, it is a check that does not work. Count the
   successes before counting the failures.
3. **Grep every call site of a tool when you fix one of them.** The second
   `-o=json` had been failing silently the whole time, and the only reason it was
   found is that "let me also check the others" beat "let me verify the one I
   touched."
4. **Verify what a tool in your PATH actually is before writing its syntax.**
   Two projects named `yq`, incompatible flags, and one of them installed.
5. **A red unit teaches you to ignore `--failed`.** If a check is permanently
   failing, the choice is fix it or remove it. Leaving it is the one option that
   makes the monitoring worse than having none.
6. **When deleting automation, read what the tool says about itself first.** The
   header comment calling the tool "purely MANUAL" and the module defaulting to
   `enable = true` is a design disagreement, and the comment was right.
7. **After an in-place edit to a `flake = false` input, check that the build
   actually changed.** Root-directory mtime caching means a committed fix can
   silently rebuild byte-identical output. Compare the store path before assuming
   your edit was wrong.
8. **Separate "the check passes" from "the check is right."** Verify both, every
   time, or you will ship a green light that is wired to nothing - which is
   roughly the state we started in, except quieter.

Generated with Space Bunny Free by OpenCode