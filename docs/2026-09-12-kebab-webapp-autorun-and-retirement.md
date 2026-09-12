# The Kebab Chronicles: From Research Idea to Auto-Running Web App to Graceful Retirement (or: We Built It, Shipped It, Fed It, and Then Archived It in One Long Day)

**Date:** 2026-09-12  
**Author:** Codebot  
**Topic:** kebab, knowledgebase, research, webapp, litellm, systemd, nixos, retire

---

## 1. Objective (or: Why Does the Knowledge Base Need a Web Face?)

The homelab already had `kebab` - a CLI knowledge base that ingests web material into a git-backed KB (`/srv/repo/sejarah/majapahit`), runs an LLM researcher over it, and proposes `changes.yaml` for a human to review and apply. The research pipeline itself ("gather web + KB, think, produce claims, cite sources") had long been exercised from the terminal. This session's job was to give that pipeline a browser:

1. Turn kebab's application layer (AI, RAG, search, knowledge, research, sources) into service objects shared by both the CLI and an HTTP API.
2. Expose research sessions over HTTP: list, create from the web, and - critically - have creation **automatically run the whole research flow** in one synchronous request.
3. Deploy it like a grown-up: systemd service behind Caddy, auto-rebuilding vite frontend, nothing bound to the public interface.
4. And, as it turns out, retire the whole thing in the same session and preserve it as `knowledgebasebuilder-legacy`.

Spoiler: every one of those happened. The session is a complete lifecycle story - build, ship, harden, hit a wall, work around it, and then a clean, staged retirement.

## 2. Background (or: The Research Loop That Worked, Somewhere You Couldn't See)

The kebab research loop had stabilized over prior sessions:

| Stage | What lives there |
|---|---|
| Search | `duckduckgo_urls()` - DDG HTML endpoint, no API key |
| Fetch | `fetch_many` -> `findings.md` + `sources.md` (SHA-256 `content_hash` provenance) |
| KB context | optional semantic search over the KB -> `kb-context.md` |
| LLM | `run_research` via the LiteLLM proxy at `http://127.0.0.1:4000` |
| Output | `claims.yaml`, `changes.yaml`, `findings.md` |
| Apply gate | `kebab diff` / `kebab apply` - changes are proposals until a human applies them |

An evidence guard kept the LLM honest: refuse to run research on a session with no gathered material unless `--force`. The missing piece was the "from the web" part - the GUI could only list sessions it had already been told about. Real users (the actual human behind this homelab) had to SSH in and type things. Unacceptable.

## 3. Problem (or: The Empty Session That Started It All)

The moment that crystallized everything: the user created a session - `candi-sukuh-dan-candi-ceta` - through the freshly hacked-together web form, and it sat there empty. A skeleton with a question mark for a soul. The complaint was fair: *"all those steps should have been automatically run when I ran the session from the kebab web GUI."* That single sentence is the thesis of this whole phase.

## 4. Work Performed

### 4.1 The Services Layer (or: One App, Two Front Doors)

Before any web feature, kebab's logic had to stop living in CLI-specific code. The result was a clean six-service layer in `kebab/services/`:

| Service | Responsibility |
|---|---|
| `AIService` | provider resolution, chat, embeddings |
| `RAGService` | build/load index, semantic retrieval |
| `SearchService` | scoring + search over the KB |
| `KnowledgeService` | records CRUD, plan/apply |
| `ResearchService` | session lifecycle, investigate, run |
| `SourceService` | sources list/detail, claims, provenance |

The CLI became a thin presenter; the API's FastAPI routes import the same services via `api/dependencies.py`. Suite went from 115 to **128 passed**. Committed on homelab as `e8a4bdf`.

### 4.2 Web Sessions (or: The Form That Made a Skeleton)

`POST /api/v1/research/sessions` plus a "New session" form on the React `SessionSourcesPage` gave the web a create button. Response was 201, session id immediately usable. **131 passed**, committed `2517c76`. First live deployment: frontend bundle `index-Cek0zdwX.js`, API restarted, POST/LIST live-verified with `curl` + `X-Kebab-Root` override against a throwaway KB.

And then the user made that empty session and the real requirement surfaced.

### 4.3 Auto-Run (or: All the Steps, One Request)

The user chose **synchronous** auto-run: `POST /research/sessions` with `auto=true` executes gather + LLM in the same request (tens of seconds, browser shows a spinner). Design decisions:

- `ResearchSessionCreate.auto: bool = False` on the schema.
- `ResearchService.autopilot(question)` returns a dataclass `AutoResearchResult` with the session plus run outcomes.
- `autopilot` never raises: failures become `error` in the response, HTTP stays 201, the session remains usable.
- Preview counts returned: `gathered`, `claims`, `sources`, `changes`.

Frontend: `ResearchResult` type, `api.createSession(question, "llm", true)`, "Start research" / "Researching..." with a result summary and inline error banner. **133 passed**, committed `113939b`.

### 4.4 LLM Credentials for a Headless Service (or: Systemd Does Not Do Bash Quoting)

The API runs as a systemd service with none of the user shell's env. It needed `KEBAB_LLM_BASE_URL` + `KEBAB_LLM_API_KEY` - and the key must come from the existing sops secret `/run/secrets/providers.env` (`LITELLM_MASTER_KEY`), never a value in git. Three attempts, three lessons:

1. `EnvironmentFile` + `Environment="KEBAB_LLM_API_KEY=${LITELLM_MASTER_KEY}"`: systemd emits `Environment=` lines **before** `EnvironmentFile=` in the generated unit, so the variable never expands - the literal `${LITELLM_MASTER_KEY}` landed in the process env.
2. A bash `-c` wrapper with inline quoting: systemd's `ExecStart` quoting is *not* bash quoting. It mangled the `tr -d "\"\r"` and the service failed with `unexpected EOF while looking for matching quote`.
3. The winner: `pkgs.writeShellScript "kebab-api-wrapper"` - a store script that extracts the key with `sed`, `export`s it, and `exec`s the uvicorn binary. No conditionals, no quoting mazes; `ExecStart = kebabApiWrapper`.

Side lessons from the homelab: NixOS's setuid `sudo` lives in `/run/wrappers/bin/sudo` (the `/run/current-system/sw/bin/sudo` copy is not setuid), and systemd-run builds rooted `dist/` directories that then break user-side `npm run build` with EACCES.

### 4.5 The Great Duck-Duck-Go Throttle (or: This Home IP Is Not Merely a Guest)

Auto-run live-tested and hit a wall that had nothing to do with kebab: DuckDuckGo's HTML endpoint started serving its "anomaly challenge" page to this home IP. Direct probes showed the IP now sits behind a rate-limit shared by the whole network (NAT). The evidence guard correctly refused to fabricate claims from nothing. A fallback engine survey under the same IP:

| Engine | Verdict |
|---|---|
| DuckDuckGo HTML | anomaly page (throttled) |
| Mojeek | served a CAPTCHA |
| Startpage | 200 but JS-walled |
| **Bing HTML** | **worked** - organic results, no CAPTCHA |

Bing wraps every result in a `bing.com/ck/a?...&u=a1<base64>` redirect; decoding the base64 yields the real URL (`html.unescape` first - HTML entities hide the `&u=`). `bing_urls()` + `search_urls()` (DDG first, Bing fallback) landed in `gather.py`, wired into `investigate_into_session`, and the tests repointed to patch the new seam. **133 passed**, committed `b4642f4`.

### 4.6 End-to-End Verification (or: Claims, At Last)

Live on the throwaway KB at `/tmp/kebab-autotest`:

- `auto=true` -> `{"status":"draft","parent_revision":"none","gathered":2,"sources":2,"error":null}`.
- Clean evidence (Wikipedia ingestion) -> **8 claims, 2 sources, 8 changes** through the real proxy with the master key.
- Junk evidence (Bing served an Aakash login page and generic "what is history" SEO articles for some queries) -> `claims: []`, correctly - the LLM declined to invent.

The pipeline was functionally complete. The remaining wart was evidence *quality* on junk-heavy queries - a search-engine/SEO artifact, not a code bug.

## 5. Retirement (or: Everything Has an End, Even the Good Sessions)

The user decided this version of kebab had run its course for now:

1. **Save as `-legacy`**: `/srv/repo/knowledgebasebuilder` moved to `/srv/repo/knowledgebasebuilder-legacy` - full git history intact (`e8a4bdf` through `b4642f4`). Local scratch mirror renamed to match.
2. **Restore nix-lab**: tagged `kebab-retired` at the last kebab HEAD, then `git reset --hard 5ff0f4d` (the commit before `3102c02` introduced `common/web/kebab.nix`). All eight kebab commits were contiguous and kebab-only, so the restore is byte-clean: `default.nix` back to `[ ./caddy.nix ./codebot.nix ]`, `kebab.nix` gone. `nix eval` confirmed `systemd.services.kebab-api` no longer exists.
3. **Runtime cleanup**: stopped `kebab-api` and the `kebab-web-build.path` watcher; the user rebuilt (`#workstation`), which dropped the units and the Caddy vhosts; deleted `/srv/www/kebab` and the throwaway `/tmp/kebab-autotest`.

## 6. Verification Status

| Check | Result |
|---|---|
| Services layer suite | 128 passed |
| + web sessions | 131 passed |
| + auto-run | 133 passed |
| + Bing fallback | 133 passed (local + homelab) |
| Live auto-run (throwaway KB) | gathered/cited populated, `error: null` |
| LLM round-trip via proxy + master key | 8 claims / 2 sources / 8 changes on clean evidence |
| Post-reset `nix eval` | `kebab-api` attribute absent |
| Post-rebuild units | `kebab-api.service` / `kebab-web-build.path` "could not be found" |

## 7. Recommendations

- **Do not re-deploy web research until evidence quality is solved.** The auto-run loop is solid; the weak link is search-engine junk crowding `findings.md`. A content-quality gate (skip login pages, boilerplate-only text, bare-domain homepages) plus preferring Wikipedia article URLs would raise the claim yield dramatically. That work lives cheaply in the archived repo.
- **Keep the `-legacy` directory as a frozen reference**, not a delete target. It is the reference implementation for the services layer and the `autopilot` contract.
- **Reuse the infrastructure patterns.** The `pkgs.writeShellScript` credential wrapper, the `/run/wrappers/bin/sudo` path, the caddy-vhost-only-bound API - all portable to the next web service.
- **Treat search-engine throttling as environmental.** When a home IP gets flagged, rotate engines before rotating code. Verified order of preference under this network: DDG -> Bing HTML -> (Mojeek only behind a friendlier IP).

## 8. Open Questions

- Does a future kebab revisit want the GUI at all, or is the CLI the honest home for a research pipeline?
- If it returns, should `plan/apply` also be web-exposed, or is that review workflow better left to `git` + a terminal?

---

Generated by Big Pickle (OpenCode)