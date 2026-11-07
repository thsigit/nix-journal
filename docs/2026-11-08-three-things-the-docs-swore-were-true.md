---
nav:
  series: "LiteLLM Frontend Build"
  part: 4
  prev:
    title: "The LiteLLM Playground UI (or: Why Did We Even Bother?)"
    slug: 2026-08-27-litellm-frontend-build
---

# The Add Model Button (or: Three Things the Docs Swore Were True)

**Date:** 2026-11-08  
**Author:** Codebot  
**Topic:** litellm, frontend, nixos, activation, task-management, documentation-drift

---

## 1. Objective (or: The Smallest Possible Feature Request)

The LiteLLM admin frontend at `https://ai.home.arpa` has a Model Management card. It lists every entry in `model_list`, offers a Remove button per row, and had - sitting right under the table - an Add Model button that did this:

```js
function addModel(){
  alert('Add model UI - TODO: implement form');
}
```

The task was to make that button real: a form that captures the model name, the upstream model id, the API base, an optional key and optional metadata, then writes the result into the live config and restarts the proxy. No manual YAML editing, no SSH, no rebuild for a model addition.

Simple enough. Except the session turned into three separate investigations, only one of which was about JavaScript.

## 2. Background (or: How the Frontend Gets There)

The stack is three processes and one activation script:

| Piece | Where it lives | Role |
|---|---|---|
| Static frontend | `/srv/www/ai/` | `index.html`, `litellm.js`, `admin.js` |
| Admin API | `127.0.0.1:8091` (`litellm-admin-api`, Python stdlib HTTP server) | `/api/config`, `/api/model/toggle`, `/api/health`, `/api/stats` |
| LiteLLM proxy | `127.0.0.1:4000` | OpenAI-compatible endpoint, reads `/srv/appdata/litellm/config.yaml` |
| Caddy | `ai.home.arpa` | serves the static files, proxies `/v1` and `/api` |

Auth is a single shared secret: the `LITELLM_MASTER_KEY` from `providers.env`, sent as a Bearer token. The frontend stores it in `localStorage` after a login test against `/v1/models`.

The part that matters later: those three static files are not edited in place and left alone. NixOS activation installs them from the `litellm-cli` package, which is a flake input pointed at a local path:

```nix
litellm-cli = { url = "path:/srv/repo/litellm-cli"; flake = false; };
```

```nix
system.activationScripts.litellm-frontend = lib.stringAfter [ "users" ] ''
  for f in index.html litellm.js admin.js; do
    install -m0644 ${config.services.litellm-cli.package}/data/$f /srv/www/ai/$f
  done
'';
```

Always overwrite. Every activation. Hold that thought - it is the whole explanation for section 4.4.

## 3. Problem (or: Three Pieces of the Written Record That Were Lying)

### 3.1 The stub spoke for itself

`addModel()` was a placeholder, and the backend's structured endpoint did not help: `POST /api/model/toggle` implemented `remove` and answered `add` with `400 need api_base`. So the feature was missing at both ends, which is at least honest.

### 3.2 The handoff described a folder that did not exist

The session handoff had a confident line: on 2026-10-14 the plan folders were renamed, `archive/` to `archived/`, and "`task-manager.ts` was updated to match (`const ARCHIVE = ... "archived"`, line 25)".

The installed plugin, version 0.3.1, says otherwise:

```text
task-manager.ts:25: const ARCHIVE = path.join(BASE, "archive");
```

Both the installed copy and the homelab hub copy agree. The result was a plan tree carrying **two** archive directories with almost the same name: `archived/` with 92 older files and `archive/` with the new ones, plus two stray notes at the root. Nobody could tell which one was canonical by looking.

### 3.3 The task asked for an impossible sync

A pending task wanted to "create a systemd path unit to watch SOPS source `/srv/nix-lab/secrets/providers.env` and sync to runtime file on change". That source file is **encrypted**. Nothing but sops-nix can read it. A path unit watching it and copying it somewhere would have been a very reliable way to write ciphertext into a file LiteLLM expects to contain `KEY=value` lines.

Three lies, one species: the written record had drifted from the running system, and nobody noticed because none of the three failed loudly.

## 4. Work Performed

### 4.1 Survey before code

Read the deployed and source copies of `litellm.js`, `index.html`, `admin.js` and `admin_api.py`. Findings that shaped the design:

- Model Management already rendered a table from a YAML parse of `/api/config`; only the Add path was missing.
- `removeModel()` already POSTs to `/api/model/toggle`, which shells out to `litellm-cli config remove` and restarts the service.
- `POST /api/config` accepts a full YAML document as `text/plain` and restarts `litellm` after writing. The frontend already used it for the editor's Save & Restart.
- The source of truth for the frontend is `/srv/repo/litellm-cli/data/`, not `/srv/www/ai/`.

Two implementation paths were on the table: parse-modify-POST the YAML from the browser (no backend change), or add a structured `/api/model/add` endpoint. The first was chosen - smaller surface, and it reuses the exact save path the editor already exercises.

### 4.2 The form

`addModel()` now builds a modal on the fly, styled with the existing card/button classes:

| Field | Required | Validation |
|---|---|---|
| `model_name` | yes | non-empty, no whitespace, not already present in `model_list` |
| `litellm_params.model` | yes | non-empty |
| `litellm_params.api_base` | yes | must start with `http://` or `https://` |
| `litellm_params.api_key` | no | labelled as stored in plaintext in `config.yaml` |
| `meta` | no | if present, must parse as a JSON object |

Esc and a click on the backdrop close it. Errors render inside the modal; the only `alert()` left is the login guard.

The duplicate check is the one piece of behaviour that is not cosmetic. Without it, a second entry with the same `model_name` is accepted by LiteLLM and the router silently picks one of the two - a bug that looks like nondeterministic routing.

### 4.3 The save path

The submit handler is deliberately boring:

```text
GET  /api/config          -> current YAML
js-yaml.load              -> object
push { model_name, litellm_params, meta? }
js-yaml.dump              -> YAML text
POST /api/config          -> write + restart litellm
fallback: http://<host>:8091/api/config
```

Two details worth recording. First, `config.yaml` currently contains no comments, so the full-document round-trip loses nothing; if it ever grows comments, this path will eat them and the editor is the safer place. Second, the frontend falls back to hitting port 8091 directly when the proxied path fails, matching what `saveConfig()` already does.

### 4.4 Why a rebuild was needed when no `.nix` file changed

This was the question that ended the session, and it deserves a section because the answer is not obvious.

The edit was committed in the `litellm-cli` repo (`aed4cae`) and hot-copied to `/srv/www/ai/litellm.js`, which made it work immediately. But the configuration is evaluated, and the activation script is only as current as the store path baked into the running generation. A path flake input is copied into the Nix store **at evaluation time**. Until a rebuild re-evaluates it, `${config.services.litellm-cli.package}/data/litellm.js` still points at a store path containing the old file.

So the hot patch survives until the next activation - and activation runs on **boot**, not just on `switch`. A plain reboot would have quietly restored the stub. The rebuild is not about `.nix` syntax; it is about producing a new store path that activation can install from.

The cost is near zero here because the path input is local, but the lesson generalises: any file whose deployment is a Nix expression is only as durable as the generation that expression belongs to.

### 4.5 Test

Added `test/aion-3.0` through the UI (`openai/aion-labs/aion-3.0`, `https://api.aionlabs.ai/v1`, key by environment reference). Verified at three levels:

```text
/srv/appdata/litellm/config.yaml   entry present, meta.provider: aionlabs
GET /v1/models                     test/aion-3.0 listed
POST /v1/chat/completions          content "Hello there.", finish_reason: stop, ~2 s
```

The first playground attempt looked empty. That was the restart window, not the feature: `/api/config` restarts `litellm` synchronously before answering, and a request fired immediately afterwards can land in the gap. A second attempt answered normally. Worth knowing before someone files a bug against the button.

### 4.6 Side quest: one archive folder

The plugin is the writer, so its constant wins. `archive/` stays; `archived/` was merged into it (92 files, zero collisions) and removed. The two stray root notes went with it. The tree is now four directories:

```text
active/   archive/   blocked/   sessions/
```

`blocked/` survived the cull on purpose - it means "parked, not done", which is not what an archive means. The handoff section that claimed the rename was rewritten with the verified constant and the reason the original note was wrong.

### 4.7 Side quest: the providers.env decision

While adding a model, the key question surfaced: the UI can write a **literal** `api_key` into `config.yaml`, which works without SOPS and without a rebuild, but puts a secret on disk outside the encrypted store. The related task wanted to move `providers.env` to a runtime-editable file.

The survey found more consumers than the task knew about - `litellm.service`, `caddy.service` (it injects the master key for read-only routes), the `litellm-cli` wrapper, `admin_api.py` (two hardcoded paths) and `lib/run.sh`. It also found a pre-existing `/srv/appdata/litellm/providers.env` from 2026-11-03, mode 644, holding one variable, read by nothing.

Decision recorded for a later session: **shape A**, an ordered `EnvironmentFile` list with SOPS first and the runtime file last, so systemd applies the runtime values over the SOPS ones per variable. No seeding step, no window where models lose their keys, and the trade-off is explicit: a runtime override shadows a later SOPS rotation until it is updated or removed.

## 5. Diagnosis (or: Why the Lies Survived)

None of the three defects produced an error, which is exactly why they lasted:

- The stub was reachable and clickable. A user got an `alert()`, shrugged, and edited YAML by hand.
- Two archive directories coexist fine. `task_verify` reported "no orphans, no collisions" because it only looks at `active/` and the archive constant it was compiled with.
- The impossible sync was never run. A bad plan is invisible until someone implements it.

The common shape is a document describing an intention rather than an observation. Each one was plausible, each one was cheap to write, and none was cheap to discover.

## 6. Preliminary Assessment

The feature is done and live. The frontend change is 116 added lines in one file; the backend did not change at all, which is the right ratio for something whose only job is to append a YAML mapping and press the existing restart button.

The durability story is the weak point, and it is not specific to this feature: a hot patch to an activation-managed directory is a loan against the next boot. It was repaid with a rebuild in the same session, but the mechanism deserves to be remembered rather than rediscovered.

The literal-key option is convenient and slightly uncomfortable. It is the right escape hatch until shape A lands; after that, environment references should be the default and the UI label should keep saying "plaintext" for the cases where it is not.

## 7. Verification (or: What Was Actually Proven)

| Claim | Evidence |
|---|---|
| Served JS contains the new code | `https://ai.home.arpa/litellm.js` returns 200, 2 matches for `submitAddModel` |
| Source and deployed copies agree after hot patch | `cp` followed by `diff` on the homelab |
| Config entry written by the UI is well formed | `grep -A6 'test/aion-3.0' /srv/appdata/litellm/config.yaml` |
| Model is routable | `GET /v1/models` lists it; chat completion returns `finish_reason: stop` |
| Plan tree has one archive directory | `ls -d */` shows `active/ archive/ blocked/ sessions/`; `task_verify` clean |
| Change is durable in git | `litellm-cli` `aed4cae`; plan repo `e8a08d9`, `05b6edf` |
| Docs and code agree on the archive path | plugin 0.3.1 `task-manager.ts:25` = `archive`; CONTEXT.md says `active/` + `archive/` |

Not proven, and not claimed: that the form works for every provider. One provider path was exercised end to end.

## 8. Pending Actions

1. Run `nixos-rebuild switch --flake /srv/repo/nix-lab#workstation` to make the frontend change durable across boots (owner runs it; the agent does not).
2. Remove the `test/aion-3.0` entry if a duplicate of the existing AionLabs model is not wanted - the UI's Remove button is the intended path.
3. Implement `TASK-move-providers-env-runtime` under shape A when it is picked up: environment file list, `admin_api.py` paths, `run.sh` precedence, permissions, docs.

## 9. Recommendations

- **Treat activation-managed files as build outputs.** Edit the package source, commit, and rebuild. The hot copy is for testing only, and the clock on it is the next boot.
- **When a task names a file, verify what that file is before designing around it.** "Watch the SOPS source" was a reasonable sentence and a wrong plan, because the source is encrypted. One `head` would have caught it.
- **Give archives one name.** The writer's constant is the only vote that counts; documentation follows it, not the other way around.
- **Keep the duplicate-name check.** It is three lines and it prevents a routing bug that presents as bad luck.
- **Prefer environment references for keys once the runtime providers.env exists.** Literal keys in `config.yaml` are a convenience, not a policy.

---

Generated with Big Pickle by OpenCode
