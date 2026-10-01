# Unified CARBENTRA edge gateway

This is the sole active edge runtime. The prior hardware repository edge source
is retired to a provenance/handoff reference. Run `python edge/service.py`; this
entry point delegates to the multi-device runtime, not a second Plug service.
The gateway owns durable ingress/outbox, concrete MQTT/BLE/GATT adapters, cached
observations, bounded local policy and delivery. Campus identity, room binding,
energy accounting, authorization and dashboards remain in the backend.

## Supported, concrete paths

- Plug v2: exact `carbentra/v1/{device}/{hello,telemetry,ack}` topics and existing time/receipt/command wire; shared strict validator
- Switch firmware v1: exact `carbentra/switch/{device}/{state,ack,availability}` topics, three individually typed lighting channels, one aggregate meter, local input/manual priority, no fabricated independent feedback
- Sense v2 manufacturer diagnostics and authenticated GATT v1 via supported Bleak 3.0.2 / Linux BlueZ; no PIR or lux claim
- Explicit SIMULATED-only virtual Presence event topic and `virtual_bridge.py` for three families in multiple rooms

No universal driver, direct frontend MQTT, synthetic REAL fallback, automatic
enrollment, production key generation, pairing, or unbounded offline authority.

## Install and start

Install from the root cross-platform uv workspace. Direct Edge dependencies live
in `[dependency-groups].edge`; `uv.lock` supplies platform-specific transitive locks.

```powershell
uv venv --python 3.12 .venv
uv sync --locked --all-groups
uv run --locked --all-groups pytest edge/tests -r s
```

The operator supplies narrowly scoped `CARBENTRA_ADAPTER_TOKEN`. HTTPS is mandatory
except loopback tests; redirects, implicit environment proxies and token-bearing
alternate origins are refused. mTLS verifies broker hostname/CA. Enforce broker
ACLs per certificate identity and exact enrolled device topics; wildcard ACLs in
local integration tests are not production deployment guidance.

`examples/devices.virtual.json` contains six explicitly simulated endpoints across
two rooms. `examples/devices.example.json` documents real enrollment shape without
credentials. The prior concrete Plug-only `devices`/`virtual_devices` config can be
read for migration; new installations use typed `enrollments`.

BLE radio input is **off** unless `--enable-ble` is supplied. Linux needs an actual
adapter, BlueZ and appropriately authorized system D-Bus access; these are not
silently requested, created or bypassed. `--ble-adapter hci0` selects an adapter.
Authenticated Sense enrollment declares `protocol: presence-gatt-v1` and a path
to an already provisioned private 32-byte key file. Missing/unsafe files fail
startup rather than silently downgrading. Bleak uses a fresh nonce write/read;
invalid, stale or missing proofs remain unavailable. Actual RF is not exercised
by the fake-client tests and software bridge.

The container image must copy `edge/` and `packages/iot-contract/` from this same
platform checkout. The shared package is installed with its schema data or kept
at `/app/packages/iot-contract` beside `/app/edge`. Do not mount hardware/edge as
another active source. Container D-Bus/radio access is a separate opt-in deployment
choice, not included in the default MQTT stack.

## Durability, replay and offline behavior

SQLite WAL + FULL synchronous stores immutable canonical events and HTTP outbox
in one transaction. Duplicate sample identities compare canonical content;
conflicts are rejected, never overwritten. HTTP receipts must match event ID,
device, boot and sequence and assert committed durability. HTTP 409 blocks the
retained outbox row for operator review. Retries preserve original evidence.

`current_snapshots` is an offline cache, not an authority to replay desired state.
Repeated advertisements do not refresh sample age; old sequence/retired boots do
not replace current state. Authentication highwater is independent of ads. Unsigned diagnostic IDs use an
`adv-` boot namespace, so spoofed ads cannot preempt signed sample tuples. For
authenticated GATT enrollment, ads stay local diagnostics and never overwrite the
backend signed-observation timeline.
Restart/reconnect re-subscribes and waits for fresh observations. It does not
resend the cached relay intent. Pending HTTP events reconcile by immutable IDs.

Receipt age and control freshness are separate. A REAL Plug control snapshot
requires authenticated device UTC, its consistent at-most-five-second uncertainty
interval, and fresh sample/measurement monotonic times. The oldest plausible
measurement time must fit the caller's age limit (ten seconds for transport, at
most five for local rules). A newly received 300-second-old buffered sample stays
durable and is forwarded as history, but cannot authorize a rule or dispatch.
Unknown/untrusted Plug time, wholly future observation intervals, reversed gateway
time, same-boot monotonic/UTC rollback, and REPLAYED sources fail closed.

`observation_clocks` persists same-boot monotonic highwater and conservative receipt
bounds. Higher sequence numbers with stalled uptime cannot continually refresh a
snapshot. The relative bound allows a deliberately generous one-percent slow-clock
drift and is tightened by subsequent receipts; it survives restart and seeds from
the original snapshot when upgrading. New boot IDs reset only that boot's timing
bounds; a retired boot still cannot replace the current snapshot.

Switch does not provide authenticated UTC: its live, non-retained state publication,
receipt age and same-boot monotonic progress remain the supported timing evidence.
These cannot prove an unknown first publication's absolute generation time. Its
device-side boot-relative expiry remains mandatory; the gateway never invents an
`observed_at`. SIMULATED unknown-clock fixtures remain explicitly simulated, while
any supplied authenticated Plug timestamps are subject to the same age checks.
Snapshot `age_seconds`/`arrival_age_seconds` preserve receipt age for signed sensor
age calculations; `observation_age_seconds` is null without usable device UTC,
not a fabricated zero. `control_age_seconds` combines available arrival,
relative-clock and observation bounds; `freshness_reason` explains refusal.
None of these checks rewrites immutable event payloads.

The durable command inbox is committed before publish. Crash or ambiguous PUBACK
becomes `mqtt_delivery_uncertain`, never a blind resend. Expiry and lease are
checked before inbox admission and again immediately before publish. Broker
PUBACK is transport delivery, not execution. Leases themselves are persisted
before driver admission; the separate delivery receipt outbox retries lost HTTP
receipts even though the backend correctly never reissues an already-leased action.
A committed `sending` state is uncertain both before and after the network call;
restart does not guess which side of that boundary the crash happened on.
Firmware ACK and independent actual
feedback retain separate meanings. Switch `commanded` ACK reaches `acknowledged_unverified`, never `verified`.
A late transport receipt cannot roll a terminal device outcome backwards.

An explicit user `manual_hold_seconds` (60–86400) has `backend_edge` scope: the
backend and gateway persist it per channel before dispatch. It is not an extra
field in the strict firmware command and does not override device-local key holds.
Gateway restarts and lease retries do not extend the original hold deadline.

## Control remains independently gated

Commands default OFF. `--enable-virtual-commands` permits only explicitly enrolled
SIMULATED endpoints and matching cloud VIRTUAL leases. Physical dispatch additionally
requires exact `CARBENTRA_ENABLE_PHYSICAL_DISPATCH=true`, an operator-provided
`CARBENTRA_PHYSICAL_RELEASES_JSON` per-device release map, matching REAL command
release, fresh same-boot evidence, declared channel, bounded authority and the
firmware's separately commissioned/compiled gates. No physical gate was enabled
in development. Software release records are not electrical qualification.

One authenticated backend lease stream carries concrete Plug wire-v2 commands
and canonical Switch channel commands. `LeasedDispatcher` routes them by actual
protocol; `ChannelTransport` explicitly translates one Switch gang to its current
six-field boot-relative command wire, ordered by device-global numeric sequence. Presence is read-only. Unsupported targets
are rejected, never treated as generic relays.

`--rules file.json` installs a revisioned local cache. `--enable-local-rules`
additionally permits dispatch through the independent transport gates. Without a
lease, evaluation says `evaluated_not_authorized`. An operator lease identifies
one rule/target/channel, expires within one hour, supplies an explicit offline
expiry and a reserved command sequence range. It is not automatically minted or
renewed by the cloud. Operator reservations must be coordinated with the backend
sequence allocator before any real use; the deployment runtime conservatively
uses the offline window even while MQTT is connected. Revisions cannot roll back
and a lease ID cannot be reused with changed authority.

Priority: fault → maintenance/protected → manual hold → lease/expiry → fresh
sensor condition. Only fresh authenticated continuous radar or explicit simulation
can drive rules. Vacancy needs at least 60 seconds of uninterrupted fresh false
evidence. Missing samples, unauthenticated ads, unknown radar, old ages, mixed
sources or stale cache never mean vacancy. Optional light threshold is explicitly
raw ADC counts. No arbitrary scripts, model decisions or cloud-setting overrides
run at the gateway. A device-local key hold takes priority over remote automation.

## Software verification

```
python -m pytest edge/tests -q
uv run --locked --all-groups python edge/tools/run_checks.py --release --output /path/to/private-checks/edge.json
python edge/tools/status.py --database /durable/edge.sqlite3
python edge/tools/check_mqtt_multidevice.py --mosquitto /path/to/mosquitto
```

Release checks require prebuilt actual firmware host encoders/verifiers via
`CARBENTRA_STARTUP_TEST_BINARY`, `CARBENTRA_TIME_TEST_BINARY`,
`CARBENTRA_CERT_TEST_BINARY`, and `CARBENTRA_SWITCH_COMMAND_TEST_BINARY`; missing
compiled gates are a hard release failure. The last binary links
`tests/c/switch_command_decoder.c` with the actual Switch `core/switch_core.c`,
`main/command_json.c`, and its approved cJSON source. It takes one JSON argument
and returns 0 for accepted, 1 for rejected, 2 for invalid harness invocation. The
cross-language test proves canonical/transport/C agreement at 48/49-character
Switch command IDs, including rejection before any publisher call.
In ptrace-managed environments the existing firmware harness uses
`ASAN_OPTIONS=detect_leaks=0`; address/undefined sanitizers remain enabled, but leak
checking is not claimed. The requested output JSON records source hashes, platform exclusions, dependency-lock checks and exact outcome.

`check_mqtt_multidevice.py` starts a real local Mosquitto with ephemeral mTLS certs,
the actual edge runtime, six virtual devices and a durable HTTP **contract sink**.
It checks all three families, virtual command/ACK, offline buffering, gateway
restart, outbox reconciliation and no command replay. This is not the actual
campus backend or actual RF. `mqtt-integration.json` records that exact scope.

To start the virtual endpoint against an operator-supplied test broker:

```
python edge/virtual_bridge.py --rooms a101,a102 --broker TEST_BROKER \
  --ca /test/ca.pem --certificate /test/virtual.pem --key /test/virtual.key
```

`--scenario manual-hold` exercises physical-key semantics in simulation;
`--scenario sensor-outage` stops virtual sensor delivery so age becomes stale.
No simulated test demonstrates relay qualification, hardware calibration, measured
savings, electrical safety or actual occupancy accuracy.

`tools/check_backend_multidevice.py` additionally runs the **actual FastAPI backend**
with isolated SIMULATED registry data, real HTTP authentication/CSRF/commands,
actual edge, and real Mosquitto mTLS. It addresses all three Switch gangs, checks
independent ACK correlation without independent feedback, rejects missing targets,
checks aggregate power is not duplicated, and injects a lost first delivery receipt
to prove late receipt recovery cannot regress terminal `acknowledged_unverified`.
Its current-source result is `backend-integration.json`; SQLite here is explicitly
a development fixture, not the production PostgreSQL verification.

For reproducible test dependencies, use root `uv sync --locked --all-groups`.
All proof runners fingerprint relevant sources before and after execution and fail
if they changed during the run. Rebuild/rerun after source updates; historical
evidence alone is not proof of a newer checkout.

## One-time upgrade of a prior Edge database

Stop the old gateway first and preserve its entire `/data` directory, including any
SQLite WAL/SHM files, or take an SQLite online backup. Keep the unchanged explicit
device enrollment and source modes. The new runtime runs version
`20261001_legacy_outbox_to_iot_v1` before opening any transport.

Pending old `telemetry` outbox rows are converted through the concrete Plug wire
adapter into canonical events in one SQLite transaction. Original raw tuple,
original receipt time and retry/block flags are preserved. The original `telemetry`
receipt table is not modified; original outbox rows are archived. Already delivered
rows retain their delivered marker in the archive and are never reopened. ACK rows
and command inbox history stay intact. A retransmitted old sample cannot become
fresh merely because the process upgraded. A database trigger prevents a retired
old application writer from repopulating its obsolete outbox kind.

Missing source enrollment, original receipt time or consistent raw evidence causes
quarantine with a reason. It does not invent migration-time measurements or discard
records. Only an explicit operator retry after fixing the issue can resolve it:

```
python edge/tools/migrate_legacy.py --database /durable/edge.sqlite3 \
  --devices /operator/enrollments.json --retry-quarantine
```

The active forwarder has no legacy telemetry HTTP branch. All migrated pending
telemetry uses `/api/v1/ingest/events`. The backend's wire compatibility API is not
an alternate deployment route for this gateway. `tools/status.py` reports migration
state and unresolved quarantine counts without printing payloads.

`tools/check_legacy_migration.py` generates an old-format database by running the
actual historical Git Edge implementation in a temporary fixture, then validates
current migration. `migration-integration.json` records that proof.
`guest-row-migration.json` additionally records verification with an actual exported
synthetic guest row and schema; its pending-row variant is explicitly fault-injected
on a copy, not claimed as originally pending.
