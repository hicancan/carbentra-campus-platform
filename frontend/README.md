# 碳迹未来 · Campus frontend

React + TypeScript + Vite client for the authenticated CARBENTRA API. No fixture adapter or dashboard fallback is used in the shipped application.

## Run

Start the backend at `127.0.0.1:8000`, then:

```sh
npm ci --cache /tmp/carbentra-npm-cache
npm run dev
```

The development server binds to `127.0.0.1:5173` by default. Vite proxies `/api`, `/health`, and authenticated `/assets/spatial` to the backend. Production uses the nginx container from the repository's Compose setup, including SPA fallback for deep links. See the root operations guide for credentials and secure environment configuration. There is no embedded account password or production bootstrap secret in the client.

```sh
npm run api:check
npm run typecheck
npm test
npm run build
npm audit
```

`dist/` is the production output. Spatial models are loaded from the backend mount, not bundled in the main JavaScript. Three.js and the 3D viewer are lazy-loaded only when 3D is requested.

## Workspaces

- **运行总览**: API-computed campus energy, current load, carbon, cost, quality, alarms and building ranking
- **校园空间**: 136 imported registry buildings; 129 authenticated real-reference footprints / LOD1 meshes; source-linked floor and room navigation; independent indoor diagrams where published
- **空间计划与检修**: planned teaching/events/holidays/maintenance, bounded JSON import preview, edits and cancellation history. Planned attendance never substitutes for observed occupancy
- **能耗分析**: scoped accounting periods, meter hierarchy and balance, coverage / exclusion evidence
- **碳与成本**: versioned factors and tariffs, IANA-timezone daily price bands, strict boundary accounting or explicitly selected proportional energy-charge estimates
- **设备与边缘**: paginated registry, telemetry evidence, space/circuit binding, simulated commissioning and transport settings; explicit lazy product-reference model with size and SHA-256 verification
- **配电拓扑**: electrical hierarchy independent of physical location; create/edit with server-side historical-boundary and cycle checks
- **告警工单**: acknowledge, record, resolve, with persisted timeline and request failures surfaced
- **预测与策略**: model/baseline holdout comparison, eligible cohort, freshness, uncertainty; shadow evaluation, approval and separately acknowledged simulated dispatch
- **命令追踪**: request, delivery, acknowledgement and verification evidence; rejected/failed/timeout states remain distinct
- **报表与审计**: durable report snapshots, authenticated CSV/JSON export, read-only action records
- **系统管理**: operational health, safe timing thresholds, scoped accounts, roles and session-revoking password updates

## Boundary contracts

`src/lib/api.ts` is the only API transport: same-origin cookie credentials, CSRF header, explicit request errors, cancellation and session-expiry handling. All lists and mutations use the backend `data/meta` envelope. Paged lists retain backend totals. A successful submit means only what the returned persisted state says; errors never dismiss a form as success.

`src/lib/hooks.ts` owns polling and SSE. Event invalidation is domain-scoped; telemetry bursts do not reload static geometry or retrain the forecasting model. Polling remains functional when SSE disconnects. SSE invalidation, timed polling and focus refresh coalesce with an in-flight read instead of repeatedly aborting slow accounting requests. Request cancellation prevents older navigation responses from replacing newer views.

`src/lib/generated-api.ts` is reproducibly generated from the pinned `packages/contracts/openapi.json` using `openapi-typescript`. Core auth, device, telemetry, command, energy, carbon, cost, forecast and control-eligibility DTOs are aliases of these generated schemas, including nullable values and decimal-string uint64 counters. Run `npm run api:generate` after a backend schema update; `npm run api:check` detects schema/type drift. Remaining unmodeled endpoints are explicitly typed in `src/lib/types.ts`. `src/lib/spatial.ts` models published spatial resources separately. Indoor geometry remains in normalized top-left coordinates; no metric transform or precise BIM claim is invented. The default campus viewer uses authentic source geometry, optional source road/green/water context and visible map attribution. Published exterior detail is fetched only by a separate single-building action, preserves source PBR and campus placement, and falls back to LOD1 on errors. Detail selection resolves verified ancestor asset IDs for multi-material meshes. Spatial URLs and query cache keys include manifest version, and product URLs include the display SHA, preventing stable-filename package upgrades from reusing stale bytes. Keyboard/list navigation works without WebGL. Product geometry is a design reference with no device-installation or physical qualification claim; the pinned model is fetched only after a separate explicit load action, never for every campus asset.

The client is a usability boundary, not an authorization authority. The backend rechecks RBAC, campus scopes, quality, safety interlocks and sequence/expiry semantics. The UI never commissions or releases real devices and never directly accesses MQTT or a database. Delivered physical deployment flags are OFF. A future single-device REAL action is offered only after server eligibility permits it, with an exact named-load/action/consequence confirmation and a second server safety check. Bulk strategy dispatch is SIMULATED-only. Source mode, unknown values, measurement units and quality remain visible. A REAL review freezes the named load, action and consequence; identity, release or profile-revision changes clear acknowledgement before submission.

Dates entered in period and schedule controls use the displayed browser timezone and are sent as UTC instants. Factor/tariff validity fields are explicitly UTC; daily tariff bands use their configured IANA timezone. Unknown coverage stays unknown rather than becoming zero.

Forecasts use persisted background evaluations. Queued/running/stale work polls every five seconds; ready or failed work returns to the normal interval. A failed evaluation requires an explicit retry action. Retained stale results keep their original result timestamp, and first-run null predictions are never displayed as zero.

## UI system

`src/styles.css` holds the restrained white/charcoal/teal design tokens, light/dark themes, responsive breakpoints and reduced-motion behavior. `src/components/ui.tsx` owns shared cards, tables, badges, dialogs, fields and visible loading/error/empty states. Dialogs trap focus and restore the prior focus; ESC and Back/Forward preserve route state for spatial/device/command details.

## Verification status

Unit tests cover transport errors/CSRF, roles, source/quality control blocks, idempotent retries, signed chart coordinates and missing-value gaps, unknown occupancy, dialog dismissal, asset path checks and event invalidation. Cross-stack browser acceptance belongs to `tests/acceptance` at the repository root and must run against the real API. Unit passes do not substitute for browser or physical commissioning acceptance.

## Classroom operations upgrade

The original twelve workspaces remain available. **教室工作台** adds `/classrooms` and `/classrooms/:spaceId`; its DTOs in `src/lib/classroom-types.ts` are aliases of the generated OpenAPI, never a client simulation adapter.

- The scoped API loads all published rooms (currently 603), while the matrix renders at most 96 tiles per page. Room search, building/floor filters, occupancy/output/mode dimensions and pagination reach the complete response. Aggregates are calculated over the full loaded scope, not just the visible page. Missing values remain unknown.
- The `at` query parameter selects an exact historical snapshot and survives classroom ↔ campus-floor links. Historical cards and plans do not permit control or mode writes. Invalid supplied timestamps are rejected by the API rather than silently becoming current state.
- Room cards group actual channel descriptors by device and declared product family. Sense is read-only, light raw counts stay raw counts, and requested relay state is distinct from output feedback. An absent feedback capability is labeled explicitly. SIMULATED Switch sensing/feedback does not establish real Switch hardware capability.
- Single-room history is fetched only on its history tab. It renders API half-open intervals, explicit unknown gaps, observed power coverage, original observation IDs and actual command/feedback events. Initially only the latest 50 events are rendered; earlier events remain available on demand.
- The interval distribution tab is loaded on demand, uses server-computed space-duration aggregates, and preserves historical source modes. Query cancellation and cache identity prevent a prior time range from overwriting a newer one.
- Manual takeover is bounded; maintenance/fault/automatic changes retain a reason and explicit review when releasing a protected state. All device commands still use the existing server eligibility and exact-load review flow. Classroom policies support SHADOW or SIMULATED only, with create → evaluate → review → dispatch → persisted feedback. No setpoint, dimming or real multi-relay control is invented.
- Room anomalies expose rule version, threshold, median/MAD conditional baseline, historical sample count, required persistence, quality flags and original observation IDs. Acknowledge/resolve require diagnostic notes; insufficient baseline is not rendered as a learned success.
- Room-level plans reuse the existing schedule workflow and preserve the distinction between planned attendance and actual occupancy. The general alarm workspace exposes a separate classroom-history tab.

Frontend test fixtures live only under `src/test-fixtures/` and are imported only by tests. The shipped components always request authenticated backend data. API integration and screenshot evidence should record the exact DB seed timestamp and viewport; genuine browser screenshots are a separate acceptance stage from type checking, React tests and production build.

### Three-gang target and rule verification

Switch cards expose `relay.1`, `relay.2` and `relay.3` independently plus exactly one `meter.aggregate`. Each request carries the server's stable `channel_id`; device-wide Switch/light requests are blocked in the legacy command and device screens. The optional `manual_hold_seconds` is an atomic channel-specific **backend/edge** override, not a firmware/local-button hold. UI changes to the reviewed target/state/action clear acknowledgement.

Requested state, actuator-reported state and independently measured physical output remain separate. Switch terminal status `acknowledged_unverified` is displayed as unverified; it is not merged into successful physical verification or failures. A Switch aggregate meter is never copied into per-gang power. Missing device UTC is shown as unknown, with authenticated relative age and platform knowledge time separately disclosed.

Room anomaly settings read authoritative GET values and PATCH a new version with `expected_revision` and a reason. A conflict is visible and requires explicit reload. W thresholds, median/MAD factors, persistence and clear hysteresis are labeled engineering assumptions; no client default silently replaces an unreadable configuration. Historical views disable configuration and lifecycle writes.

The optional acceptance script `scripts/verify-classroom-upgrade.py` runs from `backend/` using its Python environment, against a **disposable copy** of `/tmp/classroom-v3.db`. It verifies all 603 spaces and 4,221 corrected-profile channels, exact relay-2 effects, untouched relay-1/3, unverified-only outcome, scoped hold, rule conflict, shadow rejection and persisted evaluation reopening. It does not replace actual browser acceptance.

### Product-family references

PLUG, SWITCH and PRESENCE each resolve their own authenticated manifest, fixed engineering hero image and optional GLB. Classroom cards request only the small family hero; the heavy renderer and GLB remain behind an explicit “加载三维参考模型” action. Unknown/generic devices do not inherit the Plug model. Changing a reference family resets the viewer to unloaded. The backend validates hero/model bytes and hashes, while the client additionally verifies model SHA-256 and same-origin family identity before parsing.

`node scripts/verify-product-families.mjs ../packages/product/dist` checks each published GLB with the exact shipped `GLTFLoader`, including all declared selectable part identities and finite model bounds. This CPU-only check is deliberately not described as a WebGL or browser rendering test.
