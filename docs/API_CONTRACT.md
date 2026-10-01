# Campus HTTP contract v1

All routes below are relative to `/api/v1`. Success: `{data: VALUE, meta?: {total,limit,offset,...}}`. Errors: `{error:{code,message,request_id,details?}}`. Times UTC ISO-8601. Unknown quantities use null, never false zero. Paginated registry/ledger list routes accept `limit` 1–500 and `offset` >=0; aggregate and adapter routes have their own explicit bounds. Operational source mode is `SIMULATED`, `REPLAYED`, or `REAL`; no seeded device or telemetry is real.

## Authentication

- POST `/auth/login` `{username,password}` → `{data:{user:{id,username,display_name,role},csrf_token,expires_at}}`; HttpOnly session cookie `carbentra_session`, SameSite=Lax, secure in production
- GET `/auth/me` → same payload
- POST `/auth/logout` → `{data:{logged_out:true}}`
- Use credentials:include. All authenticated mutations require `X-CSRF-Token` returned by login/me. Browser Origin is checked against operator-configured allowed origins; no wildcard CORS
- Roles `admin`, `operator`, `analyst`, `viewer`. Operator/admin mutate registry, commands and alarms; analyst/admin create/evaluate strategies and reports; admin approves strategies; global administrators (`campus_ids:null`) edit global settings/accounting configuration. All authenticated roles read
- Explicit development fixture only: with CARBENTRA_ENV=development and CARBENTRA_DEV_AUTH=true, usernames admin/operator/analyst/viewer, password `development-only`. Deployment must be loopback-bound. Production rejects development auth and requires an operator-managed admin password and PostgreSQL

## Spatial registry

- GET `/campuses` → Campus[] `{id,name,timezone,source,source_mode,provenance}`
- GET `/buildings?campus_id=&q=` → Building[] `{id,campus_id,name,category,floors,area_m2,centroid:[longitude,latitude]|null,geometry:GeoJSON|null,external_space_id,source,source_mode,provenance,device_count}`
- GET `/buildings/{id}` → Building plus aggregate `device_count`
- GET `/floors?building_id=` → Floor[] `{id,building_id,name,level,source,provenance}`
- GET `/spaces?campus_id=&building_id=&floor_id=&q=` → Space[] `{id,campus_id,building_id,floor_id,name,kind,source,confidence,provenance}`
- GET `/topology?campus_id=&building_id=` → `{circuits:[{id,campus_id,building_id,space_id,parent_id,name,meter_device_id,kind,source_mode}],devices:[Device]}`
- GET `/assets/manifest` → the pinned spatial manifest plus provenance/availability

## Devices and telemetry

Device: `{id,name,campus_id,building_id,floor_id,space_id,circuit_id,kind,source_mode,commissioned,critical,allow_control,profile_id,profile_revision,capabilities:string[],status,last_seen_at,latest:{observed_at,received_at,active_power_w,voltage_v,current_a,energy_import_wh,energy_export_wh,board_temperature_c,desired_on,output_present,quality,source_mode}|null,provenance,created_at,updated_at}`

- GET `/devices?campus_id=&building_id=&space_id=&q=&status=&source_mode=` → Device[]
- GET `/devices/{id}` → Device plus `binding_history` and `command_count`
- POST `/devices` `{id,name,campus_id,building_id?,floor_id?,space_id?,circuit_id?,kind:'smart_plug'|'meter'|'sensor',source_mode:'SIMULATED'|'REPLAYED'|'REAL',critical?:bool,allow_control?:bool,capabilities?:string[]}`
- PATCH `/devices/{id}` `{name?,commissioned?,critical?,allow_control?}`
- PUT `/devices/{id}/binding` `{campus_id,building_id?,floor_id?,space_id?,circuit_id?,reason}`; clears commissioning/control authorization after movement
- GET `/devices/{id}/telemetry?start=&end=&limit=` and `/telemetry?device_id=&building_id=&circuit_id=&start=&end=` → Telemetry[] `{id,device_id,boot_epoch,sample_seq,observed_at,received_at,time_source,time_uncertainty_ms,active_power_w,voltage_v,current_a,energy_import_wh,energy_export_wh,board_temperature_c,desired_on,output_present,quality,quality_flags:string[],source_mode,source_version}`

## Overview and accounting

- GET `/overview?campus_id=&building_id=` → `{scope:{campus_id,building_id},source_mode,generated_at,freshness:{status,latest_sample_at,stale_after_seconds},counts:{buildings,spaces,devices,online_devices,stale_devices,offline_devices,active_alarms},energy:{known_kwh,coverage_ratio,quality,period_start,period_end},power:{active_kw,quality},carbon:{kg_co2e,factor_id,quality},cost:{amount,currency,tariff_id,quality},trend:[{timestamp,known_kwh,active_kw}],buildings:[{id,name,active_kw,known_kwh,device_count,alarm_count,quality}],alarms:Alarm[],provenance:{...}}`
- GET `/energy/summary?campus_id=&building_id=&start=&end=&device_ids=` → `{known_kwh,export_kwh,coverage_ratio,quality,period_start,period_end,device_count,interval_count,excluded_intervals,source_mode,warnings,method,selected_device_ids}`
- GET `/energy/breakdown?...&group_by=building|device|circuit` → `[{id,name,known_kwh,coverage_ratio,quality,source_mode}]`
- GET `/energy/balance?...` → `{parent_kwh,children_kwh,residual_kwh,quality,warnings}`
- GET `/carbon/summary?...` → EnergySummary plus `{kg_co2e,factor_id,factor,method:'location_based',reduction_claim:false}`
- GET `/cost/summary?...` → EnergySummary plus `{amount,currency,tariff_id,tariff}`
- GET/POST `/carbon/factors` → `{id,name,region,year,kg_co2e_per_kwh,valid_from,valid_to,source_url,source_mode,version}`
- GET/POST `/tariffs` → `{id,name,currency,rate_per_kwh,valid_from,valid_to,source_url,source_mode,version}`

## Commands (default SIMULATED execution; protected adapter transport)

Command `{id,device_id,action,sequence,status,reason,source_mode,issued_at,expires_at,created_by,idempotency_key,simulation_scenario,history:[{status,at,reason,evidence}],result:null|{desired_on,output_present,voltage_absence_proven:false,simulated:bool}}`.

- GET `/commands?campus_id=&building_id=&device_id=&status=` and GET `/commands/{id}`
- POST `/commands` header Idempotency-Key required; body `{device_id,action:'hold'|'shed'|'restore',expires_in_seconds:1..60,reason,simulation_scenario?:'success'|'reject'|'fail'|'timeout'}`. Returns persisted command; background worker drives requested→dispatched→acknowledged→verified or rejected/failed/timed_out. Poll details. Reused same key/body returns original; changed body returns409
- REAL/REPLAYED control returns explicit 409 physical_control_disabled in the delivered default configuration. Critical, stale, uncommissioned, unsupported capability and minimum dwell constraints fail closed. Optional software MQTT transport is implemented and independently tested; real transport additionally requires the commissioning and deployment gates described below

## Alarms and strategies

Alarm `{id,device_id,campus_id,building_id,space_id,type,severity,status,title,description,source_mode,created_at,acknowledged_at,resolved_at,acknowledged_by,resolved_by,notes:[{at,by,text}]}`
- GET `/alarms?campus_id=&building_id=&status=&severity=`; GET `/alarms/{id}`
- POST `/alarms/{id}/acknowledge` `{note?}`; POST `/alarms/{id}/resolve` `{note}`; POST `/alarms/{id}/notes` `{note}`
- GET `/forecasts?campus_id=&building_id=&horizon_hours=24` → `{method:'seasonal_naive'|'ridge_regression',trained_until,source_mode,quality,mae_kw,points:[{timestamp,predicted_kw,lower_kw,upper_kw}],warnings}`
- GET/POST `/strategies` → Strategy `{id,name,description,campus_id,building_id,target_reduction_pct,max_devices,status,mode:'SHADOW',created_at,created_by,approved_at,approved_by,latest_evaluation:null|Evaluation}`; POST body `{name,description?,campus_id,building_id?,target_reduction_pct,max_devices?}`
- POST `/strategies/{id}/evaluate` `{}` → Evaluation `{id,strategy_id,created_at,mode:'SHADOW',candidate_device_ids,rejected_devices:[{device_id,reason}],estimated_reduction_kw,baseline_kw,quality,source_mode,dispatch_performed:false}`
- POST `/strategies/{id}/approve` `{note}` → Strategy (approval does not dispatch)

## Reports, audit, status

- GET `/reports?campus_id=&building_id=` → Report[] `{id,name,type,created_at,created_by,source_mode,parameters,summary}`
- POST `/reports` `{name,type:'energy'|'carbon'|'cost'|'operations',campus_id?,building_id?,start?,end?}` → Report (durable snapshot)
- GET `/reports/{id}` → Report plus `content`
- GET `/reports/{id}/export?format=json|csv` → attachment
- GET `/audit?campus_id=&entity_type=&entity_id=&limit=` → `[{id,actor,action,entity_type,entity_id,at,details}]`
- GET `/settings` → safe operational values only; PATCH `/settings` requires a global administrator and accepts `{stale_after_seconds?,offline_after_seconds?}`
- GET `/system/status` → `{mode,version,database:{status,dialect},worker:{status,last_tick_at},ingestion:{last_received_at,total_samples},physical_control:{enabled:false,reason},spatial:{...},simulation:{enabled,source_mode},warnings:[]}`
- GET `/events?after_id=` → Server-Sent Events, event `change`, data `{id,type,entity_id,at}`. Polling fallback supported
- Public `/health/live`, `/health/ready` are outside `/api/v1`

## Additions implemented after the initial UI contract

The generated OpenAPI is the canonical current field contract. Additional semantics and strict limits:

- User DTO includes `campus_ids:null|[]|string[]`. Null is global; [] grants no campus access. Server-side campus scope applies to lists, direct-ID reads/writes, histories, audit, events and exports. Role/scope/password changes revoke all existing sessions
- GET/POST `/users`; POST `{username,display_name,role,campus_ids,password}` with password minimum16. PATCH `/users/{id}` `{display_name?,role?,campus_ids?,enabled?}`. POST `/users/{id}/password` `{password}`. Responses never include password hashes or session digests
- Device exposes `dispatch_mode:'IN_PROCESS'|'VIRTUAL'|'PHYSICAL'|'DISABLED'` (PHYSICAL is only set through the independently gated commissioning lifecycle). PATCH allows these three safe modes only; Ordinary REAL/REPLAYED enabling/commissioning stays rejected; the separate REAL release workflow is described below. Source mode and device identity are immutable
- POST `/circuits` `{id,campus_id,building_id?,space_id?,parent_id?,name,kind:'main'|'branch'|'load',source_mode}`; PATCH `/circuits/{id}` `{name?,parent_id?}`. Cycles/cross-campus/source-mode mismatch are rejected. A parent change after measurement history exists is rejected rather than relabeling old energy
- Telemetry GET accepts `campus_id` as well as device/building/circuit filters
- Factor and tariff POST require unique `id`, integer `version>=1`, aware `valid_from` AND non-null `valid_to`, HTTPS `source_url`, and explicit source_mode. Overlapping intervals for a source mode are rejected; versions are immutable
- Strategy `target_reduction_pct` is >0 and <=50. POST `/strategies/{id}/dispatch` uses `Idempotency-Key` (8–80 chars), body `{evaluation_id,reason}`, and returns `{evaluation_id,commands:[Command],source_mode:'SIMULATED',physical_dispatch:false}`. It requires an approved exact evaluation younger than5minutes, and rechecks every candidate. Approval alone never dispatches
- Command sequence is always a decimal JSON string and persists without signed-int32 or JavaScript float truncation. Terminal success references an immutable acknowledgement observation; IN_PROCESS simulation also references independently persisted `telemetry_id`
- GET `/adapter/commands?limit=20` uses bearer adapter identity and explicit device allowlist, returning `[{id,device_id,source_mode,dispatch_mode,transport:'MQTT',wire:{id,device_id,profile_id,seq,issued_s,expires_s,action},lease_id,lease_expires_at}]`
- POST `/adapter/commands/{id}/delivery` `{lease_id,status:'published'|'failed'|'expired',reason?}` → `{id,seq,status,durable:true}`. A publish acknowledgement only advances to dispatched
- POST `/ingest/firmware` accepts the exact pinned v2 firmware wire JSON. POST `/ingest/ack` accepts the exact v2 acknowledgement. Both authenticate the adapter and return durable receipts only after database commit. Acknowledgement receipt `{id,device_id,seq,durable:true,status:'stored'|'duplicate',matched}`. Unmatched/late evidence is retained without manufacturing success
- POST `/ingest/telemetry` accepts normalized `{samples:[TelemetryIn]}` with <=500 samples and a2MiB request cap. Duplicate object keys, non-finite numbers and ambiguous booleans are rejected

### Schedules

Schedule DTO `{id,campus_id,building_id,space_id,title,kind,starts_at,ends_at,planned_occupancy,status,source,source_mode,revision,created_by,created_at,updated_at,observed_occupancy:'unknown',control_authorization:false}`.

- GET `/schedules?campus_id=&building_id=&space_id=&start=&end=` with pagination
- POST `/schedules` and PUT `/schedules/{id}` body `{campus_id,building_id?,space_id?,title,kind:'teaching'|'holiday'|'event'|'maintenance',starts_at,ends_at,planned_occupancy?:integer|null,source,source_mode:'SIMULATED'|'REFERENCE'}`
- POST `/schedules/import` `{events:[ScheduleIn]}` <=500; atomic validation/import
- POST `/schedules/{id}/cancel` `{note}`; cancellation is recoverable history rather than deletion
- Active maintenance is a conservative control interlock. Planned occupancy0, a holiday or an absent class never prove actual vacancy or independently authorize control

### Forecast response

`/forecasts` now returns the transparent quality-gated model comparison from `app/forecasting.py`. Original `method,trained_until,source_mode,quality,mae_kw,points,warnings` fields are preserved. Additional `model,holdout,coverage,freshness,provenance` explain the eligible cohort, challenger, selected model, temporal holdout, source/time limitations and empirical residual bounds. It may select seasonal_naive when the trained ridge challenger performs worse. The result is never a measured-savings or real-campus-model claim.

### Operator-attested commissioning, disabled by default

This API records operator-reviewed evidence; it does not certify hardware or prove a physical installation. No commissioning/release is performed in the delivered demo.

- GET `/devices/{id}/commissioning` returns immutable record identities and their pending/released/revoked lifecycle
- POST `/devices/{id}/commissioning` (admin) `{id,profile_id,load_id,load_name,hardware_revision,safety_assessment_ref,installation_approval_ref,calibration_ref,valid_until}` records pending evidence against the current dated placement. REAL registration is required; no control is enabled
- POST `/devices/{id}/commissioning/release` (admin) `{release_id,operator_attested:true,noncritical_load_attested:true,note}` additionally requires independent deployment `CARBENTRA_PHYSICAL_DISPATCH_ENABLED=true` and exact release ID in `CARBENTRA_PHYSICAL_RELEASE_IDS`, fresh authenticated valid telemetry <=10s, matching hardware revision, control capabilities and unchanged placement. All deployment defaults remain false/empty
- POST `/devices/{id}/commissioning/{release_id}/revoke` (admin) `{note}` disables future dispatch and invalidates the device profile. Previously leased/in-flight delivery may remain uncertain and is not silently called cancelled
- PHYSICAL outbox items include `release_id`; the edge independently requires its own disabled-by-default physical gate and per-device release-ID allowlist. Backend approval alone cannot bypass the edge gate
- VIRTUAL/PHYSICAL command dispatch rechecks profile, actor authorization, critical-load policy, control permission, capability, fresh observation <=10s, local fault and minimum dwell at the actual lease boundary

### Optional lazy-loaded product reference

- GET `/assets/product/manifest` (authenticated) → `{version,name,source_mode:'REFERENCE',source_commit,source_sha256,display_sha256,model_url,bytes,units,axis,node_count,mesh_count,triangle_count,parts:[{id,name,node_index,provenance}],optimized:bool,materials_preserved:true,physical_qualification:false,device_binding:false,provenance,limitations}`
- GET `/assets/product/model` (authenticated) → pinned display-only GLB. The model is optional and must only be requested after an explicit product-view action; it is not loaded into the campus default view or instanced for every device
- Both return503 `product_asset_unavailable` when the optional artifact is not installed. The model does not prove installation, calibration, clearance or safe-to-touch state

### Fresh control eligibility and physical-action confirmation

GET `/devices/{id}/control-eligibility` returns `{device_id,device_name,profile_revision,source_mode,dispatch_mode,eligible,allowed_actions,reasons:{hold,shed,restore},physical_deployment_enabled,load:{id,name,profile_id},release:{id,status,valid_until,basis}|null,checked_at,server_rechecks_on_submission_and_lease:true,consequence}`. It applies current role/scope, release, binding, capability, clock/quality/feedback, critical-load, dwell and maintenance constraints. This preview is not authorization to skip submission/lease checks.

Commissioning records require explicit `load_id` and `load_name` in addition to the evidence fields above. A REAL POST `/commands` additionally requires `physical_confirmation:{device_id,release_id,profile_revision,load_id,action,understands_mains_consequence:true}` matching the currently released load. The browser must show the named device, named load, action and mains-power consequence before the user confirms. Omitted/mismatched confirmations are rejected. A changed release ID or profile revision returns409 `physical_review_stale` before command creation, requiring a fresh review. SIMULATED requests need no such object. No actual physical gate is enabled or hardware action performed by this implementation task.

### Time-of-use energy-charge estimation

Tariff read/write adds `timezone` (installed IANA name, default `Asia/Shanghai`) and `bands` (0–24 entries). Each band is `{start_minute:0..1439,end_minute:1..1440,rate_per_kwh,label?}`. Bands must be non-overlapping and cannot wrap midnight; use two bands for an overnight override. The explicit base `rate_per_kwh` covers all other local minutes. Versions and source-mode validity ranges remain immutable/non-overlapping. No institution price is inferred.

GET `/cost/summary?allocation_mode=strict|proportional_estimate` defaults to strict. A cumulative-counter interval spanning distinct rates lacks measured subinterval usage: strict returns unavailable amount; explicit proportional mode uses elapsed UTC time and labels estimation. Response evidence includes `pricing_mode`, `boundary_estimated_intervals`, `boundary_unresolved_intervals`, `pricing_coverage_ratio`, `allocation_method`, `derived_price_windows`, and optional `pricing_error`. All outputs have `charge_type:'configured_energy_charge_estimate'`, `settlement_bill:false`, and excluded separate demand/fixed charges. Ambiguous/nonexistent DST price switches abstain rather than choosing an undocumented fold/gap rule. POST `/reports` accepts `cost_allocation_mode` and preserves the selected mode/evidence in snapshots and exports.

### Machine-readable public responses

`backend/app/responses.py` defines runtime-validated auth, devices, telemetry, commands, energy/carbon/cost, forecasts and control eligibility. Unknown fields fail closed; serialization failures never echo internal values. The corresponding OpenAPI components are `AuthResponse`, `DeviceResponse`, `DeviceDetailResponse`, `TelemetryResponse`, `CommandResponse`, `EnergySummaryResponse`, `CarbonSummaryResponse`, `CostSummaryResponse`, `ForecastResponse`, and `ControlEligibilityResponse`, wrapped in typed `Envelope` schemas. Canonical uint64 counters are decimal strings even beyond JavaScript safe integers. Reproduce/check the generated artifact with `backend/tools/export_openapi.py [--check]`.

### Persisted reference-package state

`/system/status.spatial` exposes `bundled` package/seed/manifest hashes, the successfully `imported` registry version, and `synchronized`. Deploying a new bundled package does not imply the database metadata was reconciled. Operator CLI `python -m app.import_spatial --check|--apply [--expected-version SHA256]` imports source-only reference identities without demo users/devices/telemetry. Removals and source/parent changes are reported and refused atomically.

### Background forecast evaluation

GET `/forecasts` is responsive during backfill: it returns a stored result or an explicit queued result with null points. It never falls back to a synchronous raw scan/model fit. Optional `evaluation` is `{id,status:'queued'|'running'|'ready'|'failed'|'stale',worker_status,requested_at,started_at,completed_at,input_revision,result_input_revision,projection_pending_hours,retry_after_seconds,error_code,cached}`. Stored results retain their original `generated_at` and `trained_until`. Poll pending/running/stale results no more often than the suggested interval.

POST `/forecasts/refresh` body `{campus_id?,building_id?,horizon_hours?:1..72}` uses the session+CSRF and explicitly retries failed derived work. Repeated requests deduplicate; the queue is bounded. Scope is part of both the cache key and worker authorization. The analysis role reads append-only hour revisions selected by historical fact availability; it never actuates equipment. `/system/status.analysis` reports the independent analysis worker heartbeat.
