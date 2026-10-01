"""Stateful simulated output adapter, deliberately separate from command intent/verification."""
from sqlalchemy import select
from .models import SimulatedOutput, Telemetry, Device
from .schemas import TelemetryIn
from .telemetry import ingest_sample
from .adapter import store_ack


def output_state(db, device):
    state = db.get(SimulatedOutput, device.id)
    if state is None:
        latest = db.get(Telemetry, device.latest_telemetry_id)
        state = SimulatedOutput(device_id=device.id, campus_id=device.campus_id, desired_on=bool(latest.desired_on) if latest else True,
            output_present=bool(latest.output_present) if latest else True, fault_latched=False)
        db.add(state)
        db.flush()
    return state


def measured_power(db, device, at, state=None):
    from .seed import synthetic_power
    state = state or output_state(db, device)
    if device.provenance.get("source") == "deterministic-classroom-simulation-v1":
        from .classroom_simulation import room_power
        return room_power(db, device, at, state)
    if "simulated_base_power_w" in device.provenance:
        own = synthetic_power(device, at, state.output_present)
    else:
        latest = db.get(Telemetry, device.latest_telemetry_id)
        own = (latest.active_power_w or 0) if latest and state.output_present else 0.0
    if device.kind == "meter":
        # The building total is unmetered base plus its instrumented child loads.
        # A simulated shed therefore changes both local load and the measured boundary.
        children = db.scalars(select(Device).where(Device.building_id == device.building_id, Device.kind == "smart_plug", Device.source_mode == "SIMULATED")).all()
        own += sum(measured_power(db, child, at) for child in children)
        from .switch_simulation import aggregate_power
        for switch in db.scalars(select(Device).where(Device.building_id == device.building_id, Device.kind == "switch", Device.source_mode == "SIMULATED", Device.dispatch_mode == "IN_PROCESS")):
            if switch.provenance.get("source") == "deterministic-classroom-simulation-v1":
                own += aggregate_power(db,switch,at)[0]
    return round(own, 6)


def emit_sample(db, device, at, state=None, command=None):
    state = state or output_state(db, device)
    prior = db.get(Telemetry, device.latest_telemetry_id)
    if not prior or at <= prior.observed_at:
        return None
    dt = (at-prior.observed_at).total_seconds()
    power = measured_power(db, device, at, state)
    gap = dt > 1800
    sample = TelemetryIn(device_id=device.id, boot_epoch=prior.boot_epoch, sample_seq=str(int(prior.sample_seq)+1), observed_at=at,
        correlation_command_id=command.id if command else None, time_source="simulated", time_uncertainty_ms=0.0,
        active_power_w=power, voltage_v=230.0, current_a=round(power/230/.98, 6),
        energy_import_wh=(prior.energy_import_wh or 0)+((power+(prior.active_power_w or 0))/2*dt/3600 if not gap else 0), energy_export_wh=prior.energy_export_wh or 0.0,
        board_temperature_c=round(28+power/100000, 2), desired_on=state.desired_on, output_present=None if device.provenance.get("scenario") == "feedback_unknown" and device.kind == "light" else state.output_present, fault_latched=state.fault_latched,
        valid=True, calibrated=device.provenance.get("scenario") != "uncalibrated", energy_status="known",
        energy_uncertain_intervals=prior.raw_payload.get("energy_uncertain_intervals", 0)+int(gap), source_mode="SIMULATED", source_version="campus-simulation-v2")
    raw = sample.model_dump(mode="json")
    if command:
        raw.update(command_id=command.id, command_sequence=str(command.sequence), simulation_observation=True)
    row, _ = ingest_sample(db, sample, raw_payload=raw, received_at=at, actor="simulation-adapter")
    state.updated_at = at
    return row


def dispatch_simulated(db, command, device, now):
    state = output_state(db, device)
    state.pending_command_id = command.id
    state.desired_on = command.history[0]["evidence"]["desired_on"]
    state.requested_monotonic_ms = int(now.timestamp()*1000)
    state.deadline_monotonic_ms = state.requested_monotonic_ms + 5000
    state.updated_at = now
    db.flush()


def raw_ack(command, device, state, status, now):
    result = {"schema_version": 2, "device_id": device.id, "boot_epoch": command.expected_boot_epoch, "id": command.id, "seq": str(command.sequence),
        "status": status, "terminal": status != "REQUESTED_AWAITING_FEEDBACK", "desired_on": state.desired_on, "fault_latched": state.fault_latched,
        "voltage_absence_proven": False, "requested_monotonic_ms": state.requested_monotonic_ms, "deadline_monotonic_ms": state.deadline_monotonic_ms}
    if result["terminal"]:
        result.update(observed_monotonic_ms=int(now.timestamp()*1000), feedback_valid=True, output_present=state.output_present,
            output_sensing="AC_PRESENT" if state.output_present else "NO_AC_PULSES_DETECTED")
    return result


def accept_simulated(db, command, device, now):
    state = output_state(db, device)
    store_ack(db, raw_ack(command, device, state, "REQUESTED_AWAITING_FEEDBACK", now), now)


def observe_simulated(db, command, device, now):
    from .control import transition
    state = output_state(db, device)
    if command.simulation_scenario == "timeout":
        return
    monotonic = int(now.timestamp()*1000)
    if monotonic < state.requested_monotonic_ms + 100:
        return
    if monotonic >= state.deadline_monotonic_ms:
        store_ack(db, raw_ack(command, device, state, "TIMED_OUT", now), now)
        return
    # A separately persisted output state models the physical outcome, including a
    # stuck-output fault. The verifier below reads evidence, never the command action.
    state.output_present = not state.desired_on if command.simulation_scenario == "fail" else state.desired_on
    db.flush()
    sample = emit_sample(db, device, now, state, command)
    if sample is None:
        return
    for meter in db.scalars(select(Device).where(Device.building_id == device.building_id, Device.kind == "meter", Device.source_mode == "SIMULATED")):
        emit_sample(db, meter, now)
    status = "OBSERVED_VERIFIED" if state.output_present == state.desired_on else "FAILED_FEEDBACK"
    store_ack(db, raw_ack(command, device, state, status, now), now, telemetry_id=sample.id)
    state.pending_command_id = None
