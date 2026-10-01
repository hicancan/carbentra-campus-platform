# Isolated public simulation deployment

This is the maintained Campus API, React frontend, PostGIS database, control/simulation
worker and analysis worker, with a dedicated HTTPS gateway. It is not a static copy,
public development server, tunnel, hardware bridge or alternative Sites implementation.
All operational samples and command results are explicitly **SIMULATED**; real campus
geometry is reference data, not a claim of installation or measured energy savings.

## Security and lifetime contract

- Use **only** `compose.public-demo.yaml`. Never merge development, production,
  bootstrap or transport overlays into it. Ordinary `compose.prod.yaml` stays unseeded
  with simulation disabled. Public simulation uses production authentication, Secure
  HttpOnly same-site cookies, CSRF checks, HTTPS origins and scoped server-side roles.
- The visitor account is a real hashed-password **viewer**, scoped to the imported
  campuses. Its authenticated mutations are denied except its own logout. A separate
  private **operator** can explicitly evaluate/dispatch existing simulated controls;
  a separate private administrator is provisioned. Do not publish either private
  credential. No development password or automatically signed-in shared admin exists.
- Identity, device/topology, commissioning and external ingest/adapter mutations are
  unavailable through the demo API, even to the demo administrator. There is no MQTT,
  Edge, physical device mapping or physical-release allowlist. Configuration refuses
  physical dispatch/adapter credentials in this mode, and a demo-only database
  constraint requires every device to remain `SIMULATED` / `IN_PROCESS` without a
  physical release. Changing the environment mode cannot repurpose this database as
  an operational production database.
- Migrations first require the dedicated database **and role** `carbentra_public_demo`,
  PostGIS, a restricted application role and a bootstrap-owned database comment matching
  the generation ID. Initialization additionally requires every application table to
  be empty. Its explicit ID confirmation is mandatory. An interrupted initialization
  stays failed, never resumes over partial data. A completed matching initialization
  is a verified no-op; changed secrets are rejected rather than silently rotated.
- Default lifetime is **continuous** (`CARBENTRA_PUBLIC_DEMO_LIFETIME_HOURS=0`). A value
  from 1 to 720 opts into expiry at initialization. Restart never extends a recorded
  deadline. No automatic deletion/reset is performed. The API and all writers are
  supervised and stop after optional expiry or database budget exhaustion; an expired
  API also rejects requests immediately. Availability requires operator capacity and
  retention management, not an unlimited storage promise.

## Prerequisites and authorization

Before provisioning: approve the hosting account, region, recurring cost/budget,
public hostname/DNS changes and public access. Choose a dedicated host/project and
storage containing **no real user, student, staff, telemetry or operational data**.
No external deployment, DNS/account change, certificate issuance or persistent real
credential creation is implied by the local checks described below.

Use the official Docker Engine **28+** and a current official Docker Compose, with PowerShell
7 for the commands below. The pinned PostGIS image is linux/amd64; use an amd64 target
(or separately accept/test emulation). Start with at least 4 vCPU / 8 GiB RAM, 20 GiB
available image/build storage and a separate database volume with at least 10 GiB
capacity. These are starting budgets, **not a benchmark or an accepted hosting cost**.
The full reference and seed are sizable; a fresh clone includes the locked consumption
assets and needs no other repository or developer-specific filesystem path.

Get an operator-managed trusted TLS full chain and key for the approved hostname.
Certificate issuance/renewal is outside this package, and is not silently registered
with a CA. Do not use `curl -k`, bypass browser warnings or expose the development
HTTP endpoint. Use an existing trusted local CA for a private acceptance test, or
validate an authorized public certificate before making the target public.

## Fresh-clone launch (operator-run; not executed as a deployment in this review)

1. Clone the reviewed commit. In its root, run `uv sync --locked --all-groups` if Python
   tooling is needed. Copy `.env.public-demo.example` to `.env.public-demo` and edit:
   - a unique lowercase `CARBENTRA_PUBLIC_DEMO_ID` (8–48 characters)
   - the reviewed image tag and approved DNS hostname
   - absolute **external** secrets/TLS directories
   - a non-overlapping private network prefix (default `172.30.88`)
   - the storage budget and optional expiry; default expiry is off
   Keep `CARBENTRA_DEMO_BIND_ADDRESS=127.0.0.1` until target acceptance and public-host
   authorization. Each ID creates its own Compose project and database volume.
2. After approving persistent account setup, create a private parent directory outside
   the checkout and run this helper **yourself on the target**:

   ```powershell
   uv run python tools/public-demo-secrets.py --directory /absolute/private/public-demo/secrets
   ```

   Run this helper on a POSIX host with real Unix permission enforcement (the intended
   Linux deployment target); it refuses other hosts rather than assuming their ACLs.
   It exclusively creates five independent random passwords and the matching database
   URL; it prints no values and never replaces existing files. The secret directory
   is mode 0700. Files are 0444 because local Compose file secrets are read-only bind
   mounts and do not honor uid/gid remapping; the private parent blocks host traversal.
   Keep this permission arrangement, or use an audited deployment secret provider.
   Verify any inherited host ACLs as well. Only initialization receives account
   passwords; long-lived API/worker/analysis containers receive only the DB URL.
3. Place `fullchain.pem` and `privkey.pem` in the external TLS directory. On a Linux
   host, make the key readable **only by the gateway's mapped UID 101** (for example,
   owner 101:101 and mode 0400 inside a private parent). Account for rootless Docker
   UID mapping if used. Do not fix permission errors by making the key public. The
   service mounts just these files read-only. Protect their host parent from other
   users. Check hostname, SAN, validity, complete trust chain and renewal ownership.
4. Set a PowerShell argument array and validate the actual Compose file:

   ```powershell
   $demo = @('--env-file', '.env.public-demo', '-f', 'compose.public-demo.yaml')
   docker compose @demo config --quiet
   docker compose @demo build --pull
   docker compose @demo up -d --wait --wait-timeout 900
   docker compose @demo ps --all
   docker compose @demo logs --tail 80 migrate demo-init api worker analysis gateway
   docker compose @demo exec gateway nginx -t -c /tmp/nginx.conf
   docker compose @demo exec api python -m app.public_demo check
   ```

   Database bootstrap → identity-checked migrations → explicit fresh initialization →
   API → workers/web → HTTPS gateway is enforced by dependencies. Secrets, migrations,
   TLS errors and partial initialization must fail startup. Never treat `config` or
   `nginx -t` as a successful cold start or public HTTPS acceptance.
5. Run the checks below through the **actual hostname and trusted HTTPS chain**, then
   change binding to the approved public interface and open only TCP 80/443 in the
   authorized host firewall. No DB, API, worker or web port is published. Re-run target
   HTTPS and browser checks from outside the host before sharing the URL or visitor
   credential. Do not run the backend or workers directly, bypassing supervision.

## Target acceptance gate (required before calling it deployed)

Record the reviewed commit, OS/architecture, Docker/Compose versions, resolved image
identities, hostname, certificate expiry, UTC times and every observed result. Keep
credentials, cookies and CSRF tokens out of logs/screenshots/reports.

- Fresh volume cold start finishes, migrations are at head and all long-lived services
  become healthy. A second `up` is a no-op for seed/users/deadline; no duplicate seed.
- The UID101 gateway can read the mounted key and `nginx -t` passes. HTTPS chain/SAN
  verifies without bypasses, HTTP redirects to the configured hostname, unknown
  host/SNI is rejected, HSTS is present. Verify that the certificate renews via the
  operator-owned process and reload gateway after renewal.
- Only 80/443 are externally reachable. Spoofed forwarded headers do not defeat login
  throttling; check per-IP and total login rate limits. Normal navigation and SSE
  reconnects remain usable under the configured request/concurrency limits.
- No login is unauthorized (401); `admin` / `development-only` fails. Visitor receives
  Secure/HttpOnly/SameSite cookies, reads the map/history, and cannot command, change
  users/devices/topology, modify policies or ingest data (403). Visitor logout needs
  its valid CSRF token. A separate operator cannot administer users or external IO.
- Operator can explicitly request an eligible simulated Plug/Switch action, follow
  persisted history and observe the documented terminal state. Missing/wrong CSRF
  and cross-origin writes fail. Switch ACK remains `acknowledged_unverified`, never
  a physical-outcome claim. Unknown/stale observations retain their boundaries.
- Restart API/control/analysis and confirm user roles, sessions, commands, source
  labels and seed data persist without reinitialization. Test wrong deployment ID,
  wrong database role/comment, changed init secret and attempts to enable physical
  dispatch: all fail closed without overwriting the database.
- On a separate disposable acceptance generation, test optional expiry and a budget
  below measured database size: API and writers stop; evidence is retained. Do not
  simulate exhaustion by filling the host filesystem. Monitor disk headroom, resource
  limits and health on the final host. Complete the official browser scenario suite
  against this mode as well as the read-only visitor flows.

## Capacity, retention and recovery

CPU, memory, PIDs, temporary files, connection counts and container logs are bounded in
Compose. Gateway login/request limits bound unauthenticated work. Forecast queues and
caches have reduced budgets. Default simulation periods are 60s (general) / 120s
(classroom), with a 180s freshness threshold. These settings preserve semantics but
must be load-tested at the chosen hardware size and expected audience.

`CARBENTRA_PUBLIC_DEMO_MAX_DATABASE_MB` defaults to 4096 (512–16384 allowed). Every
supervisor waits 15 seconds between `pg_database_size` checks and terminates its child
on exhaustion or database-check failure; slow database responses can delay a check.
No more than three automatic retries occur.
This is a **soft application database budget**, not a filesystem quota: an in-flight
transaction can overshoot, and WAL/images/logs are extra. Configure a host volume
quota/reserved headroom separately and alert on 70%/85% volume use plus failed service
health. The full seed contains hundreds of thousands of synthetic observations;
continuous simulation grows storage. Measure actual growth during target acceptance,
then choose an approved disk/retention plan before promising long-term availability.

Do not DELETE historical evidence or disable append-only triggers to make room. For
retention, the operator stops this generation, exports any required synthetic evidence
into private retained storage, and creates a **new generation ID with a new volume and
credentials**. Removing the old volume and retained backups requires explicit approval
of irreversible deletion; this package never runs `down --volumes`, pruning or timed
purges. Retain no operational/personal data in either generation. Simply restarting
or changing the ID against an existing DB never resets or extends it.

If initialization fails after its first write, inspect sanitized logs and keep that
volume for diagnosis. Correct the cause and provision a fresh empty generation after
review; the initializer intentionally refuses partial-state repairs. At budget/expiry,
stop/recover through the same decision path. Source code rollback is safe only if its
schema remains compatible; never point this disposable service at production backups.

## Validation scope for this change

The default pytest suite, CI backend job and `tools/verify-local.ps1` include the new
static checks. CI/local verification explicitly bootstrap a fresh restricted-role
demo test database, so the real-auth integration is not permanently skipped.
Repository unit/static tests and an explicitly isolated native PostgreSQL integration
exercise the configuration gates, migrations/marker checks, initializer, real hashed
login, viewer/operator role isolation, CSRF and expiry. The small integration fixture
is synthetic test data and does not establish a full-campus load benchmark.

On 2026-10-01 a separate native full-campus run also passed initialization, trusted
local-test-CA HTTPS through official nginx 1.30.5, hashed authentication, secure
cookies/CSRF/RBAC, simulated controls, supervised restart, physical fail-closed checks
and login throttling. Its snapshot was 688,551,603 bytes (about 656.65 MiB), with
185,106 telemetry records and 449,941 channel observations after a brief simulation.
This is a measured starting point, not a retention-growth or concurrent-load benchmark.

Native PostgreSQL here is **17.11 / PostGIS 3.5.2**, distinct from the pinned production
image's PostGIS 3.6. This native test used explicit test ports and a trusted local test
CA; it was not Docker or a public deployment. Docker Engine cold start, the official
images, target-mounted production TLS, public DNS/network reachability, and the actual
browser journey must still be accepted on the chosen target. Read the release evidence for exact executed results; absent stages
are not passes. This document/package is preparation, not a claim that a public URL
has been provisioned or that any physical hardware has been released.
