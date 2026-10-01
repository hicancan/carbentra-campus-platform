# CARBENTRA IoT application contract v1

This package is the **single maintained authority** for application capability,
channel/event/command schemas and concrete Plug v2 wire validation. Wire versions
are independent: application `schema_version: 1` is not manufacturer wire v1.

- `schemas/event.schema.json`: immutable typed observation envelope
- `schemas/descriptor.schema.json`: declared device/channel capabilities
- `schemas/command.schema.json`: one channel, explicit requested value, bounded lease
- `schemas/switch-ack.schema.json`: actual Switch MQTT command result, never physical verification
- `schemas/wire/`: supported Plug firmware v2 telemetry/ACK/command syntax
- `python/carbentra_iot_contract`: JSON Schema + semantic identity/units/finiteness/lease checks
- `typescript/index.ts`: consumer types; schema boundary validation remains mandatory
- `capabilities.json`: capability names, value types and units
- `products.json`: actual family/channel capability availability, rejecting overclaims
- `protocols/presence-gatt-v1.json`: GATT constants/offsets/ages/UUID authority
- `examples/`: validated source-labeled events, descriptors, commands and a public nonproduction GATT test vector

Repository Python imports use `PYTHONPATH=packages/iot-contract/python`. A built
wheel embeds the same schemas from their authoritative source using `setup.py`;
no second manually maintained schema copy is installed. `plug_wire` exposes the
existing `validate_telemetry`, `validate_ack`, `REJECTIONS`, and other wire constants.
Backend and gateway import those exact checks. Schema snapshots in OpenAPI are
generated documentation, not another source.

## Identity, times and quality

Sample identity is `(device_id, boot_id, sequence)`; `sequence` is a canonical
unsigned 64-bit decimal string. `event_id` is SHA256 of UTF-8
`carbentra-iot-v1\n{device_id}\n{boot_id}\n{sequence}`. A different payload at the same
identity is a conflict, never an overwrite. Edge receipt time is not intrinsic
sample identity: duplicate arrivals retain the first committed receipt time.

Command IDs contain only ASCII letters, digits, underscore and hyphen. Canonical
commands enforce each existing firmware wire boundary: 1–48 characters for
Switch (also its ACK limit), 1–47 for Plug. The JSON Schema is authoritative;
the gateway must reject oversized IDs before translation or publication. Ordinary
platform `cmd_` IDs (36 characters) and Edge `local-` IDs (38) fit both products.

`received_at` is the gateway's timestamp. The backend adds its own receipt time.
`observed_at` remains null without a device wall clock; gateway receipt does not
invent measurement time. GATT carries authenticated per-sensor monotonic ages;
the gateway conservatively adds the whole challenge round-trip to those ages.
A restarted gateway does not make its cached sample fresh.
For buffered REAL Plug observations, fresh arrival does not establish fresh
measurement: Edge control also requires authenticated UTC and the oldest endpoint
of the original `unix_lower_s`/`unix_upper_s` interval (maximum width five seconds),
including measurement age relative to captured same-boot uptime. Unknown clock,
time rollback, delayed samples and stale measurement evidence remain historical
data and cannot authorize control. Clockless live Switch transport retains its
explicit receipt/monotonic limitations and device-side boot-relative expiry.

`REAL`, `SIMULATED`, and `REPLAYED` remain separate all the way to the UI. Unknown,
invalid and unavailable readings carry null. Stale/partial/raw readings retain
explicit quality and do not become usable merely because a receipt is durable.
Wh is never silently converted to kWh. Aggregate Switch energy is a single device
boundary, not split or counted again on each lighting gang.

Channels: `relay.1` (Plug); `relay.1`–`relay.3` (Switch); `meter.aggregate`;
`sensor.radar`, `sensor.light`, `sensor.buffer`; `button.1`–`button.3`; `device`.
Current Sense RevB has **no PIR capability**. Reserved protocol bytes are not an
installed sensor. `illuminance.raw` is uncalibrated ADC `raw_count`, never lux.
Switch `relay.feedback` is explicitly unavailable. Plug feedback means qualified
optical output indication, not independently proven contact isolation or safety.

## Sense GATT v1, exact bytes

Service UUID `4c410001-7d6b-4c8f-a092-47b965150001`; challenge write UUID
`4c410002-7d6b-4c8f-a092-47b965150001`; response read UUID
`4c410003-7d6b-4c8f-a092-47b965150001`.

Manufacturer company ID `0xffff` is development-only. Its 24-byte v2 frame:

| Offset | Field |
|---|---|
| 0 | version=2 |
| 1 | flags: bit0 reserved=0, warming, low-buffer, vendor-unavailable, radar-power, button-event, light-valid, buffer-valid |
| 2 | radar enum: 0 unknown, 1 clear, 2 present |
| 3 | radar error code |
| 4 | stable enrolled identity, uint32 LE |
| 8 | random nonzero boot epoch, uint32 LE |
| 12 | sample sequence, uint32 LE |
| 16 | raw light, uint16 LE |
| 18 | buffer voltage mV, uint16 LE |
| 20 | monotonic seconds, uint32 LE |

The 86-byte authenticated response is:

| Offset | Field |
|---|---|
| 0 | response version=1 |
| 1–24 | exact frame above |
| 25–40 | gateway random 16-byte challenge |
| 41–44 | reserved PIR age=UINT32_MAX |
| 45–48 | radar measurement age ms, uint32 LE |
| 49–52 | light measurement age ms, uint32 LE |
| 53 | evidence flags: continuous occupancy, reserved PIR-valid=0, radar-valid, light-valid, buffer-valid; upper bits zero |
| 54–85 | HMAC-SHA256(key, `b'CARBENTRA-SENSE-GATT-v1\x00' + bytes[0:54]`) |

Each attempt consumes its nonce; response deadline is five monotonic seconds.
A valid flag cannot carry unknown age UINT32_MAX. A fresh continuous, healthy,
authenticated radar measurement can represent vacancy; a momentary CLEAR or
unavailable detector cannot. Device boot/sequence replay state persists across
gateway restarts and is separate from unauthenticated advertisements. Ads cannot
retire an authenticated boot or replace a cached authenticated observation.
Unsigned diagnostic application events use `boot_id: adv-<wire_boot_hex>`; the
original wire boot remains in raw evidence. Signed GATT events use the exact wire
boot hex. This domain separation prevents a forged ad from reserving a later
authenticated immutable tuple. For GATT-enrolled devices the gateway retains ads
locally for diagnostics/discovery and forwards only authenticated snapshots.
Advertisement generation and signed snapshot generation allocate distinct global
sample sequences; gaps within one transport are therefore not themselves proof
of lost measurements. Retransmitting an unchanged advertisement keeps its old sequence.

Per-device 32-byte keys are operator-provisioned through a separate secure process.
No production key is included or generated. Gateway key files must be private
regular binary files (0400 or 0600). Public fixture key material in the explicitly
named test vector must never be provisioned. Address/identity allowlisting by
itself does **not** authenticate BLE; unsigned advertisements remain diagnostic.

Run `python packages/iot-contract/tools/check_contract.py` to validate schema syntax, examples, family capabilities, TypeScript names and golden proof, and regenerate the source-fingerprint manifest.
