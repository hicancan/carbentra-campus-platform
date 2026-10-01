"""Pinned real reference identities, explicitly synthetic instrumentation and measurements."""
import hashlib
import json
import math
from datetime import timedelta
from sqlalchemy import select, insert, func
from .common import payload_hash, audit
from .db import utcnow, iso
from .models import Campus, Building, Floor, Space, Circuit, Device, Binding, Telemetry, Alarm, CarbonFactor, Tariff, Strategy, State, Command
from .registry import add_binding
from .schemas import TelemetryIn
from .telemetry import ingest_sample


def stable_number(value):
    return int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)


from .spatial import import_package


def synthetic_power(device, at, desired_on=True):
    number = stable_number(device.id)
    local_hour = (at.hour + 8 + at.minute / 60) % 24
    daytime = .23 + .77 * max(0, math.sin((local_hour - 6) / 16 * math.pi))
    profile = .6 + .4 * daytime if device.provenance.get("category") == "residential" else daytime
    base = device.provenance["simulated_base_power_w"]
    variance = 1 + .045 * math.sin(at.timestamp() / 3600 + number % 31)
    return round(base * profile * variance * (1 if desired_on else .015), 3)


def seed_demo(db, settings, now=None):
    previous = db.get(State, "demo_seed")
    if previous:
        if previous.value.get("classroom_boundary_model") != "same-scenario-v3":
            raise RuntimeError("Legacy synthetic boundary fixture requires a fresh development database; historical meter evidence is not rewritten to add new classroom loads")
        from .classroom_simulation import seed_classrooms
        return seed_classrooms(db, settings, now)
    now = (now or utcnow()).replace(microsecond=0)
    import_package(db, settings, apply=True, actor="demo-spatial-import")
    buildings = list(db.scalars(select(Building).order_by(Building.id)).all())
    from .classroom_simulation import scenario_values, SCENARIOS
    room_specs = {}
    for room_index, room in enumerate(db.scalars(select(Space).order_by(Space.id))):
        room_specs.setdefault(room.building_id, []).append((room.id, SCENARIOS[room_index % len(SCENARIOS)]))
    all_devices = []
    for index, building in enumerate(buildings):
        short = hashlib.sha256(building.id.encode()).hexdigest()[:10].upper()
        main_id = f"sim-circuit:{short}:main"
        db.add(Circuit(id=main_id, campus_id=building.campus_id, building_id=building.id, name=f"{building.name} · 仿真总回路", kind="main", source_mode="SIMULATED"))
        db.flush()
        spaces = list(db.scalars(select(Space).where(Space.building_id == building.id).order_by(Space.id).limit(4)).all())
        for slot in range(5):
            meter = slot == 0
            space = spaces[(slot - 1) % len(spaces)] if spaces and not meter else None
            circuit_id = main_id if meter else f"sim-circuit:{short}:load-{slot}"
            if not meter:
                db.add(Circuit(id=circuit_id, campus_id=building.campus_id, building_id=building.id, space_id=space.id if space else None,
                    parent_id=main_id, name=f"{space.name if space else building.name} · 仿真支路 {slot}", kind="load", source_mode="SIMULATED"))
                db.flush()
            device_id = f"SIM-{short}-{'M' if meter else f'P{slot:02}'}"
            scenario = "offline" if (index * 5 + slot) % 43 == 42 else "uncalibrated" if (index * 5 + slot) % 59 == 58 else "normal"
            base = (25000 + stable_number(building.id) % 330000) if meter else (250 + stable_number(device_id) % 1950)
            device = Device(id=device_id, name=f"{building.name} · {'总电表' if meter else f'智能插座 {slot}'}", campus_id=building.campus_id, building_id=building.id,
                floor_id=space.floor_id if space else None, space_id=space.id if space else None, circuit_id=circuit_id, kind="meter" if meter else "smart_plug",
                source_mode="SIMULATED", commissioned=True, critical=meter or slot == 4, allow_control=not meter and slot != 4,
                profile_id="simulated-meter-v1" if meter else "simulated-controllable-v1", capabilities=["metering"] if meter else ["metering", "temperature", "hold", "shed", "restore"],
                provenance={"source": "deterministic-campus-simulation-v1", "synthetic": True, "real_installation_claim": False, "scenario": scenario,
                    "simulated_base_power_w": base, "category": building.category, "binding_status": "scenario_reference_only", "calibration": "synthetic fixture, not laboratory calibration"},
                created_at=now-timedelta(days=15), updated_at=now)
            db.add(device)
            db.flush()
            add_binding(db, device, "demo-seed", "SIMULATED placement on source reference; not a verified installation", now-timedelta(days=15))
            if meter:
                db.get(Circuit, main_id).meter_device_id = device.id
            all_devices.append(device)
    db.flush()
    children_by_building = {}
    for child in all_devices:
        if child.kind == "smart_plug":
            children_by_building.setdefault(child.building_id, []).append(child)
    # Seed into the same telemetry table/schema, with deterministic synthetic provenance.
    for device in all_devices:
        binding = db.scalar(select(Binding).where(Binding.device_id == device.id))
        points = 673 if device.kind == "meter" else 49
        finish = now - timedelta(hours=2) if device.provenance["scenario"] == "offline" else now
        epoch = hashlib.sha256(f"simulation:{device.id}:{iso(now)}".encode()).hexdigest()[:32]
        energy, rows = 0.0, []
        for seq in range(points):
            at = finish - timedelta(minutes=30 * (points - 1 - seq))
            power = synthetic_power(device, at)
            if device.kind == "meter":
                power += sum(synthetic_power(child, at) for child in children_by_building.get(device.building_id, []))
                power += sum(sum(scenario_values(room_id, at, now, scenario)[3].values()) for room_id, scenario in room_specs.get(device.building_id, []))
            if seq:
                energy += power * .5
            flags = ["UNCALIBRATED"] if device.provenance["scenario"] == "uncalibrated" else []
            raw = {"device_id": device.id, "boot_epoch": epoch, "sample_seq": str(seq), "observed_at": iso(at), "time_source": "simulated", "time_uncertainty_ms": 0.0,
                "active_power_w": power, "voltage_v": 230.0, "current_a": round(power/230/.98, 4), "energy_import_wh": round(energy, 6), "energy_export_wh": 0.0,
                "board_temperature_c": round(28+power/100000, 2), "desired_on": True, "output_present": True, "fault_latched": False,
                "valid": True, "calibrated": not flags, "energy_status": "known", "energy_uncertain_intervals": 0, "source_mode": "SIMULATED", "source_version": "campus-simulation-v1"}
            rows.append({**{k: v for k, v in raw.items() if k not in {"valid", "calibrated", "energy_status", "energy_uncertain_intervals", "observed_at"}},
                "observed_at": at, "received_at": at, "payload_hash": payload_hash(raw), "raw_payload": raw, "quality": "uncertain" if flags else "good", "quality_flags": flags,
                "campus_id": device.campus_id, "building_id": device.building_id, "space_id": device.space_id, "circuit_id": device.circuit_id, "binding_id": binding.id})
        db.execute(insert(Telemetry), rows)
        latest = db.scalar(select(Telemetry).where(Telemetry.device_id == device.id).order_by(Telemetry.id.desc()).limit(1))
        device.latest_telemetry_id = latest.id
        device.last_seen_at = latest.received_at
        if device.provenance["scenario"] != "normal":
            offline = device.provenance["scenario"] == "offline"
            db.add(Alarm(id=f"alarm-seed-{device.id}", device_id=device.id, campus_id=device.campus_id, building_id=device.building_id, space_id=device.space_id,
                type="device_offline" if offline else "data_quality", severity="warning", title=f"{device.name} · {'离线场景' if offline else '数据质量场景'}",
                description="SIMULATED scenario for operator lifecycle testing. No actual campus fault is claimed.", source_mode="SIMULATED", created_at=finish))
    from .projection import queue_history
    db.flush()
    queue_history(db,device_ids=[d.id for d in all_devices if d.kind=="meter"],end=now,now=now)
    valid_from, valid_to = now-timedelta(days=365), now+timedelta(days=365)
    db.add(CarbonFactor(id="simulated-factor-v1", name="仿真排放因子 · 非官方", region="SIMULATED", year=now.year, kg_co2e_per_kwh=.55,
        valid_from=valid_from, valid_to=valid_to, source_url="https://example.invalid/synthetic-carbon-factor", source_mode="SIMULATED", version=1))
    db.add(Tariff(id="simulated-tariff-v1", name="仿真单一电价 · 非真实账单", currency="CNY", rate_per_kwh=.82, valid_from=valid_from, valid_to=valid_to,
        source_url="https://example.invalid/synthetic-tariff", source_mode="SIMULATED", version=1))
    campus = db.scalar(select(Campus).order_by(Campus.id))
    db.add(Strategy(id="strategy-demo-shadow", name="校园非关键负载削峰 · 影子评估", description="Only evaluates explicitly simulated noncritical controllable loads. No automatic dispatch.",
        campus_id=campus.id, target_reduction_pct=5, max_devices=30, created_by="demo-seed"))
    db.add(State(key="demo_seed", value={"version": 2, "at": iso(now), "devices": len(all_devices), "source_mode": "SIMULATED", "classroom_boundary_model": "same-scenario-v3"}))
    audit(db, "demo-seed", "created", "simulation", "campus", {"devices": len(all_devices), "measurement_claim": False})
    db.commit()
    from .classroom_simulation import seed_classrooms
    seed_classrooms(db, settings, now)
    return True


def simulation_tick(db, now=None):
    from .simulation import emit_sample
    now = (now or utcnow()).replace(microsecond=0)
    devices = list(db.scalars(select(Device).where(Device.source_mode == "SIMULATED", Device.dispatch_mode == "IN_PROCESS").order_by(Device.kind.desc())))
    count = 0
    for device in devices:
        if device.provenance.get("source") != "deterministic-campus-simulation-v1" or device.provenance.get("scenario") == "offline":
            continue
        if emit_sample(db, device, now):
            count += 1
    return count
