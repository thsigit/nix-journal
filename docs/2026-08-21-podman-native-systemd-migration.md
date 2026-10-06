# The LiteLLM Gateway Evolution - Part 13

*Podman to native systemd migration*

**Date:** 2026-08-21  
**Author:** Codebot  
**Topic:** LiteLLM, NixOS, homelab, Podman, refactor, migration

---

## 1. Objective

Replace the Podman-container-based LiteLLM gateway (`litellm-podman.nix`) with a native NixOS systemd service, eliminating the container runtime dependency while preserving the existing Caddy reverse proxy and litellm-cli config pipeline.

## 2. Background

The LiteLLM gateway had been running as a Podman OCI container (`ghcr.io/berriai/litellm:v1.92.0`) with host networking, mounted config from litellm-cli, and PostgreSQL for DB features. The container approach worked but added operational complexity: image pulls, container health checks, a separate restart-helper systemd path unit, and a dedicated appdata directory (`/srv/appdata/litellm-podman/`).

Meanwhile, nixpkgs ships a native `services.litellm` module that runs LiteLLM as a systemd service with DynamicUser isolation and security hardening. The migration path was clear: retire the container, wire up the native service.

## 3. History

| Commit | Description |
|--------|-------------|
| `65ed828` | Moved LiteLLM modules into `common/ai/litellm/` subdirectory |
| `db4e196` | Fixed DATABASE_URL read from `database.env` |
| `e06c69c` | Consolidated `litellm.env` into `providers.env` |
| `03109e3` | Retired Podman, created native `litellm.nix` |
| `cbfeaa7` | Removed PostgreSQL (no-DB mode due to upstream Prisma issue) |
| `f1f7a31` | Fixed quotes stripped by heredoc |

## 4. Why Native Over Podman

| Aspect | Podman | Native |
|--------|--------|--------|
| Runtime | Container image + conmon | systemd DynamicUser |
| Config source | Container volume mount | `--config` flag to store path |
| Restart helper | `litellm-podman-helper.nix` (path unit) | Built-in systemd restart |
| Security | `--cap-drop=ALL`, `--security-opt=no-new-privileges` | `ProtectHome`, `DevicePolicy=closed`, `RestrictNamespaces`, etc. |
| DB access | PostgreSQL via container networking | Removed (no-DB mode) |
| Image management | Manual `podman pull` | Declarative via nixpkgs |

## 5. Work Performed

### 5.1 Created native litellm.nix

New module at `common/ai/litellm/litellm.nix` that defines `systemd.services.litellm` directly. Key decisions:

- Port pinned to 4000 (matching historical value, avoiding collision with `services.llama-cpp` on 8080)
- Consumes litellm-cli rendered `config.yaml` via `--config` flag (not the native module's `settings` attrset)
- Provider API keys passed via `environmentFile` (sops-decrypted `providers.env`)
- Caddy reverse proxy wired via `services.caddy.services.litellm`

### 5.2 Removed PostgreSQL dependency

The nixpkgs LiteLLM package (v1.83.14) has a known upstream issue: Prisma client generation is broken. The service crashes with `RuntimeError: The Client hasn't been generated yet` on startup. Since this is unfixable in nixpkgs, the decision was to run in no-DB mode.

Why the Podman container worked but the native package does not:

- **Podman container** - The upstream image (`ghcr.io/berriai/litellm`) bundles `prod_entrypoint.sh`, which runs `prisma generate` at container startup in the writable overlay filesystem. The generated client lives in `/app/prisma/` inside the container, ephemeral and recreated each start. The container has full write access to its own filesystem.
- **Native nixpkgs package** - The LiteLLM derivation includes `prisma` as a Python dependency, but the generated client artifacts are not part of the build. At runtime, LiteLLM tries to write the generated client to the Nix store (read-only), or to a path the `DynamicUser` cannot reach. The nixpkgs module's `ExecStartPre` only seeds the tiktoken cache and fixes UI permissions - it has no `prisma generate` step.

The core issue: nixpkgs packages are immutable store paths. Prisma generation is a runtime operation that writes to the filesystem. The upstream Docker image solves this by running it in a writable layer; NixOS has no equivalent without an explicit `ExecStartPre` or patching the package to pre-generate during build. This is an upstream gap in the nixpkgs LiteLLM module.

Changes made:

- Removed `common/db/default.nix` from imports (archived as `.old`)
- Removed `database.env` from `environmentFiles`
- Removed `postgresql-setup.service` and `litellm-db-password.service` ordering

Why not SQLite instead of removing the database entirely: the Prisma error (`The Client hasn't been generated yet`) happens before LiteLLM even tries to connect to a database. Prisma is the ORM layer - it needs its generated client to talk to *any* database, PostgreSQL or SQLite alike. The generated client contains the query engine, type bindings, and schema mappings. Without it, LiteLLM cannot open a database connection at all. Switching `DATABASE_URL=postgresql://...` to `DATABASE_URL=file:./litellm.db` would hit the exact same `RuntimeError`. The problem is not PostgreSQL-specific. It is a Prisma-in-NixOS problem.

Trade-off: no spend tracking, no user/key management via UI. Pure API proxying.

### 5.3 Archived old modules

- `litellm-podman.nix` renamed to `litellm-podman.nix.old`
- `litellm-podman-helper.nix` renamed to `litellm-podman-helper.nix.old`
- `common/db/default.nix` renamed to `default.nix.old`

### 5.4 Updated documentation

- `AGENTS.md`: all litellm-podman references updated to native service
- Module comments updated to reference `./litellm.nix` instead of `./litellm-podman.nix`

## 6. What Broke (and Was Fixed)

**Prisma crash** - The first rebuild failed with `exit-code=3` and the Prisma error. Root cause: nixpkgs LiteLLM module has no `prisma generate` in ExecStartPre. Fix: removed PostgreSQL entirely.

**Heredoc quote stripping** - Writing Nix files via SSH heredoc (`cat > file << 'EOF'`) stripped all double quotes, producing `description = LLM Gateway...` instead of `description = "LLM Gateway..."`. Fix: wrote the file locally with the `write` tool and `scp`'d it to homelab.

## 7. Verification

```text
$ curl http://127.0.0.1:4000/health/liveliness
"I'm alive!"

$ litellm-cli providers
  nvidia, openrouter, ollama, freetheai

$ litellm-cli debug doctor
  nvidia: healthy (393ms)
  openrouter: healthy (245ms)

$ litellm-cli models
  93 models listed
```

## 8. Recommendations

- Monitor LiteLLM stability in no-DB mode; if spend tracking is needed later, revisit when nixpkgs fixes Prisma generation
- The archived `.old` files in `common/ai/litellm/` and `common/db/` can be deleted once the native service is confirmed stable
- Run `litellm-cli debug doctor` periodically to verify provider health
