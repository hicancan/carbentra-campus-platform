# Backend implementation and evidence boundaries

This file describes the independent platform implementation, not an audit of the unavailable original software repository. Physical hardware qualification, installation and deployment remain separate gates.

## Implemented

- Full-campus registry imports 136 pinned building identities, 3 campuses, 41 source floors and 603 source space units. An explicit reference-only check/apply CLI works independently of demo seeding, verifies manifest/seed integrity, reports safe metadata changes and refuses destructive identity reconciliation. Bundled and imported versions are distinct. Spatial authoring remains in the map/search producers
- Explicit synthetic scenario data: 680 devices, separated electrical hierarchy, 14 days of building-meter history and 24 hours of plug history. Every operational sample and assumed factor/tariff is labeled SIMULATED
- Runtime-validated public response DTOs and reproducible OpenAPI for generated TypeScript, with explicit decimal-string uint64 sequences and no internal storage fields
- Cookie sessions, CSRF, bounded strict JSON, explicit CORS/hosts, account/client throttling, optional explicitly trusted proxies, salted password hashes, session revocation, admin lifecycle and protection against removing the last global administrator
- Current campus scope applied server-side to resource reads, mutations, historical samples, commands, reports and exports. Existing SSE streams revalidate the session and current scope on every poll
- Durable telemetry identity deduplication, conflict rejection, transactional receipts, raw v2 preservation, trusted-time/quality gates, dated placement and source provenance. Historical faults do not create false current-location alarms
- Shared canonical hardware wire validation, imported as a generated hash-pinned artifact from a clean producer commit. The platform does not maintain a second editable wire parser
- Durable command sequences stored without signed-int32/JavaScript precision truncation, idempotent requests, expiry, role/scope/capability/critical-load/dwell/freshness/binding interlocks and append-only transition audit
- Independent simulated output state, fresh correlated telemetry and ACK verification. Aggregate simulated building meters include child loads; changing a simulated plug changes the modeled meter boundary too
- Authenticated command leases, durable delivery receipts, MQTT publish acknowledgement distinct from observed result, raw ACK retention, reordered ACK/delivery handling and no blind replay of uncertain delivery
- Future REAL transport code path behind separate platform and edge deployment gates, per-device operator-attested commissioning/release records, current binding, calibration/safety evidence references and runtime guards. All supplied defaults remain OFF; no real release or actuation is performed
- Alarm acknowledgement, resolution and notes with history; global immutable factor/tariff versions; timezone-aware daily tariff bands with strict or explicitly estimated boundary allocation; snapshots and JSON/CSV export with spreadsheet-formula neutralization
- Interval-specific meter antichains, same-boot Wh differences, quality/time/reset/binding exclusions, explicit coverage and unknowns. SQL summaries/breakdowns/cost/carbon avoid loading all raw observations into Python
- Planned schedules, revisions, import and cancellation. Maintenance is a conservative control interlock; planned occupancy and an absent class never become observed vacancy or sole control permission
- Transparent trained ridge challenger versus seasonal-naive baseline, chronological paired holdouts, a fixed eligible cohort, explicit freshness/coverage and empirical bounds. Append-only closed-hour evidence revisions preserve receipt-aware backtesting and late invalidations. HTTP reads a scoped persisted evaluation with explicit queued/running/ready/failed/stale state; independent analysis work performs backfill and fitting. The fixture legitimately chooses the better seasonal baseline
- Independent control and synthetic ingestion worker loops, bounded simulation transactions, role-specific PostgreSQL locks, durable worker health plus a stdlib-only process-identity/heartbeat probe, explicit Alembic migrations, PostgreSQL bigint identities/sequences and database-enforced append-only audit history

## Verified evidence, with scope

- Focused backend and independently authored acceptance tests exercise the invariants above. Test counts evolve as regressions are added; use the final repository verification report and exact command logs rather than an old count here
- Native PostgreSQL acceptance has verified concurrent same/conflicting telemetry, concurrent idempotent commands, uint64 sequences, actual API/worker restarts, session/report persistence, pg_dump/restore and a software MQTT/mTLS loop
- A native load test verified 30/30 simulated commands while 13 forecasts, 12 overview queries and 24 ingestion batches (600 samples) ran concurrently: observed command p95 was 1.364 seconds, max 1.372 seconds. These numbers describe that recorded test environment and source snapshot; they are not a production SLA or physical timing proof
- Later SQL accounting and bigint migration changes must be included in the final repeated PostgreSQL/Docker verification. Do not reuse an earlier pass as evidence for untested later code
- On an isolated PostgreSQL fixture containing 3,133,576 REPLAYED observations from 136 meters, the real bounded rebuild queue produced 26,112 hour revisions in 156.067 seconds across 1,088 batches. Direct projected analysis took 1.629–1.761 seconds. An immutable owner snapshot (`f49d152c…56aabb26`) then returned the initial queued HTTP response in 70.2 ms, completed background evaluation in 1.756 seconds and served five populated cached reads in 31.3–36.7 ms. Request-time fitting was disabled in that test to prove GET did not train. All 90 focused forecasting tests also passed PostgreSQL. Cold rebuild, analysis and HTTP cache latency are separate measurements, not a production SLA
- Positive commissioning/PHYSICAL code-path tests use inert fake records in disposable databases and do not publish to a real broker. The firmware remains DEV_ACTUATION_DISABLED

## Explicitly not claimed / remaining deployment work

- No real campus telemetry, installed socket fleet, calibrated field energy, verified energy savings or attributable carbon reduction
- No mains manufacturing/safety qualification, operator commissioning of a real site, physical relay activation or production credential provisioning
- No automatic certification of uploaded/operator-referenced safety documents. Release records are operator attestations, bounded by independent deployment gates
- No trained real-campus model, measured occupancy, surveyed indoor registration or guaranteed model performance
- Flat and bounded daily time-of-use energy-charge estimates are implemented. Counter intervals crossing rates are unavailable in strict mode, or explicitly estimated by elapsed UTC time when requested. Ambiguous/nonexistent DST switch times abstain. Certified billing, demand/capacity/fixed fees and utility settlement remain outside this version
- Automatic destructive data retention is not enabled. Sampling-rate capacity, partitioning/retention, backup RPO/RTO and fleet-scale latency require the actual deployment's measurements and operating policy
- Raw SQL remains a bounded oracle: a 3.13M-row test was correct and memory-bounded but took ~62 seconds, so it is not used synchronously for HTTP forecasts. The separately measured projection/cache results below describe the tested synthetic replay workload; deployment-specific throughput and recovery targets still need field sizing
- The optional 3D plug display asset is a lazy-loaded product reference, never proof of an individual device's placement or electrical safety

## Optional display optimization

The product importer has promoted a 22,318,016-byte display from the 30,337,768-byte pinned source, preserving 227 named parts/materials and 666,556 triangles. Independent numerical and hash-bound Khronos reports are retained. This 26.4% byte reduction is a measured artifact property; it is not a measured browser frame-rate, installed-device mapping or physical qualification claim.
