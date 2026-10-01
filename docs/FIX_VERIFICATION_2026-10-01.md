# Clock recovery and isolated demo verification, 2026-10-01

This record covers tests executed for the follow-up fixes to the October 1 delta.
It does not reuse the delta's native-host results as new Docker or hardware evidence.

## Fixed behavior

- Edge validates an observation against the previous trusted clock bound **before**
  changing that bound. A rejected gateway clock rollback, future timestamp, replay
  or inconsistent device clock cannot tighten persistent boot origin incorrectly.
- An additive SQLite migration preserves the existing three clock bounds and adds
  a trusted receipt highwater. Clockless Switch observations now detect gateway
  rollback too. Only receipts within the normal ten-second control freshness limit
  advance this highwater: a gateway forward jump followed by correction recovers,
  while coherent delayed observations still contribute device-clock history.
  Disk-backed tests reopen the store and preserve outbox, deduplication and the
  existing stalled/replayed/monotonic rollback fail-closed behavior. Already poisoned
  bounds from an older version are not silently erased; a new device boot must
  establish an independent bound.
- The first public-demo Docker cold start exposed a real address collision: Docker
  assigned the API the gateway's fixed `.5` address. The dynamic pool is now the
  upper `/25` of the private `/24`, outside that fixed address. A regression checks
  the subnet relationship; a second start used a newly empty database volume.
- Windows verifies the production secret helper's explicit POSIX refusal, while
  Linux verifies its actual permissions and exclusive creation. The existing
  disposable deployment fixture can now also create public-demo test identities
  and expiring localhost certificates; production provisioning remains unchanged.
- The new trusted-HTTPS public-demo checker reports success only after every check
  completes. Network and malformed-JSON regressions demonstrate that a partial
  run writes a failed artifact and raises, even if an earlier check passed.

## Executed results

| Check | Actual result and scope |
| --- | --- |
| `tools/verify-local.ps1` | PostgreSQL migration from `ba682468c8c6` to head, repeated upgrade and Alembic drift check passed. Backend/default suite: **464 passed, 1 optional benchmark skipped**; one upstream Starlette deprecation warning. Restricted-role public-demo test database was actually provisioned. |
| Frontend and spatial in the same local run | **39 files / 200 frontend tests**, formatting and production build passed; **13 spatial tests** passed. |
| Final focused clock regression | **16 passed, 6 subtests**, including actual SQLite close/reopen, old-schema upgrade and both Plug/Switch forward-then-corrected gateway clocks. Both forward-recovery family cases failed before the fix. |
| Final Windows Edge release | **90 passed, 2 explicit POSIX-only skips, 49 subtests**. All four required compiled C gates ran, dependency locks matched, `unexpected_skips=[]`. |
| Final Linux Edge release | **91 passed, 1 inverse non-POSIX skip, 49 subtests** in the Docker test image. All four actual Linux C gates ran, including Switch command decoding; static ASan/UBSan binaries used `ASAN_OPTIONS=detect_leaks=0`. No missing-C gate was counted as a pass. |
| Final Linux MQTT/backend integration | Both source-bound checks passed against actual Mosquitto mTLS and backend HTTP/auth/CSRF. Six simulated devices, three families, two rooms and three target channels; durable backlog/restart drainage, no command replay, no aggregate double counting, preserved terminal ACK after late receipts. ACK remained `acknowledged_unverified`; no physical feedback was claimed. |
| `tools/verify-deployment.ps1` | Fresh ordinary production fixture: **HTTPS 8/8**, **MQTT security 3/3** passed. This deployment check preceded the final Edge clock refinement; the final-source Edge mTLS checks above were rerun afterward. |
| Public-demo Docker cold start | Pinned Linux images, actual PostGIS, mounted disposable credentials/certificates: **six long-lived services healthy**, migration and demo initializer exited zero after the address fix and a fresh empty volume. |
| Public-demo trusted HTTPS | **30/30** passed, including after API/worker/analysis restart and again after the checker's artifact fix. Explicit test CA and hostname verification were enabled; normal system trust rejected that CA. Real hashed login, secure cookies, RBAC/CSRF, denied external ingest/registry mutation, logout and session revocation were exercised. |
| Public-demo repeat/restart | Repeated `compose up` and service restart preserved the ready marker, users and catalog: **3 users, 2,489 devices, 603 spaces, zero non-simulated devices**. The recorded marker/identity snapshots were identical; initialization did not reset the database. |
| Deployment unit regressions | **6 passed on Windows and 6 on Linux**, including the partial-smoke failure cases and the platform-specific secret helper behavior. The earlier complete backend run predates the last two smoke cases; its count remains 464, not 466. |
| Actual Microsoft Edge browser | **9/9**, `errors=[]`, browser sandbox enabled, against a separate fresh **development HTTP** stack. Thirteen routes, the 603-room matrix, metadata-only map fallback, three-channel aggregate, gaps/anomalies, a simulated UI `relay.2` shed with 900-second manual hold and unchanged siblings, unverified terminal ACK, and SHADOW evaluation with no commands. Command/evaluation persisted across actual API restart. |

The final Windows/Linux release artifacts have **69 identical source fingerprints**.
The final MQTT and backend proofs bind 35 and 82 files respectively, all unchanged
during execution. Final `edge/store.py` SHA-256:
`95cc83c78b4a7b5f0af99f179f8087d59c714728da851484e99cc430ca812d4c`.
The four final source-bound artifacts were copied to the smart-plug repository's
`firmware/evidence` and independently checked against all **255** referenced files.

## Reproduction entry points

Use PowerShell 7, the root uv `.venv`, Python 3.12, Node 24 and Docker Desktop Linux
containers. This run used uv 0.11.17, Python 3.12.13, Node 24.16.0, Docker 29.7.2 and
Compose 5.3.1. Start with an unused task output directory and disposable project names.

```powershell
pwsh -File tools/verify-local.ps1 -OutputDirectory <task-output>/local -ProjectName carbentra-check-local -PostgresPort 15432
pwsh -File tools/verify-deployment.ps1 -OutputDirectory <task-output>/production -ProjectName carbentra-check-production -HttpPort 18081 -HttpsPort 18443 -MqttPort 8884
```

For release-mode Edge checks, build the four actual host validators using their
hardware repositories and set `CARBENTRA_STARTUP_TEST_BINARY`,
`CARBENTRA_TIME_TEST_BINARY`, `CARBENTRA_CERT_TEST_BINARY` and
`CARBENTRA_SWITCH_COMMAND_TEST_BINARY` to those files. Run
`uv run --locked --all-groups python edge/tools/run_checks.py --release --output <task-output>/edge-release.json`.
Linux uses `tests/deployment/edge.Dockerfile` and the corresponding Linux executables;
run `tools/run_checks.py --release` inside that image. The same image contains
`tools/check_mqtt_multidevice.py` and `tools/check_backend_multidevice.py`; both were
executed with `/usr/sbin/mosquitto`, and the latter used `/app/.venv/bin/python`.

For **disposable local QA only**, the Windows-compatible fixture entry point is:

```powershell
uv run --locked --all-groups python tests/deployment/create_fixture.py --directory <task-output>/public-fixture --public-demo --disposable-fixture
```

For the public-demo cold start, supply process-local `CARBENTRA_PUBLIC_DEMO_ID`,
`CARBENTRA_IMAGE_TAG=local`, `CARBENTRA_DEMO_HOST=localhost`,
`CARBENTRA_SECRETS_DIR` and `CARBENTRA_DEMO_TLS_DIR` pointing to that fixture,
and an unused `CARBENTRA_DEMO_NETWORK_PREFIX`. This run used `172.30.89` and
project `carbentra-fix-public`. An external Compose overlay replaced gateway ports
with loopback `18082:8080` / `18444:8443` and API `CARBENTRA_ALLOWED_ORIGINS` with
`["https://localhost:18444"]`. Run the standalone `compose.public-demo.yaml` plus
that overlay with `up -d --build --wait --wait-timeout 600`, then:

```powershell
uv run --locked --all-groups python tests/deployment/public_demo_smoke.py --base-url https://localhost:18444 --fixture-directory <task-output>/public-fixture --output <task-output>/public-https.json --disposable-fixture
```

The production `tools/public-demo-secrets.py` still requires POSIX permission
enforcement and deliberately refuses Windows. The local QA generator above does
not establish a production Windows secret-provisioning path. No certificate was
installed into the host trust store and no TLS-verification bypass was used.

## Evidence lifecycle and limits

Transient outputs used `D:\Temp\codex\carbentra-fix-20261001\platform`:
`edge-release.json`, `edge-linux.json`, `mqtt-integration.json`,
`backend-integration.json`, `verify-local-final.log`, `production/`,
`public-https-final.json`, `public-before.json`, `public-after.json`,
`browser/summary.json` and `browser-persistence.json`. Logs, screenshots and expiring
test secrets are task-local disposable outputs, not committed production assets.
The durable cross-repository proof copies are in smart-plug's `firmware/evidence`.

Projects `carbentra-fix-tests`, `carbentra-fix-production`, `carbentra-fix-public`
and `carbentra-fix-browser` were stopped and their disposable volumes/networks
removed; one-shot Linux checks used `--rm`. Final inventory had **no containers,
no volumes and only Docker's `bridge`, `host`, `none` networks**. No preview was
left running. Four reusable local image tags remained as build artifacts:
`carbentra-campus-api:local`, `carbentra-campus-web:local`,
`carbentra-campus-edge:local`, `carbentra-campus-edge-tests:local`.
Docker-managed build/base-image caches were not globally pruned.

These checks do **not** establish physical sensor accuracy, relay actuation or mains
safety, measured savings, public DNS/reachability, production certificate handling,
concurrent-load/retention capacity, or a public-demo HTTPS browser journey. Browser
checks used the development HTTP stack; public-demo HTTPS was verified by the
separate trusted-CA client. Simulated devices and unverified execution remained
explicit throughout. No global tools, user/machine environment, firewall rules or
trust-store configuration were changed for these platform checks.
