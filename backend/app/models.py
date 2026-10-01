from sqlalchemy import Boolean, BigInteger, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base, UTCDateTime, UInt64Counter, utcnow
from datetime import datetime


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    campus_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_dev_fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    account_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    address_hash: Mapped[str] = mapped_column(String(64), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, default=False)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    csrf_token: Mapped[str] = mapped_column(String(80))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Campus(Base):
    __tablename__ = "campuses"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Shanghai")
    source: Mapped[str] = mapped_column(String(200))
    source_mode: Mapped[str] = mapped_column(String(30), default="REFERENCE")
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    category: Mapped[str] = mapped_column(String(80), default="unknown")
    floors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    centroid: Mapped[list | None] = mapped_column(JSON, nullable=True)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_space_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source: Mapped[str] = mapped_column(String(200))
    source_mode: Mapped[str] = mapped_column(String(30), default="REFERENCE")
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class Floor(Base):
    __tablename__ = "floors"
    id: Mapped[str] = mapped_column(String(180), primary_key=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(200))
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class Space(Base):
    __tablename__ = "spaces"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    floor_id: Mapped[str | None] = mapped_column(ForeignKey("floors.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(80), default="unknown")
    source: Mapped[str] = mapped_column(String(200))
    confidence: Mapped[str] = mapped_column(String(40), default="unverified")
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class Circuit(Base):
    __tablename__ = "circuits"
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), nullable=True, index=True)
    space_id: Mapped[str | None] = mapped_column(ForeignKey("spaces.id"), nullable=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("circuits.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    meter_device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), default="branch")
    source_mode: Mapped[str] = mapped_column(String(20), default="SIMULATED")


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), nullable=True, index=True)
    floor_id: Mapped[str | None] = mapped_column(ForeignKey("floors.id"), nullable=True)
    space_id: Mapped[str | None] = mapped_column(ForeignKey("spaces.id"), nullable=True, index=True)
    circuit_id: Mapped[str | None] = mapped_column(ForeignKey("circuits.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), default="smart_plug")
    source_mode: Mapped[str] = mapped_column(String(20))
    dispatch_mode: Mapped[str] = mapped_column(String(20), default="IN_PROCESS")
    physical_release_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commissioned: Mapped[bool] = mapped_column(Boolean, default=False)
    critical: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_control: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_id: Mapped[str] = mapped_column(String(100), default="unassigned")
    profile_revision: Mapped[int] = mapped_column(Integer, default=1)
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    minimum_dwell_seconds: Mapped[int] = mapped_column(Integer, default=300)
    last_control_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    next_command_sequence: Mapped[int] = mapped_column(UInt64Counter, default=1)
    latest_telemetry_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class Binding(Base):
    __tablename__ = "device_bindings"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160))
    building_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    floor_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    space_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    circuit_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime)
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(100))


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (UniqueConstraint("device_id", "boot_epoch", "sample_seq", name="uq_sample_identity"), Index("ix_telemetry_device_time", "device_id", "observed_at"), Index("ix_telemetry_building_time", "building_id", "observed_at"))
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    boot_epoch: Mapped[str] = mapped_column(String(80))
    sample_seq: Mapped[str] = mapped_column(String(20))
    correlation_command_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    time_source: Mapped[str] = mapped_column(String(40))
    time_uncertainty_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_power_w: Mapped[float | None] = mapped_column(Float, nullable=True)
    voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_import_wh: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_export_wh: Mapped[float | None] = mapped_column(Float, nullable=True)
    board_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    desired_on: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    output_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fault_latched: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    quality: Mapped[str] = mapped_column(String(30))
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    source_mode: Mapped[str] = mapped_column(String(20))
    source_version: Mapped[str] = mapped_column(String(100))
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    building_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    space_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    circuit_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    binding_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("device_bindings.id"), nullable=True)


class Command(Base):
    __tablename__ = "commands"
    __table_args__ = (UniqueConstraint("device_id", "sequence", name="uq_command_sequence"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    building_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dispatch_mode: Mapped[str] = mapped_column(String(20), default="IN_PROCESS")
    lease_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    delivery_receipt: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expected_boot_epoch: Mapped[str | None] = mapped_column(String(80), nullable=True)
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("device_channels.id", name="fk_commands_channel"), nullable=True, index=True)
    channel_key: Mapped[str] = mapped_column(String(100), default="relay.1")
    product_family: Mapped[str] = mapped_column(String(20), default="PLUG")
    manual_hold_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(20))
    sequence: Mapped[int] = mapped_column(UInt64Counter)
    status: Mapped[str] = mapped_column(String(30), index=True)
    reason: Mapped[str] = mapped_column(Text)
    source_mode: Mapped[str] = mapped_column(String(20))
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    created_by: Mapped[str] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    simulation_scenario: Mapped[str] = mapped_column(String(20), default="success")
    profile_revision: Mapped[int] = mapped_column(Integer)
    history: Mapped[list] = mapped_column(JSON, default=list)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Alarm(Base):
    __tablename__ = "alarms"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    building_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    space_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    type: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    source_mode: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[list] = mapped_column(JSON, default=list)


class CarbonFactor(Base):
    __tablename__ = "carbon_factors"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(100))
    year: Mapped[int] = mapped_column(Integer)
    kg_co2e_per_kwh: Mapped[float] = mapped_column(Float)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime)
    valid_to: Mapped[datetime] = mapped_column(UTCDateTime)
    source_url: Mapped[str] = mapped_column(Text)
    source_mode: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Tariff(Base):
    __tablename__ = "tariffs"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    rate_per_kwh: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Shanghai")
    bands: Mapped[list] = mapped_column(JSON, default=list)
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime)
    valid_to: Mapped[datetime] = mapped_column(UTCDateTime)
    source_url: Mapped[str] = mapped_column(Text)
    source_mode: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Strategy(Base):
    __tablename__ = "strategies"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"))
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    target_reduction_pct: Mapped[float] = mapped_column(Float)
    max_devices: Mapped[int] = mapped_column(Integer, default=20)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    mode: Mapped[str] = mapped_column(String(20), default="SHADOW")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    created_by: Mapped[str] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latest_evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    content: Mapped[dict] = mapped_column(JSON)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    created_by: Mapped[str] = mapped_column(String(100))
    source_mode: Mapped[str] = mapped_column(String(30))
    campus_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    parameters: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON)
    content: Mapped[dict] = mapped_column(JSON)


class Audit(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    campus_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(200), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    campus_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(200))
    at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class State(Base):
    __tablename__ = "system_state"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class AdapterObservation(Base):
    __tablename__ = "adapter_observations"
    __table_args__ = (UniqueConstraint("command_id", "device_id", "boot_epoch", "sequence", "status", name="uq_observation_identity"),)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    command_id: Mapped[str] = mapped_column(String(80), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    boot_epoch: Mapped[str] = mapped_column(String(80))
    sequence: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(60))
    source_mode: Mapped[str] = mapped_column(String(20))
    payload_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    matched: Mapped[bool] = mapped_column(Boolean, default=False)


class SimulatedOutput(Base):
    __tablename__ = "simulated_outputs"
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    output_present: Mapped[bool] = mapped_column(Boolean, default=True)
    desired_on: Mapped[bool] = mapped_column(Boolean, default=True)
    fault_latched: Mapped[bool] = mapped_column(Boolean, default=False)
    pending_command_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    requested_monotonic_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deadline_monotonic_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class ScheduleEvent(Base):
    __tablename__ = "schedule_events"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    campus_id: Mapped[str] = mapped_column(ForeignKey("campuses.id"), index=True)
    building_id: Mapped[str | None] = mapped_column(ForeignKey("buildings.id"), nullable=True, index=True)
    space_id: Mapped[str | None] = mapped_column(ForeignKey("spaces.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    planned_occupancy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    source: Mapped[str] = mapped_column(String(500))
    source_mode: Mapped[str] = mapped_column(String(20))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class CommissioningRecord(Base):
    __tablename__ = "commissioning_records"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    binding_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("device_bindings.id"))
    profile_id: Mapped[str] = mapped_column(String(47))
    load_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    load_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hardware_revision: Mapped[str] = mapped_column(String(80))
    safety_assessment_ref: Mapped[str] = mapped_column(String(1000))
    installation_approval_ref: Mapped[str] = mapped_column(String(1000))
    calibration_ref: Mapped[str] = mapped_column(String(1000))
    valid_until: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    released_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class ForecastHourRevision(Base):
    """Rebuildable append-only hourly import-power evidence, never billing energy."""
    __tablename__ = "forecast_hour_revisions"
    __table_args__ = (UniqueConstraint("device_id", "scope_key", "hour_end", "content_hash", name="uq_forecast_hour_content"),
        Index("ix_forecast_hour_lookup", "device_id", "hour_end", "available_at", "id"),)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(100), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    building_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    circuit_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_mode: Mapped[str] = mapped_column(String(20))
    scope_key: Mapped[str] = mapped_column(String(64))
    hour_end: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    computed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    source_watermark: Mapped[int] = mapped_column(BigInteger)
    content_hash: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON)


class ForecastDirtyHour(Base):
    __tablename__ = "forecast_dirty_hours"
    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    hour_end: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    source_watermark: Mapped[int] = mapped_column(BigInteger, default=0)
    queued_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    not_before: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class ForecastProjectionState(Base):
    __tablename__ = "forecast_projection_state"
    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    source_watermark: Mapped[int] = mapped_column(BigInteger, default=0)
    closed_revision_id: Mapped[int] = mapped_column(BigInteger, default=0)
    history_initialized: Mapped[bool] = mapped_column(Boolean, default=False)
    last_projected_hour: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class ForecastRun(Base):
    """Bounded internal derived-result cache; authorization scope is part of its key."""
    __tablename__ = "forecast_runs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True)
    campus_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    authorized_campus_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(100))
    parameters: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(100))
    input_revision: Mapped[str] = mapped_column(String(64))
    result_input_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    not_before: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    requested_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    lease_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class DeviceChannel(Base):
    """Declared capability, not evidence of state or authority to energize hardware."""
    __tablename__ = "device_channels"
    __table_args__ = (UniqueConstraint("device_id", "channel_key", name="uq_device_channel_key"),)
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    channel_key: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40))
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    freshness_seconds: Mapped[int] = mapped_column(Integer, default=120)
    controllable: Mapped[bool] = mapped_column(Boolean, default=False)
    introduced_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_control_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class HardwareEvent(Base):
    __tablename__ = "hardware_events"
    __table_args__ = (UniqueConstraint("device_id", "boot_id", "sequence", name="uq_hardware_event_identity"),)
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    boot_id: Mapped[str] = mapped_column(String(100))
    sequence: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)
    server_received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    source_mode: Mapped[str] = mapped_column(String(20))
    payload_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)


class ChannelObservation(Base):
    """Immutable observations, with historical binding and freshness captured at ingest."""
    __tablename__ = "channel_observations"
    __table_args__ = (UniqueConstraint("channel_id", "boot_epoch", "sample_seq", name="uq_channel_sample"),
        Index("ix_channel_observation_lookup", "channel_id", "observed_at", "id"),
        Index("ix_channel_observation_room_time", "space_id", "observed_at"))
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("device_channels.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("hardware_events.id"), nullable=True)
    telemetry_id: Mapped[int | None] = mapped_column(ForeignKey("telemetry.id"), nullable=True)
    boot_epoch: Mapped[str] = mapped_column(String(100))
    sample_seq: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    time_basis: Mapped[str] = mapped_column(String(50), default="device_observed")
    measured_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    measurement_age_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime)
    valid_until: Mapped[datetime] = mapped_column(UTCDateTime)
    value: Mapped[dict] = mapped_column(JSON)
    quality: Mapped[str] = mapped_column(String(20))
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    source_mode: Mapped[str] = mapped_column(String(20))
    source_version: Mapped[str] = mapped_column(String(100))
    payload_hash: Mapped[str] = mapped_column(String(64))
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    building_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    space_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    binding_id: Mapped[int | None] = mapped_column(ForeignKey("device_bindings.id"), nullable=True)


class RoomMode(Base):
    __tablename__ = "room_modes"
    __table_args__ = (Index("ix_room_mode_interval", "space_id", "starts_at", "ends_at"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class RoomPolicy(Base):
    __tablename__ = "room_policies"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    name: Mapped[str] = mapped_column(String(200))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    mode: Mapped[str] = mapped_column(String(20), default="SHADOW")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime)
    config: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class RoomEvaluation(Base):
    __tablename__ = "room_evaluations"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey("room_policies.id"), index=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    policy_revision: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str] = mapped_column(String(100))
    content: Mapped[dict] = mapped_column(JSON)
    command_ids: Mapped[list] = mapped_column(JSON, default=list)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class RoomAnomaly(Base):
    __tablename__ = "room_anomalies"
    __table_args__ = (UniqueConstraint("space_id", "type", "episode_start", name="uq_room_anomaly_episode"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    building_id: Mapped[str] = mapped_column(String(160), index=True)
    type: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    episode_start: Mapped[datetime] = mapped_column(UTCDateTime)
    last_observed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    source_mode: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[list] = mapped_column(JSON, default=list)


class ChannelAcknowledgement(Base):
    __tablename__ = "channel_acknowledgements"
    __table_args__ = (UniqueConstraint("device_id", "boot_id", "command_id", "sequence", "channel_number", "result", name="uq_channel_ack_identity"),)
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    boot_id: Mapped[str] = mapped_column(String(80))
    command_id: Mapped[str] = mapped_column(String(80), index=True)
    sequence: Mapped[str] = mapped_column(String(20))
    channel_number: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(40))
    matched: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    payload_hash: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON)


class ChannelHold(Base):
    __tablename__ = "channel_holds"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("device_channels.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    command_id: Mapped[str] = mapped_column(ForeignKey("commands.id"), unique=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    created_by: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text)


class SimulatedChannelOutput(Base):
    __tablename__ = "simulated_channel_outputs"
    channel_id: Mapped[str] = mapped_column(ForeignKey("device_channels.id"), primary_key=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), index=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    actuator_reported_on: Mapped[bool] = mapped_column(Boolean)
    last_command_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class RoomAnomalyRule(Base):
    __tablename__ = "room_anomaly_rules"
    space_id: Mapped[str] = mapped_column(ForeignKey("spaces.id"), primary_key=True)
    campus_id: Mapped[str] = mapped_column(String(160), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    config: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_by: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(Text)
