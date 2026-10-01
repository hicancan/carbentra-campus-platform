"""Deterministic all-mapped-room fixtures; every instrument and reading is SIMULATED.

Sparse 21-day baseline evidence plus a contiguous 24-hour demonstration window.
This is not a surveyed installation, human occupancy tracking, or measured savings.
"""
import hashlib
from datetime import timedelta
from sqlalchemy import select, insert
from .models import (Space, Device, Circuit, Binding, DeviceChannel, ChannelObservation,
    Telemetry, State, RoomMode, ScheduleEvent, SimulatedOutput, SimulatedChannelOutput)
from .db import utcnow, iso
from .common import payload_hash
from .registry import add_binding
from .seed import stable_number

SOURCE = "deterministic-classroom-simulation-v1"
SCENARIOS = ("occupied", "vacant_load", "vacant_off", "presence_stale", "feedback_unknown", "high_load",
    "maintenance", "manual_override", "local_fault", "critical_load", "mixed_activity", "arrival")


def scenario_values(space_id, at, anchor, scenario):
    n = stable_number(space_id)
    local_hour = (at.hour + 8 + at.minute/60) % 24
    occupied = 7.5 <= local_hour < 21.5 and (int(at.timestamp()/3600)+n)%5 != 0
    if scenario in {"vacant_load", "vacant_off"}:
        occupied = False
    if scenario == "high_load":
        occupied = True
    if scenario == "arrival" and at > anchor-timedelta(minutes=20):
        occupied = True
    light_on = occupied or scenario == "vacant_load"
    socket_on = occupied or scenario in {"vacant_load", "critical_load"}
    if scenario == "local_fault":
        light_on=socket_on=False
    base = 180. + n%260
    power = {"lighting": round((base*.65 if light_on else 0.5), 3), "socket": round((base if socket_on else 1.), 3)}
    if scenario == "mixed_activity":
        power["lighting"]=round(base*.65*((2 if light_on else 1)/3),3)
    if scenario == "high_load" and at >= anchor-timedelta(hours=2):
        power = {k: v*7 for k, v in power.items()}
    return occupied, light_on, socket_on, power


def seed_classrooms(db, settings, now=None):
    existing = db.get(State, "classroom_demo_seed")
    if existing:
        if existing.value.get("version", 1) < 3:
            raise RuntimeError("Pre-release single-output classroom fixture detected; use a fresh development fixture database. Evidence is not silently rewritten.")
        return False
    now = (now or utcnow()).replace(microsecond=0)
    spaces = list(db.scalars(select(Space).order_by(Space.id)))
    if not spaces:
        return False
    # Three sparse historical same-hour neighborhood observations on each of three prior weeks, plus
    # a fresh 15-minute series. Gaps outside this window stay visibly unknown.
    times = sorted({now-timedelta(days=d, hours=h) for d in (7, 14, 21) for h in (-1, 0, 1)} |
        {now-timedelta(minutes=15*i) for i in range(97)})
    count = 0
    for index, space in enumerate(spaces):
        short = hashlib.sha256(space.id.encode()).hexdigest()[:12].upper()
        scenario = SCENARIOS[index % len(SCENARIOS)]
        room_devices = {}
        for role, kind in (("S", "presence"), ("L", "switch"), ("P", "smart_plug")):
            ident = f"SIM-ROOM-{short}-{role}"
            cid = f"sim-room-circuit:{short}:{role}" if role != "S" else None
            if cid:
                main = db.scalar(select(Circuit).where(Circuit.building_id == space.building_id, Circuit.kind == "main", Circuit.source_mode == "SIMULATED").limit(1))
                db.add(Circuit(id=cid, campus_id=space.campus_id, building_id=space.building_id, space_id=space.id,
                    parent_id=main.id if main else None, name=f"{space.name} · 仿真{'照明' if role == 'L' else '插座'}支路", kind="load", source_mode="SIMULATED"))
                db.flush()
            critical = role != "S" and scenario == "critical_load"
            device = Device(id=ident, name=f"{space.name} · {'Sense' if role == 'S' else 'Switch 照明' if role == 'L' else 'Plug 插座'} · SIMULATED",
                campus_id=space.campus_id, building_id=space.building_id, floor_id=space.floor_id, space_id=space.id,
                circuit_id=cid, kind=kind, source_mode="SIMULATED", dispatch_mode="IN_PROCESS", commissioned=True,
                critical=critical, allow_control=role != "S" and not critical, profile_id="simulated-switch-v1" if role == "L" else "simulated-classroom-v1",
                capabilities=["presence", "illuminance"] if role == "S" else ["metering", "hold", "shed", "restore"] if role == "L" else ["metering", "hold", "shed", "restore", "relay_feedback"],
                minimum_dwell_seconds=300,
                provenance={"source": SOURCE, "synthetic": True, "scenario": scenario, "scenario_anchor": iso(now),
                    "simulated_base_power_w": 180+stable_number(space.id)%260, "real_installation_claim": False,
                    "feedback": "Switch actuator report only; no per-relay power or independent feedback" if role == "L" else "Explicitly synthetic Plug feedback", "fixture_version": 3, "command_concurrency": "per_channel", "binding_status": "scenario_reference_only"},
                created_at=times[0]-timedelta(hours=1), updated_at=now)
            db.add(device)
            db.flush()
            binding = add_binding(db, device, "classroom-demo-seed", "SIMULATED reference placement; not a commissioned real installation", times[0]-timedelta(hours=1))
            room_devices[role] = (device, binding)
        channels = []
        definitions = [("S", "sensor.radar", "presence", ["presence.radar"], None),
            ("S", "sensor.light", "illuminance", ["illuminance.raw"], "raw_count"),
            *(("L", f"relay.{i}", "lighting", ["relay.commanded"], None) for i in (1,2,3)),
            ("L", "meter.aggregate", "power", ["power.active", "energy.import"], "W"),
            ("P", "relay.1", "socket", ["relay.commanded", "relay.feedback", "power.active"], "W")]
        for role, key, kind, caps, unit in definitions:
            device, binding = room_devices[role]
            channel = DeviceChannel(id=f"{device.id}:{key}", device_id=device.id, campus_id=space.campus_id, channel_key=key,
                name=f"{space.name} · {kind}", kind=kind, capabilities=caps, unit=unit,
                freshness_seconds=900, controllable=kind in {"lighting", "socket"}, introduced_at=times[0]-timedelta(hours=1), created_at=times[0]-timedelta(hours=1))
            db.add(channel)
            channels.append((role, channel, binding))
        db.flush()
        for role, channel, binding in channels:
            device = room_devices[role][0]
            rows, telemetry_rows, energy = [], [], 0.
            epoch = hashlib.sha256(f"{SOURCE}:{device.id}:{iso(now)}".encode()).hexdigest()[:32]
            previous = None
            for sequence, at in enumerate(times):
                if scenario == "presence_stale" and role == "S" and at > now-timedelta(hours=2):
                    continue
                occupied, light_on, socket_on, powers = scenario_values(space.id, at, now, scenario)
                on = light_on if role == "L" else socket_on
                if channel.kind == "presence":
                    value = {"occupancy": "occupied" if occupied else "vacant"}
                elif channel.kind == "illuminance":
                    value = {"number": float(500+stable_number(space.id)%800) if light_on else 23.}
                elif channel.kind == "lighting":
                    # Three independently addressable requested/reported states,
                    # with no invented physical feedback or per-channel meter.
                    reported = on if channel.channel_key != "relay.3" or scenario != "mixed_activity" else not on
                    value = {"desired_on": reported, "actuator_reported_on": reported, "output_present": None,
                        "fault_latched": scenario == "local_fault"}
                elif channel.kind == "power":
                    value = {"active_power_w": powers["lighting"]}
                else:
                    value = {"output_present": on, "desired_on": on, "active_power_w": powers["socket"],
                        "fault_latched": scenario == "local_fault"}
                valid = not (scenario == "feedback_unknown" and role == "L" and channel.kind == "lighting")
                quality, flags = ("good", []) if valid else ("uncertain", ["ACTUATOR_REPORT_UNKNOWN"])
                raw = {"channel_id": channel.id, "boot_epoch": epoch, "sample_seq": str(sequence), "observed_at": iso(at),
                    "value": value, "source_mode": "SIMULATED", "source_version": SOURCE}
                rows.append(dict(channel_id=channel.id, device_id=device.id, boot_epoch=epoch, sample_seq=str(sequence),
                    observed_at=at, received_at=at, valid_until=at+timedelta(seconds=900), value=value, quality=quality, quality_flags=flags,
                    source_mode="SIMULATED", source_version=SOURCE, payload_hash=payload_hash(raw), campus_id=space.campus_id,
                    building_id=space.building_id, space_id=space.id, binding_id=binding.id))
                if role == "P":
                    power = powers[channel.kind]
                    if previous:
                        dt = (at-previous).total_seconds()
                        if dt <= 900:
                            energy += power*dt/3600
                    wire = {"device_id": device.id, "boot_epoch": epoch, "sample_seq": str(sequence), "observed_at": iso(at),
                        "time_source": "simulated", "time_uncertainty_ms": 0., "active_power_w": power, "voltage_v": 230., "current_a": power/230,
                        "energy_import_wh": energy, "energy_export_wh": 0., "board_temperature_c": 28., "desired_on": on,
                        "output_present": value["output_present"], "fault_latched": value["fault_latched"], "valid": valid, "calibrated": True,
                        "energy_status": "known", "energy_uncertain_intervals": sum((b-a).total_seconds()>900 for a,b in zip(times[:sequence],times[1:sequence+1])),
                        "source_mode": "SIMULATED", "source_version": SOURCE}
                    telemetry_rows.append({k: v for k,v in wire.items() if k not in {"observed_at", "valid", "calibrated", "energy_status", "energy_uncertain_intervals"}} |
                        dict(observed_at=at, received_at=at, raw_payload=wire, payload_hash=payload_hash(wire), quality=quality, quality_flags=flags,
                            campus_id=space.campus_id, building_id=space.building_id, space_id=space.id, circuit_id=device.circuit_id, binding_id=binding.id))
                    previous = at
            db.execute(insert(ChannelObservation), rows)
            count += len(rows)
            if role == "L" and channel.kind == "power":
                for offset, row in enumerate(rows[-2:]):
                    power=row["value"]["active_power_w"]
                    raw={"device_id":device.id,"boot_epoch":row["boot_epoch"],"sample_seq":row["sample_seq"],
                        "counter_scope":"import_only","energy_uncertain_intervals":1,"source_mode":"SIMULATED", "source_version":SOURCE,
                        "projection_basis":"single simulated three-gang aggregate; export unavailable; not billing"}
                    telemetry_rows.append(dict(device_id=device.id,boot_epoch=row["boot_epoch"],sample_seq=row["sample_seq"],observed_at=row["observed_at"],
                        received_at=row["received_at"],time_source="simulated",time_uncertainty_ms=0.,active_power_w=power,voltage_v=230.,current_a=power/230.,
                        energy_import_wh=power*.25*offset,energy_export_wh=None,desired_on=None,output_present=None,fault_latched=scenario=="local_fault",
                        raw_payload=raw,payload_hash=payload_hash(raw),quality="uncertain",quality_flags=["EXPORT_UNAVAILABLE","ENERGY_UNCERTAIN"],
                        source_mode="SIMULATED",source_version=SOURCE,campus_id=space.campus_id,building_id=space.building_id,space_id=space.id,
                        circuit_id=device.circuit_id,binding_id=binding.id))
            if telemetry_rows:
                db.execute(insert(Telemetry), telemetry_rows)
                latest = db.scalar(select(Telemetry).where(Telemetry.device_id == device.id).order_by(Telemetry.observed_at.desc()).limit(1))
                device.latest_telemetry_id, device.last_seen_at = latest.id, latest.received_at
                if role == "P":
                    db.add(SimulatedOutput(device_id=device.id, campus_id=device.campus_id, desired_on=latest.desired_on,
                        output_present=latest.output_present if latest.output_present is not None else True,
                        fault_latched=bool(latest.fault_latched), updated_at=now))
            else:
                device.last_seen_at = rows[-1]["received_at"]
                if channel.kind == "lighting":
                    db.add(SimulatedChannelOutput(channel_id=channel.id,device_id=device.id,campus_id=space.campus_id,
                        actuator_reported_on=bool(rows[-1]["value"]["actuator_reported_on"]),updated_at=now))
        if scenario in {"maintenance", "manual_override", "local_fault"}:
            mode = {"maintenance": "maintenance", "manual_override": "manual", "local_fault": "fault"}[scenario]
            db.add(RoomMode(id=f"mode-seed-{short}", space_id=space.id, campus_id=space.campus_id, mode=mode,
                starts_at=now-timedelta(hours=2), ends_at=now+timedelta(hours=2) if mode == "manual" else None,
                reason=f"SIMULATED deterministic {scenario} scenario", created_by="classroom-demo-seed"))
        db.add(ScheduleEvent(id=f"schedule-room-{short}", campus_id=space.campus_id, building_id=space.building_id, space_id=space.id,
            title=f"{space.name} · 仿真课表（非实际教务数据）", kind="class", starts_at=now-timedelta(hours=1), ends_at=now+timedelta(hours=1),
            planned_occupancy=40, source=SOURCE, source_mode="SIMULATED", created_by="classroom-demo-seed"))
        if index % 40 == 39:
            db.flush()
    db.add(State(key="classroom_demo_seed", value={"version": 3, "at": iso(now), "rooms": len(spaces),
        "channels": len(spaces)*7, "observations": count, "source_mode": "SIMULATED", "measured_savings_claim": False}))
    db.commit()
    from .room_anomalies import evaluate_room
    for space in spaces:
        evaluate_room(db, space, now)
    db.commit()
    return True


def emit_presence(db, device, at):
    from .classroom_schemas import ChannelSample, ChannelValue
    from .classrooms import ingest_channel
    scenario = device.provenance.get("scenario", "occupied")
    if scenario == "presence_stale":
        return 0
    anchor = __import__('datetime').datetime.fromisoformat(device.provenance["scenario_anchor"].replace("Z", "+00:00"))
    occupied, light_on, _, _ = scenario_values(device.space_id, at, anchor, scenario)
    count = 0
    for channel in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id)):
        latest = db.scalar(select(ChannelObservation).where(ChannelObservation.channel_id == channel.id).order_by(ChannelObservation.observed_at.desc(), ChannelObservation.id.desc()).limit(1))
        if not latest or at <= latest.observed_at:
            continue
        value = ChannelValue(occupancy="occupied" if occupied else "vacant") if channel.kind == "presence" else ChannelValue(number=750. if light_on else 23.)
        sample = ChannelSample(channel_id=channel.id, boot_epoch=latest.boot_epoch, sample_seq=str(int(latest.sample_seq)+1), observed_at=at,
            time_source="simulated", time_uncertainty_ms=0., source_mode="SIMULATED", source_version=SOURCE, valid=True, value=value)
        ingest_channel(db, sample, received_at=at)
        count += 1
    return count


def room_power(db, device, at, state):
    anchor = __import__('datetime').datetime.fromisoformat(device.provenance["scenario_anchor"].replace("Z", "+00:00"))
    _, _, _, powers = scenario_values(device.space_id, at, anchor, device.provenance.get("scenario", "occupied"))
    power = powers["lighting" if device.kind == "light" else "socket"]
    return max(power, 180.+stable_number(device.space_id)%260) if state.output_present else .5
