# Campus platform operations

## Scope and safety boundary

This repository implements the platform software. It is not evidence of campus deployment, verified energy savings, metrology accuracy, mains isolation, or hardware certification. Development devices and telemetry are explicitly `SIMULATED`. Physical dispatch is explicitly disabled and its release allowlist is empty; no MQTT broker or physical actuator is enabled by default. Production starts empty unless an operator imports authorized sources. A strategy approval only approves a shadow evaluation.

The current tested versions and results belong in [Docker verification](DOCKER_VERIFICATION.md); this runbook alone does not assert that a command was run. The image references are pinned by digest. Python and npm dependencies are locked. Refresh pins through a reviewed update and rerun acceptance tests, rather than silently following `latest`.

## Prerequisites

- A machine with Docker Engine 28+ and Docker Compose v2.26+ (or Docker Desktop using Linux containers). Older Docker engines have a documented localhost-publishing exposure to other hosts on the same L2 network; see [Docker port-publishing guidance](https://docs.docker.com/engine/network/port-publishing/)
- For the full 603-space simulated fixture, start with at least 4 vCPUs, 8 GB available RAM and 12 GB free disk as a development recommendation, then measure on your machine. This is not a certified capacity bound. The 2-vCPU / 2-GiB emulated QA guest saturated and hit a 90-second classroom-read proxy timeout. Production sizing requires load testing with the institution's actual device count and retention policy
- Linux containers on Windows; use a local NTFS checkout or WSL2, not a network share
- Port 8080 free on localhost. No database or API port is published
- Registry/package access during builds. BuildKit is required for optional build-secret support

The pinned PostGIS image packages PostgreSQL 17.11 and PostGIS 3.6.4. Its manifest publishes `linux/amd64` only (verified against Docker Registry on 2026-09-30); Compose selects that platform explicitly. ARM hosts require Docker's AMD64 emulation. Native Apple Silicon deployment has not been claimed or qualified. Use tested AMD64 hardware for production until another architecture is qualified.

## Development startup

From the repository root:

```sh
pwsh -File tools/start-dev.ps1
# Or directly:
docker compose -f compose.yaml up --build -d --wait --wait-timeout 600
```

Windows PowerShell:

```powershell
.\tools\start-dev.ps1
```

Open http://localhost:8080. Explicit development fixtures are `admin`, `operator`, `analyst`, and `viewer`, all with password `development-only`. These are deliberately blocked in production. Do not expose this development stack to the network or change its loopback port binding. The database bootstrap credentials in `compose.yaml` are development-only, with an unprivileged application role distinct from the bootstrap administrator.

- `db`: PostgreSQL/PostGIS with a named persistent volume
- `migrate`: one-shot Alembic schema migration after the database becomes healthy
- `api`: authenticated HTTP API after successful migration
- `worker`: durable simulated command transitions, source simulation and heartbeat
- `analysis`: independently queued hourly projections and forecast evaluation after API readiness
- `web`: non-root nginx serving the built frontend and same-origin API/spatial requests

```sh
docker compose ps -a
docker compose logs --tail 100 api worker analysis db web
curl --fail http://localhost:8080/health/ready
```

Optional Python hot reload:

```sh
docker compose -f compose.yaml -f compose.dev.yaml up --build -d
```

Frontend source changes require rebuilding `web`. Do not copy workstation `node_modules` into an image. Native frontend development uses its documented npm/Vite commands and API proxy.

## Production preparation and first startup

Do not overlay production on development. `compose.prod.yaml` is a separate configuration and project, with a separate database volume. It refuses missing origin/host/image-tag values and has no fixture accounts, demo seeding, automatic migration or public listening port.

1. Copy `.env.production.example` to `.env.production`; replace the example institution hostname and release tag. `CARBENTRA_ALLOWED_ORIGINS` must be an explicit JSON array of HTTPS origins. `CARBENTRA_TRUSTED_HOSTS` must include the institution host plus local health-check names; never use `*`.
2. On Windows, first create an empty `.secrets` directory and restrict its NTFS ACL to the operator and Docker Desktop; Python `chmod` does not establish that ACL. Then run `python3 tools/create-local-secrets.py` (Windows: `py tools/create-local-secrets.py`). The operator chooses and enters the initial administrator password locally. The script creates random database credentials, refuses overwrites, never prints secrets, and stores them outside Git. Do not send these files in chat or commit them.
3. On POSIX the directory is mode 0700 and individual secret files are 0444 so a non-root container can read its bind-mounted file. Docker Compose ignores secret UID/GID remapping for local file sources. On Windows, restrict the directory's NTFS ACL to the operator and Docker Desktop. For a real deployment prefer an institution-managed secret store and its supported mounts.
4. Install/configure the institution's TLS reverse proxy to forward its approved HTTPS host to `127.0.0.1:8080`. This template does not obtain a certificate, publish DNS, expose a network port, or set up that proxy. Secure session cookies require HTTPS for normal use.
5. Start the first production deployment with the explicit bootstrap overlay:

```sh
docker compose --env-file .env.production -f compose.prod.yaml -f compose.bootstrap.yaml config --quiet
docker compose --env-file .env.production -f compose.prod.yaml -f compose.bootstrap.yaml up --build -d --wait --wait-timeout 180
```

6. Import the reviewed spatial reference package explicitly, after migrations. This imports source campuses/buildings/floors/spaces only. It does not create accounts, registered devices, telemetry, tariffs or synthetic consumption. First inspect the check output and the release's manifest version; then replace the placeholder with that reviewed version:

```sh
docker compose --env-file .env.production -f compose.prod.yaml run --rm --no-deps migrate python -m app.import_spatial --check
docker compose --env-file .env.production -f compose.prod.yaml run --rm --no-deps migrate python -m app.import_spatial --apply --expected-version '<reviewed-manifest-version>'
```

The import is transactional and refuses source/parent identity changes or removals. After application, `/api/v1/system/status` reports bundled/imported spatial hashes and synchronization. Repeat the check and review changes as part of future spatial-package upgrades; never substitute development seeding for this production import.

7. Verify the intended admin can log in through the approved HTTPS host and that `/api/v1/system/status` reports production mode, database health and disabled physical control. Then remove the bootstrap secret from the API's runtime configuration:

```sh
docker compose --env-file .env.production -f compose.prod.yaml up -d --no-deps --force-recreate api
```

Keep the initial admin password in the operator's approved password manager. Ongoing production starts use only `compose.prod.yaml`. The database user is not a superuser and cannot create roles or databases. The API, worker and analysis processes use a read-only root filesystem, a bounded temporary filesystem, a non-root user, dropped Linux capabilities and `no-new-privileges`. API, worker, analysis and database use an internal-only network with no outward connectivity. Only the static web proxy also joins a normal bridge so Docker can materialize its localhost-only published port. The API disables uvicorn's automatic proxy-header trust. `CARBENTRA_TRUSTED_PROXY_CIDRS` is empty by default, so forwarded client IPs are ignored. If accurate client-IP attribution is required, an operator must review and configure only the actual proxy network and ensure the first public proxy overwrites untrusted incoming forwarding headers. These controls do not replace an institutional security review, external TLS, secret rotation, firewall policy, backup encryption or monitoring.

### Corporate package CA / proxy

The delivered images do not contain this test environment's CA or proxy settings. For a build behind an authorized intercepting proxy, optional BuildKit secret `build_ca` supplies a trusted CA bundle only to the pip/npm installation step. Use Docker's standard `HTTP_PROXY`/`HTTPS_PROXY` build arguments. Never disable TLS checks or commit credentials. Keep any environment-specific Compose build-secret override outside source control.

## Migrations, upgrades and rollback

`python -m app.migrate` applies the pinned Alembic head. Compose gates API startup on the one-shot migration's successful exit; do not remove that dependency. `CARBENTRA_AUTO_MIGRATE=false` is mandatory in production.

For a release:

1. Verify the exact source commit, dependency locks, spatial manifest version and tested image tag
2. Take a database backup and pass the isolated restore check below
3. Schedule a maintenance window; stop writers (`web`, `api`, `worker`, `analysis`) while retaining `db`
4. Run the new release's one-shot migration, inspect its exit status and schema revision
5. Start the tested API, worker, analysis and web images; run login, RBAC, registry, reporting and simulated command smoke tests
6. Verify old records, new records and source/provenance labels; observe health and logs

Do not assume schema downgrades are safe. Reusing an old image with a newer schema is allowed only if compatibility was explicitly tested. Otherwise rollback means restoring the pre-upgrade backup into a fresh database volume and using the corresponding previous image/spatial snapshot. Preserve the failing volume for diagnosis; never use `docker compose down -v` as an upgrade step.

## Backups and isolated restore checks

Use PostgreSQL custom-format dumps, retain the matching image digest/source commit/spatial manifest, and protect backups as sensitive institutional data. The backup contains users/session data, telemetry, audit events, commands and reports. The script does not send backups externally or encrypt them; apply the institution's approved at-rest encryption and retention controls.

Development:

```sh
pwsh -File tools/backup.ps1 -Destination backups/campus-2026-09-30.dump
pwsh -File tools/restore-check.ps1 -Backup backups/campus-2026-09-30.dump
```

Production (Compose reads `COMPOSE_FILE` and `COMPOSE_ENV_FILES`):

```sh
export COMPOSE_FILE=compose.prod.yaml COMPOSE_ENV_FILES=.env.production
pwsh -File tools/backup.ps1 -Destination backups/campus-before-upgrade.dump
pwsh -File tools/restore-check.ps1 -Backup backups/campus-before-upgrade.dump
```

Windows PowerShell:

```powershell
$env:COMPOSE_FILE = 'compose.prod.yaml'
$env:COMPOSE_ENV_FILES = '.env.production'
.\tools\backup.ps1 -Destination backups\campus-before-upgrade.dump
.\tools\restore-check.ps1 -Backup backups\campus-before-upgrade.dump
```

The PowerShell backup uses `docker cp` rather than text redirection, preserving binary dumps on Windows PowerShell 5.1. A unique temporary destination and non-overwriting file move prevent replacing an existing backup; container-side dump files are restricted to mode 0600. On Windows, restrict the backup directory NTFS ACL to the operator and authorized backup administrators before use. Windows execution is not verified in this Linux-only acceptance environment. Restore checks create a unique temporary database and never replace the live database. They stop on PostgreSQL restore errors, preserve original object owners and grants, check the schema revision and read devices/reports using the non-superuser application role, then remove the temporary database. A fresh recovery target must first provision the same `carbentra` and `carbentra_bootstrap` roles through the approved database initialization; suppressing owners or grants can produce a restore that the application cannot use. Regularly test actual record counts and application reads on a restored disposable deployment as well; a successful dump command alone is not recovery evidence. Before a real restore, stop writers, obtain the operator's explicit target/downtime approval and restore into a fresh volume. Restoring a database is not safe while live writers continue. Recovery also restores the old authentication/session state: after an approved recovery, revoke restored sessions and require fresh sign-ins so sessions revoked since the backup do not silently become valid again. Keep physical dispatch disabled during recovery; reconcile device boot epochs, sequences, commissioning and release authorization before any separately approved physical restart.

## Persistence and stop/reset

`docker compose restart api worker analysis web` preserves records. `docker compose down` also retains the named database volume. The init script runs only on a new empty volume; changing a secret file does not rotate an existing PostgreSQL password. Use an approved coordinated credential rotation procedure instead.

`docker compose down -v` deletes the named database volume and is destructive. It is only appropriate for an explicitly disposable development deployment, after confirmation that no needed records remain. This handoff never calls it on a production deployment.

## Operational acceptance checklist

- Public live/ready and web health are healthy; persisted worker heartbeat is recent
- Viewer mutations and cross-origin/CSRF-less requests fail; production rejects dev auth and SQLite
- Unknown or stale data is visibly incomplete, never zero/safe/vacant
- Source mode/provenance, observed/received time and Wh units survive ingestion and reporting
- Telemetry retries deduplicate durably; conflicting retries fail; replayed/real actuation fails closed
- Simulated command success, rejection, failure and timeout have persisted transition history
- Parent/child meter overlap does not double-count; carbon/cost use explicit dated factors/tariffs
- Device binding changes clear commissioning/control authorization
- API/worker restart preserves users, telemetry, reports and command history
- Backup restores into an isolated database with matching application records
- No production secrets, dump files, credentials or `.env.production` appear in Git or images

## Troubleshooting

- `migrate` failed: inspect `docker compose logs migrate db`; do not force-start API against an unknown schema
- API unhealthy: inspect `logs api`; check trusted hosts, valid PostgreSQL URL, bootstrap admin and production guards
- Worker unhealthy: inspect `logs worker`, database reachability and persisted heartbeat; never label a requested command successful because a worker is down
- Blank SPA route: verify nginx fallback and built frontend; API requests must proxy under `/api/v1`, not return `index.html`
- Spatial artifact unavailable: inspect pinned manifest/path. Do not substitute invented geometry or fake model success
- Secure-cookie login fails on plain HTTP production: complete the approved HTTPS reverse proxy setup
- Docker unavailable in a restricted runner: report it honestly. Native tests and `docker compose config` alone do not prove containers ran

## Reference documentation

- [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)
- [Compose environment-file and project selection](https://docs.docker.com/compose/how-tos/environment-variables/envvars/)
- [Official Python image](https://hub.docker.com/_/python), [Node image](https://hub.docker.com/_/node), [nginx image](https://hub.docker.com/_/nginx)
- [PostGIS image](https://hub.docker.com/r/postgis/postgis/)

### Local production-mode acceptance fixture

`tests/deployment/production_smoke.py` is a stdlib-only test for a disposable loopback HTTPS fixture. It requires an explicit test flag, a trusted test certificate, a test-only administrator whose username starts with `container-test-`, and a local password file. It checks fixture-password rejection, verified HTTPS, Secure/HttpOnly/SameSite cookies, cleartext session refusal, production/no-demo/no-actuation status, CSRF/origin rejection and logout. It must not be pointed at a real production account. The fixture TLS proxy and test private key are not shipped as production infrastructure.

## Optional unified Edge / MQTT transport packaging

The default stack has no broker. `compose.transport.yaml` adds an explicitly configured mTLS Mosquitto broker, a private HTTPS adapter gateway, and this platform's authoritative `edge/` service. Its image copies `edge/` and `packages/iot-contract/` from the same reviewed platform build context. The hardware checkout is no longer a runtime build input; its former Edge implementation is retired.

Required operator configuration:

- `CARBENTRA_TRANSPORT_DIR`: private directory (0700 or equivalent NTFS ACL), with individually readable mounted files as described in the production secrets section
- `CARBENTRA_ADAPTER_ALLOWED_DEVICE_IDS`: exact JSON array of explicitly enrolled device IDs; the platform registry and edge `devices.json` must agree
- `adapter_token`: deliberately provisioned scoped adapter bearer token, at least 32 characters. It is mounted only to API and edge, never written into Compose environment text or images
- `mqtt-ca.crt`, `broker.crt`, `broker.key`: reviewed broker trust chain and certificate with DNS SAN `broker` (plus any authorized external client hostname)
- `edge.crt`, `edge.key`: distinct client identity with clientAuth usage. Its certificate CN must match the explicit edge ACL identity
- `platform-ca.crt`, `platform.crt`, `platform.key`: reviewed private HTTPS chain, with the server certificate containing DNS SAN `platform-tls`
- `mosquitto.acl`: reviewed exact-topic ACL (start from `infra/mosquitto.acl.example`)
- `devices.json`: typed Plug/Switch/Sense enrollments following `edge/examples/devices.example.json`; the disposable six-device/two-room example is `edge/examples/devices.virtual.json`. Enroll device IDs, product families, source modes and allowed transports explicitly. Legacy Plug-only `devices`/`virtual_devices` files remain a migration path, not a second contract source.

No production CA, private key, certificate, enrollment or adapter token is created by these templates. The operator must provision/approve that persistent access. An mTLS device identity may write only its own hello/telemetry/ack and read only its own cmd/time/receipt. The edge gets the inverse permissions only for its enrolled devices. Never grant `write #`. The non-root broker copies only its own mounted secrets into a mode-0700 tmpfs directory with mode-0600 files owned by uid 1883 before startup. This avoids relying on unsupported Compose bind-secret UID remapping and keeps the ACL/private key private inside the container. Mosquitto ignores username impersonation because identity comes from the client certificate. Anonymous connections, plaintext MQTT and retained messages are disabled. The broker caps the entire MQTT packet at 8192 bytes, including topic/protocol headers, before forwarding to the edge. This is intentionally stricter than the edge's 8192-byte raw-payload ceiling; client payloads must leave room for headers. See [Mosquitto packet-size semantics](https://mosquitto.org/man/mosquitto-conf-5.html).

```sh
# Add the required values to the approved environment file first.
docker compose --env-file .env.transport -f compose.yaml -f compose.transport.yaml --profile transport config --quiet
docker compose --env-file .env.transport -f compose.yaml -f compose.transport.yaml --profile transport up --build -d
```

For production, substitute `compose.prod.yaml` and the approved combined production/transport environment. The broker publishes only `127.0.0.1:18883` for local enrolled-client verification. Do not change network exposure without an approved institutional security plan. The edge/broker transport network cannot directly reach the database. Only the broker also joins a normal bridge to materialize its localhost-only published MQTT port. The edge's platform requests use HTTPS with CA and hostname validation; no insecure HTTP exception or proxy forwarding is enabled.

The default transport overlay forwards measurements/ACKs but does not poll or publish commands. Only an explicitly disposable SIMULATED/VIRTUAL enrollment may use the separate `compose.transport.virtual.yaml` opt-in overlay. Physical dispatch remains explicitly disabled in these templates, with an empty release allowlist; adding a source-code path does not authorize hardware operation. A broker PUBACK is delivery evidence only. Switch commands require an explicit `relay.1`, `relay.2` or `relay.3` target and the command ledger remains `acknowledged_unverified` after a correlated actuator report: the current Switch has no independent contact feedback or per-relay meter. Aggregate power is never copied into three relay measurements. Plug verification still requires durable correlated device feedback. BLE scanning is off by default; the container does not mount a radio or host D-Bus. Enabling BLE needs a separately reviewed host integration.

The broker health check confirms the configured broker process is alive. The edge health check verifies its SQLite database; neither is an end-to-end telemetry freshness claim. Inspect durable forwarding backlog, platform receipt timestamps and per-device freshness. Keep the `edge_data` volume: it contains raw evidence, deduplication identities, pending outbox deliveries and command transport state. Deleting it destroys retry/restart evidence. Deployment qualification must include the actual broker/edge test results recorded in `DOCKER_VERIFICATION.md` and the independent transport acceptance record.

## Background forecast analysis

`analysis` runs the same pinned backend image with `python -m app.worker --role analysis`, independently from the latency-sensitive control/simulation worker. It starts only after API readiness, so an atomic development seed has finished; production still imports reference data explicitly and never seeds demo measurements. It has no administrator bootstrap secret. It rebuilds bounded hourly projections and evaluates queued forecasts outside request/control loops, yields between batches and lowers its own CPU priority. Cold rebuild duration is visible as queued/running work, not presented as an immediate completed forecast.

Its stdlib-only `app.worker_health --role analysis` probe checks an atomic local heartbeat tied to the live PID/start identity, with a 180-second freshness threshold. The control heartbeat remains 10 seconds and command feedback remains five seconds. A healthy analysis process alone does not mean its projection or every queued job is complete; inspect job state, projection watermark and coverage. Migration `ba682468c8c6` follows `6d7d7c3c7c86`; an upgrade must run all migrations before starting this role.

## Classroom / unified-contract upgrade

The classroom schema chain after `ba682468c8c6` is `273cb450c2f7` → `22dd42bc323d` → `23281196af6d` → `98f4a5aa6b9d`. Run the tested image's explicit migration service before API, control, analysis or Edge. Keep the shared `packages/iot-contract` bytes identical in API and Edge images, and retain the generated frontend OpenAPI identity beside the release manifest. `tools/run_system_upgrade_postgres.sh` tests an actual old-head upgrade, idempotent repeat and canonical classroom behavior on cloned migrated PostgreSQL databases.

Production still never auto-seeds. The v3 development fixture deliberately rejects an older synthetic primary-meter boundary: adding 603 classroom loads to old historical parent-meter samples would falsify accounting. Preserve that database and its backup, then use a separately named disposable development database/volume to generate the v3 fixture. Do not edit its seed marker to bypass the guard, relabel old samples or reset a real operational database.

The new Edge performs one versioned migration before starting any transport. Old delivered telemetry outbox records are archived with their original delivered marker; they are never resent. Pending legacy Plug rows convert only when the original raw receipt and explicit enrollment establish identity, source and time. Missing or inconsistent evidence is quarantined with the exact original row, rather than guessed, deleted or assigned the migration time. ACK rows and original telemetry receipts remain intact. Never run the retired gateway and the unified gateway as concurrent writers on one SQLite file.

Before replacing Edge, stop it and back up the complete `edge_data` directory, including any SQLite WAL/SHM files. The new image includes two small operator tools, with no test framework:

```sh
# Read-only backlog, migration and transport-health report
# Include the appropriate approved Compose files/environment for your deployment.
docker compose --profile transport exec -T edge python tools/status.py --database /data/edge.sqlite3

# Only after stopping Edge, backing up DB/WAL, reviewing quarantined evidence,
# and correcting the exact enrollment; this is an explicit operator retry.
docker compose --profile transport run --rm --no-deps edge python tools/migrate_legacy.py \
  --database /data/edge.sqlite3 --devices /run/secrets/edge_devices --retry-quarantine
```

A successful schema migration or healthy process is not proof of source freshness, physical actuation, or recovered pending delivery. Verify counts, retained receipt times, backlog disposition and device-specific ACK correlation. On rollback, preserve the upgraded database for diagnosis and restore a tested pre-upgrade backup into a separate volume; do not destructively downgrade retained classroom/command evidence.

Product reference HTTP requests now require the explicit `family=PLUG`, `family=SWITCH` or `family=PRESENCE` query parameter. The pinned catalog provides distinct GLB and 640-pixel derived hero identities; all images are engineering references, not site photographs. The focused `tests/system_upgrade/asset_transport.py` verifier checks authenticated family routing and decoded model/hero hashes. Its HTTP result does not establish browser WebGL rendering.
