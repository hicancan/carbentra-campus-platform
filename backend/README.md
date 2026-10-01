# CARBENTRA Campus API

An independent full-campus implementation. Authentic spatial references are imported from pinned njupt-map/njupt-search assets. All seeded instrumentation, measurements, faults, factors and tariffs are explicitly SIMULATED. The API never reports simulated evidence as measured campus performance. Accounting summaries run an interval-specific SQL projection with a bounded five-million-source-sample workload; oversized requests fail explicitly without partial totals.

## Run locally

Python 3.12 is required. Start from the repository root with PowerShell 7:

```powershell
uv venv --python 3.12 .venv
uv sync --locked --all-groups
$env:CARBENTRA_ENV='development'
$env:CARBENTRA_DATABASE_URL='sqlite:///./campus-dev.db'
$env:CARBENTRA_DEV_AUTH='true'
$env:CARBENTRA_SEED_DEMO='true'
$env:CARBENTRA_SIMULATION_ENABLED='true'
Set-Location backend
uv run --locked python -m app.migrate
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Development fixtures: usernames `admin`, `operator`, `analyst`, `viewer`; password `development-only`. These fixtures have no stored production password and are rejected when development auth is disabled. Bind the development deployment to loopback. A separate persistent SQLite file is development/test only; production requires PostgreSQL. Docker/PostGIS and operational procedures are owned by the root Compose configuration.

`/health/live`, `/health/ready`, `/api/docs`, `/api/openapi.json`; protected API under `/api/v1`. Use HttpOnly cookie sessions, `credentials: include`, and the returned `X-CSRF-Token` on mutations. CORS origins and hosts are explicit operator configuration, never wildcard. Direct object access, queries, mutations and exports are filtered by the user's current campus scope.

## Process roles

- API: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Explicit migrations: `python -m app.migrate`
- Control/simulation worker: `python -m app.worker`
- Required independent analysis worker for projections/forecasts: `python -m app.worker --role analysis`
- Independent workers when desired: `python -m app.worker --role control` and `python -m app.worker --role simulation`
- Lightweight container health: `python -m app.worker_health`; simulation health: `python -m app.worker_health --role simulation`
- Analysis health: `python -m app.worker_health --role analysis` (180-second analysis heartbeat, independent of the 10-second control threshold)
- DB-backed diagnostic: `python -m app.worker --health` (imports the application stack)

Set `CARBENTRA_WORKER_ENABLED=false` in API processes when running separate workers. The control/simulation worker uses independent loops; the analysis role must run in a separate process. It does not execute control actions or share a control cadence. Control runs at 250 ms; synthetic ingestion commits in bounded 25-device batches and yields to outstanding commands. PostgreSQL transaction advisory locks serialize each role across replicas. Physical feedback deadlines are not extended to hide load-induced latency.

## Configuration and first production administrator

Configuration is in `app/config.py`, using the `CARBENTRA_` prefix. Secrets are supplied by the operator; none are generated or committed for production.

Production requires `ENV=production`, a PostgreSQL URL, `COOKIE_SECURE=true`, `AUTO_MIGRATE=false`, explicit HTTPS `ALLOWED_ORIGINS` and explicit `TRUSTED_HOSTS`. Development authentication and demo seeding are rejected. Run migrations separately before starting the API. On first bootstrap, provide `ADMIN_USERNAME` and `ADMIN_PASSWORD` (at least 16 characters) through the deployment's secret-file mechanism. The password is salted and PBKDF2-hashed; remove the bootstrap secret after an enabled non-fixture administrator exists. Subsequent startups do not require the original password and do not silently rotate it. Startup fails if production has no enabled non-fixture global administrator.

Opaque session tokens are stored only as SHA-256 digests, expire within 24 hours, and are revoked on logout, role/scope/enablement changes and password reset. Login failure throttles are persisted. Authentication and configuration errors never echo supplied secrets. There is no JWT signing key or default production credential.

## Domain boundaries

- `registry.py`: source identities, electrical circuits, dated immutable device placement
- `telemetry.py`: strict normalized ingestion, raw wire retention, durable identity deduplication and quality gates
- `packages/iot-contract`: installed shared application contract and Plug wire validator
- `accounting.py`, `energy_sql.py`, `pricing.py`: same-boot Wh differences, counter/time/quality/binding exclusions, interval-specific meter antichains, versioned factors and timezone-aware daily tariffs
- `spatial.py`, `import_spatial.py`: verified reference-only registry bootstrap and safe additive metadata reconciliation
- `responses.py`: runtime-validated public DTOs, exported as OpenAPI for generated TypeScript contracts
- `control.py`, `adapter.py`, `simulation.py`: durable command ledger, delivery boundary, independent output/observation state and verification
- `scoping.py`, `security.py`: role and current campus-resource authorization
- `forecasting.py`: quality-gated hourly cohort, transparent ridge challenger versus seasonal-naive baseline, paired temporal holdout; no data writes
- `scheduling.py`: planned events and maintenance interlock. Planned occupancy is never measured occupancy and absence of a class never authorizes shedding
- `invariants.py`: database-enforced append-only audit history

Spatial and electrical hierarchies are separate. Rebinding closes an old placement, creates a new dated one, and resets control authorization. Historical measurements retain their original placement. Existing meter boundaries cannot be silently rewritten. Source IDs, map confidence, imported provenance, geometry and coordinate assumptions remain visible.

## Command transport and physical release boundary

The normal development adapter is IN_PROCESS and SIMULATED. It persists requested and actual simulated output separately, emits a fresh command-correlated telemetry observation, and verifies the canonical acknowledgement against that evidence. Its building meter is the modeled uninstrumented base plus the modeled child loads, so a simulated state change changes the simulated aggregate measurement too. This does not establish real savings.

The authenticated edge transport is implemented: command lease → MQTT delivery receipt → raw canonical ACK → correlated observed result. Set a simulated device's dispatch mode to VIRTUAL to exercise this path using software MQTT devices. The edge and API require operator-supplied adapter identity and an explicit device allowlist. `published` means broker delivery acknowledgement only. A lost lease or uncertain delivery is not blindly replayed. Wrong sequence/epoch/device, stale or mismatched observation and expired commands cannot verify.

Real dispatch is default-disabled. It requires independent operator configuration (`PHYSICAL_DISPATCH_ENABLED` plus an explicit release ID allowlist) and a matching, commissioned device with a PHYSICAL dispatch mode and release record. Ordinary registry/patch APIs do not provide a physical-release shortcut. The operator-attested commissioning API can prepare such release records when the independent deployment gate is explicitly provisioned. The delivered demo does not create any real release record, connect a real broker, certify mains hardware, commission a physical installation or authorize actual actuation. Actual physical release and device safety qualification remain external, uncompleted gates.

## Tests and dependency locks

The root `pyproject.toml` owns the workspace, testing, Edge and optional asset
validation groups. Backend runtime dependencies remain in `backend/pyproject.toml`.
One cross-platform `uv.lock` locks all groups; Windows/Linux-specific packages use
platform markers. Runtime Docker images install only their required groups.

```powershell
uv sync --locked --all-groups
uv run --locked pytest backend/tests tests/acceptance
uv run --locked python packages/iot-contract/tools/check_contract.py
pwsh -File tools/verify-local.ps1 -OutputDirectory D:/Temp/carbentra-check
```

Review protocol changes in `packages/iot-contract` and the corresponding firmware.
There is no backend-local validator shim or separately editable schema copy.

## Data semantics and known limits

- Unknown is null, never invented zero, free occupancy, safe-to-touch, or verified success
- Same identity `(device, boot epoch, canonical sequence)` with the same content is a durable duplicate; different content is a conflict. Batches roll back atomically on a rejected sample
- Reception, trusted observation time, measurement quality and accounting eligibility are distinct. Unknown firmware time is retained using reception time with `TIME_UNCERTAIN`, excluded from accounting
- Accounting sums complete eligible intervals only. Partial boundaries, gaps, resets, binding changes and quality failures reduce coverage. It never sums cumulative Wh counters or parent+child measurements
- Carbon is location-based modeled emissions, not a reduction claim. Demo factor 0.55 and tariff 0.82 CNY/kWh are explicitly synthetic, non-official assumptions
- Versioned flat and bounded daily time-of-use tariffs are implemented with an IANA timezone, explicit base rate and up to 24 non-overlapping override bands. Strict mode withholds a total when cumulative counters cross unresolved rate boundaries. Explicit proportional_estimate mode allocates by elapsed UTC time, conserves energy and labels the affected intervals estimated. Ambiguous/nonexistent DST switch times abstain. Demand/capacity/fixed fees, utility settlement and certified revenue metering are not claimed
- Forecast selection uses a fixed eligible cohort, explicit coverage and a paired temporal holdout. On the synthetic fixture the seasonal baseline can legitimately beat the ridge challenger. No claim of trained real-campus AI is made
- HTTP forecast reads never scan the raw training history or fit a model. They read a scoped persisted evaluation or queue one; queued/running/ready/failed/stale are explicit. The independent analysis worker rebuilds closed UTC-hour revisions from at most one device/day per batch and then trains from the bounded 21-day hourly history. Revision readers cap 100,000 rows and abstain rather than truncate. Raw-SQL reading remains an explicit test/rebuild oracle, not an HTTP fallback. Warm and rebuild performance are measured separately
- Telemetry is durably stored, but automatic production retention/purge is not enabled. Capacity, disaster-recovery and PostgreSQL tuning must be set for the deployment's actual sampling rate
- Reference geometry is not surveyed indoor registration, and room plans do not prove current occupancy

See repository `docs/API_CONTRACT.md`, the generated OpenAPI schema and deployment operations documentation for exact HTTP and handoff details.

### Commissioning workflow clarification

The operator-attested evidence and release lifecycle is now implemented at `/devices/{id}/commissioning` and its release/revoke actions. Recording evidence alone enables nothing. Release needs the separately configured deployment gate and exact release allowlist, reviewed evidence references, the unchanged dated binding and fresh canonical authenticated hardware-revision observation. The edge has an independent physical gate and per-device release allowlist. All supplied runtime defaults remain OFF/empty; the only positive physical-code-path test uses an inert fake device in a disposable local database and performs no MQTT publication. This is software-path proof, not hardware qualification.

### Trusted proxy and login throttling

`CARBENTRA_TRUSTED_PROXY_CIDRS` defaults to an empty JSON list. Forwarded client-address headers are ignored unless the immediate peer is explicitly trusted; the chain is read from the trusted end. Login limits are per account+client (8 failed attempts/5minutes), per account across clients (50/15minutes), and a higher address-wide abuse ceiling (200/minute). Eight mistakes by one user behind a shared campus proxy do not lock every other account.

## Reference-only production bootstrap

After migrations, import the bundled verified reference registry independently of all demo data:

```sh
python -m app.import_spatial --check
python -m app.import_spatial --apply --expected-version <reviewed-manifest-version>
```

The CLI uses the normal operator-provided database configuration. It creates no users, devices, circuits, telemetry or tariffs. Check mode is read-only. Both modes verify the manifest content hash and the exact seed SHA-256/byte count, source version and hierarchy. Apply is transactional: stable identities may be added and descriptive metadata refreshed; removals, source-identity changes and parent changes are reported and refused rather than rewriting historical device bindings. Other package artifacts retain their manifest hashes and are verified by the spatial package build/consumer tests; this registry command verifies the manifest and seed, not every display asset. `/system/status.spatial` distinguishes `bundled`, `imported`, and `synchronized`; a new image alone does not claim the persisted registry was updated.

## Public response contracts

Auth, device/detail, telemetry, command, energy/carbon/cost, forecast and control-eligibility routes validate `app/responses.py` at runtime. Extra internal fields fail closed without echoing their values into HTTP or logs. `sample_seq` and command `sequence` are exact canonical uint64 decimal strings. Generated OpenAPI is reproducible:

```sh
python tools/export_openapi.py
python tools/export_openapi.py --check
```

The frontend derives response types from `packages/contracts/openapi.json`; generated code is not a second editable domain schema. Unknown quantities remain nullable, and conditional forecast fields remain optional.

## Optional product reference

`python tools/import_product_asset.py /path/to/hardware-repository --family PLUG|SWITCH|PRESENCE` is the single publisher for product references in `packages/product/dist`. The catalog selects an explicitly requested family; no unspecified device falls back to Plug. Each family has an authenticated, hash-checked manifest/model/hero route. Plug retains its validated display quantization, while Switch and Sense B currently use byte-identical small GLBs. Models load only after an explicit viewer action and are not installation, actuation, calibration or safety evidence. See `packages/product/README.md` for exact commands and source qualification.

## Forecast jobs, revision evidence and recovery

`ForecastHourRevision` is append-only derived evidence, grouped by immutable placement/source boundary. Complete 3600-second coverage is required; invalidated hours get explicit tombstone revisions. Each revision separates facts’ `available_at` from computation time, retaining older revisions for receipt-aware historical backtests. Raw telemetry remains authoritative and unchanged.

Normal ingest only coalesces bounded dirty-hour work. Short leases release dirty/Device locks before reconstruction; a changed watermark retains new work after publication. State revision counters update under a short row lock. An existing database whose first fresh ingest creates a projection state still bootstraps its older history when `history_initialized=false`. Explicit operator recovery is available without deleting observations:

```sh
python -m app.rebuild_forecasts --queue [--device-id ID] [--start UTC_ISO] [--end UTC_ISO]
python -m app.worker --role analysis
```

GET `/forecasts` returns the existing DTO plus `evaluation`. Cache keys include current authorized campus scope, request scope/horizon and model version; freshness tracks closed-hour revisions, binding/source identity, calendar and coarse availability, not every open-hour sample. A stale result keeps its original generated/training times. POST `/forecasts/refresh` is CSRF-protected and retries failed derived work. Jobs are bounded globally (default 128 pending/4096 cache keys) and per requester (16 pending), use 180-second leases and at most 3 automatic attempts, and recheck current authorization before compute/publication. No job dispatches a device command.

A source-bound PostgreSQL replay benchmark with 3,133,576 observations and 136 meters measured 156.067 seconds for the bounded cold rebuild, 1.63–1.76 seconds for populated projected analysis and 31–37 ms for populated cached HTTP reads. Initial queue admission was 70 ms. These are separate synthetic workload measurements; they do not predict hardware or deployment-specific throughput.

## Classroom state, canonical IoT ingestion and bounded operations

The classroom surface covers every imported `Space` in the authenticated campus
scope, including uninstrumented reference units. A reference room is not a verified
installation. `GET /api/v1/classrooms` supports up to 2,000 rows per page and reports
`meta.total`; the timestamp, timeline and distribution views all use the same
immutable channel observation history.

- `/classrooms?at=...`: half-open event-time snapshots; no latest-state backfill
- `/classrooms/{room_id}/timeline?start=...&end=...`: state intervals, explicit
  unknown durations and genuine command/observation events, at most seven days
- `/classrooms/distribution?start=...&end=...&group_by=building`: full-scope
  room-seconds and source modes; power is explicitly a partial known-room sum
- `/classrooms/{room_id}/mode`: audited automatic/manual/maintenance/fault history;
  manual override requires 60–86,400 seconds and resumes an underlying automatic
  mode only if one was explicitly authorized before the hold
- `/classrooms/{room_id}/policies`: at most 20 targets, at most seven-day windows,
  persisted SHADOW or SIMULATED evaluations; dispatch requires a review no older
  than 30 seconds and rechecks vacancy, freshness, binding, dwell, policy revision,
  actor authorization and room mode. Queued commands lose authority when presence
  returns or a manual override is set. Only independently modeled SIMULATED output
  observations may verify a simulated outcome; modeled reduction is not savings
- `/classrooms/anomalies`: persisted deduplicated open/acknowledged/resolved
  episodes. Rules combine persistence with measured channel evidence. Conditional
  high-load rules require at least eight samples over three historical dates,
  matching room, observed occupancy, local hour and weekday/weekend class. Training
  is strictly 1–28 days before the target; insufficient evidence does not invent a
  baseline. No weather model or physical electrical safety claim is made

New devices use `/api/v1/ingest/events` with the shared package in
`packages/iot-contract`; authenticated adapters have an explicit device allowlist.
The backend separately records its receipt time. PLUG raw wire payloads normalize
into the existing unique Telemetry identity and accounting ledger. The old
`/ingest/firmware` route is a protocol adapter into that same ledger, not a second
source of energy. `/ingest/channel-acks` durably stores channel-specific Switch
acknowledgements but `commanded` never means load feedback or physical verification.
The shared Python package must accompany the backend directory (the Docker build
copies both); backend `wire_contract` is an import compatibility shim only.

PIR silence is never vacancy. Any fresh occupied sensing point establishes occupied;
vacancy requires all declared radar/occupancy sensing points to have fresh valid
vacant evidence. Receipt-only, stale, invalid or missing observations remain unknown.
Raw illuminance counts are not lux. CO₂/temperature schema extensibility does not
claim those sensors exist on current hardware. SIMULATED profiles explicitly label
synthetic feedback that real Switch hardware does not provide.

### Migrate, seed and operate

1. Back up PostgreSQL using the repository operations procedure, then run
   `python -m app.migrate` before starting the upgraded API. Migration
   `273cb450c2f7` adds eight relational tables and append-only evidence triggers.
2. Development `CARBENTRA_SEED_DEMO=true` initializes idempotent all-mapped-room
   scenarios once; production never seeds automatically. Fixtures contain a sparse
   21-day same-hour baseline and a 24-hour 15-minute state window. Large gaps remain
   unknown. Initial fixture generation takes approximately 40–50 seconds locally.
3. Run the existing control, simulation and analysis worker roles. Anomaly analysis
   processes eight rooms per bounded transaction, separately from control.
   `CARBENTRA_CLASSROOM_SIMULATION_INTERVAL_SECONDS` defaults to 60 (30–900 allowed),
   independently of the older campus telemetry simulation cadence. All simulated
   local/remote/room actions remain labeled SIMULATED; actual hardware actuation
   remains closed behind existing commissioning/authorization gates.
4. Rollback is a coordinated application+database operation: stop writers, retain a
   backup, then `alembic downgrade ba682468c8c6` only when the classroom evidence can
   be discarded or restored from backup. Downgrade drops these new tables; it is not
   a reversible user-level delete operation. Do not run an old API against the new
   application while upgrading or downgrading schemas.

Direct fixture controls and policy dispatch share the existing Command ledger.
Schedules remain plans, never observations. Edge local rules require separately
provisioned bounded authority; this API does not fabricate offline command leases
or claim that cached cloud intent authorizes unattended real-hardware operation.

### Measurement authority and three-channel outcome semantics

The final all-room fixture is version 3. Building primary meters are generated from
one common model: building base load + original legacy modeled plugs + every new
room Plug + each three-gang Switch aggregate exactly once. The original and room
loads are descendants of that same electrical measurement boundary. Default
accounting selects the parent-meter antichain; explicitly selecting a parent and
its descendants is rejected. A missing branch observation does not turn the branch
into zero in the independent simulated parent meter: its explicit software output
model remains the modeled load. This is synthetic test evidence, not campus energy.

Switch aggregate events also project into the existing Telemetry ledger, using the
same device/boot/sequence uniqueness boundary. The current hardware has no cumulative
export result; export remains null, and partial import counters remain explicitly
uncertain (`EXPORT_UNAVAILABLE`, `ENERGY_UNCERTAIN`). They do not become fabricated
zero-export or billing-certified energy. Classroom power views use capability-level
observation quality; the Wh ledger conservatively excludes incomplete intervals.
No per-relay power is manufactured from the shared aggregate. A partial-gang policy
has an unknown watt reduction even when the aggregate threshold allows control.

Switch command acceptance ends in `acknowledged_unverified`, based on an exact
matching device ACK (device, boot, command, sequence, channel), never broker PUBACK.
It is neither independently verified nor counted as a failure. Plug commands retain
their independent-feedback path. Atomic manual holds are channel-specific and apply
to backend+edge automation only; they cannot override firmware-local protection or
local manual holds. Room takeover remains a separate explicit action.

Old prerelease demo fixtures are rejected rather than silently rewritten into the
new boundary model. Keep historical evidence/backup if needed and initialize a
fresh development database. Production data is never automatically reseeded.
Authenticated relative-time Sense proofs preserve `observed_at=null`; current
knowledge begins at backend receipt only after proof provenance, signed age,
upload-delay and clock-skew checks. `effective_at`, `time_basis` and bounded age are
exposed. Delayed uploads and unsigned advertisements remain unknown.

Anomaly settings are available through `GET/PATCH /classrooms/{id}/anomaly-rule`
and bounded atomic `PATCH /classrooms/anomaly-rules/batch`. Optimistic revisions,
reason and audit are required. Threshold, baseline multiplier/MAD factor,
persistence and clear hysteresis are configurable; they are engineering defaults,
not calibration facts. A configuration revision supersedes an active episode while
retaining its previous threshold/evidence. Unknown data cannot clear an episode.

Optional engineering assets require an explicit `family=PLUG|SWITCH|PRESENCE` on
`/assets/product/manifest`, `/model` and `/hero`. They use one fixed catalog,
authentication, same-origin URLs, containment and full SHA256 checks. Unsupported
families never fall back to an unrelated Plug model.
