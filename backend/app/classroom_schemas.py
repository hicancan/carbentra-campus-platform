"""Public classroom contracts. Unknown is a first-class state, never vacant/off/zero."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import Field, StrictBool, field_validator, model_validator
from .schemas import Input, ID, ShortID, Finite, Mode, CommandIn
from .responses import Output, SourceMode, CommandResponse

ChannelKind = Literal["presence", "lighting", "socket", "power", "temperature", "illuminance", "co2"]
Occupancy = Literal["occupied", "vacant", "unknown"]
LoadState = Literal["on", "off", "mixed", "unknown"]
OperationMode = Literal["manual", "automatic", "maintenance", "fault"]

class ChannelIn(Input):
    id: ID
    device_id: ShortID
    channel_key: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    name: str = Field(min_length=1, max_length=200)
    kind: ChannelKind
    capabilities: list[str] = Field(min_length=1, max_length=16)
    unit: Literal["W", "Wh", "degC", "lux", "raw_count", "ppm"] | None = None
    freshness_seconds: int = Field(default=120, ge=5, le=3600, strict=True)
    controllable: StrictBool = False

class ChannelValue(Input):
    occupancy: Occupancy | None = None
    actuator_reported_on: StrictBool | None = None
    output_present: StrictBool | None = None
    desired_on: StrictBool | None = None
    active_power_w: Finite | None = Field(default=None, ge=-10000000, le=10000000)
    number: Finite | None = None
    fault_latched: StrictBool | None = None

class ChannelSample(Input):
    channel_id: ID
    boot_epoch: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    sample_seq: str = Field(pattern=r"^(0|[1-9][0-9]{0,19})$")
    observed_at: datetime | None
    time_source: Literal["authenticated", "simulated", "device_clock", "received_only"]
    time_uncertainty_ms: Finite | None = Field(default=None, ge=0, le=86400000)
    source_mode: Mode
    source_version: str = Field(min_length=1, max_length=100)
    valid: StrictBool
    value: ChannelValue
    @field_validator("sample_seq")
    @classmethod
    def uint64(cls, v):
        if int(v) > 2**64 - 1:
            raise ValueError("Sequence exceeds uint64")
        return v
    @model_validator(mode="after")
    def times(self):
        if self.observed_at and self.observed_at.tzinfo is None:
            raise ValueError("Timestamp requires UTC offset")
        if self.observed_at is not None:
            self.observed_at = self.observed_at.astimezone(timezone.utc)
        if self.time_source != "received_only" and self.observed_at is None:
            raise ValueError("Observed timestamp required")
        if self.time_source == "simulated" and self.source_mode != "SIMULATED":
            raise ValueError("Simulated clock requires SIMULATED source")
        return self

class ChannelBatch(Input):
    samples: list[ChannelSample] = Field(min_length=1, max_length=500)

class ModeIn(Input):
    mode: OperationMode
    duration_seconds: int | None = Field(default=None, ge=60, le=86400, strict=True)
    reason: str = Field(min_length=3, max_length=1000)
    @model_validator(mode="after")
    def bounded(self):
        if self.mode == "manual" and self.duration_seconds is None:
            raise ValueError("Manual override requires bounded duration (60–86400 seconds)")
        return self

class PolicyIn(Input):
    name: str = Field(min_length=1, max_length=200)
    mode: Literal["SHADOW", "SIMULATED"] = "SHADOW"
    enabled: StrictBool = True
    starts_at: datetime
    ends_at: datetime
    channel_ids: list[ID] = Field(min_length=1, max_length=20)
    action: Literal["shed"] = "shed"
    vacant_for_seconds: int = Field(default=300, ge=30, le=7200, strict=True)
    minimum_power_w: Finite = Field(default=5.0, ge=0, le=1000000)
    max_commands: int = Field(default=5, ge=1, le=20, strict=True)
    reason: str = Field(min_length=3, max_length=1000)
    @model_validator(mode="after")
    def window(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Policy timestamps require UTC offsets")
        if not 0 < (self.ends_at-self.starts_at).total_seconds() <= 7*86400:
            raise ValueError("Policy window must be positive and at most seven days")
        if len(set(self.channel_ids)) != len(self.channel_ids):
            raise ValueError("Channel targets must be unique")
        return self

class ChannelSnapshot(Output):
    effective_at: datetime | None
    time_basis: Literal["device_observed", "authenticated_relative_receipt", "received_only", "unknown"]
    measurement_age_ms: float | None
    channel_id: str
    channel_key: str
    device_id: str
    name: str
    kind: ChannelKind
    product_family: Literal["PLUG", "SWITCH", "PRESENCE", "METER", "SENSOR"]
    capabilities: list[str]
    unit: str | None
    value: ChannelValue | None
    quality: Literal["good", "uncertain", "invalid", "stale", "unknown"]
    quality_flags: list[str]
    observed_at: datetime | None
    received_at: datetime | None
    valid_until: datetime | None
    observation_id: int | None
    binding_id: int | None
    source_mode: SourceMode
    source_version: str | None
    online_status: Literal["online", "stale", "offline", "unknown"]
    controllable: bool
    feedback_supported: bool
    verification_kind: Literal["independent_feedback", "actuator_reported_only", "not_applicable"]
    manual_hold_until: datetime | None
    manual_hold_scope: Literal["backend_edge"] | None
    allowed_actions: list[Literal["hold", "shed", "restore"]]
    block_reason: str | None

class RoomSnapshot(Output):
    id: str
    name: str
    kind: str
    campus_id: str
    building_id: str
    floor_id: str | None
    at: datetime
    occupancy: Occupancy
    lighting: LoadState
    lighting_verification_kind: Literal["independent_feedback", "actuator_reported_only", "mixed", "unknown"]
    sockets: LoadState
    observed_power_w: float | None
    power_coverage: float
    mode: OperationMode
    mode_expires_at: datetime | None
    mode_reason: str | None
    source_mode: SourceMode
    quality: Literal["good", "partial", "unknown"]
    channels: list[ChannelSnapshot]
    active_anomaly_ids: list[str]
    planned_occupancy: int | None
    scheduled_titles: list[str]
    control_authorization: Literal[False] = False

class RoomInterval(Output):
    start: datetime
    end: datetime
    duration_seconds: float
    occupancy: Occupancy
    lighting: LoadState
    lighting_verification_kind: Literal["independent_feedback", "actuator_reported_only", "mixed", "unknown"]
    sockets: LoadState
    observed_power_w: float | None
    power_coverage: float
    mode: OperationMode
    source_mode: SourceMode
    quality: Literal["good", "partial", "unknown"]
    observation_ids: list[int]

class StateDurations(Output):
    occupancy: dict[str, float]
    lighting: dict[str, float]
    sockets: dict[str, float]
    mode: dict[str, float]
    observed_power_seconds: float
    unknown_power_seconds: float

class TimelineEvent(Output):
    actuator_reported_on: bool | None = None
    verification_kind: str | None = None
    id: str
    at: datetime
    type: str
    device_id: str | None
    channel_id: str | None
    command_id: str | None
    status: str | None
    requested_on: bool | None
    output_present: bool | None
    source_mode: SourceMode
    description: str

class TimelineResponse(Output):
    room_id: str
    start: datetime
    end: datetime
    intervals: list[RoomInterval]
    events: list[TimelineEvent] = Field(default_factory=list)
    durations: StateDurations
    source_modes: list[str]
    semantics: str

class DistributionGroup(Output):
    source_modes: list[str]
    id: str
    name: str
    room_count: int
    occupancy: dict[str, int]
    lighting: dict[str, int]
    sockets: dict[str, int]
    observed_power_w: float | None
    known_power_rooms: int
    durations: StateDurations | None = None

class DistributionResponse(Output):
    source_modes: list[str]
    at: datetime
    start: datetime | None
    end: datetime | None
    group_by: Literal["campus", "building", "floor"]
    total_rooms: int
    groups: list[DistributionGroup]
    semantics: str

class ModeResponse(Output):
    id: str
    space_id: str
    campus_id: str
    mode: OperationMode
    starts_at: datetime
    ends_at: datetime | None
    reason: str
    created_by: str
    created_at: datetime

class PolicyConfig(Output):
    channel_ids: list[str]
    action: Literal["shed"]
    vacant_for_seconds: int
    minimum_power_w: float
    max_commands: int
    reason: str

class PolicyResponse(Output):
    id: str
    space_id: str
    campus_id: str
    name: str
    revision: int
    mode: Literal["SHADOW", "SIMULATED"]
    enabled: bool
    starts_at: datetime
    ends_at: datetime
    config: PolicyConfig
    created_by: str
    created_at: datetime

class EvaluationTarget(Output):
    aggregate_power_w: float | None = None
    channel_id: str
    device_id: str | None
    eligible: bool
    blocked_by: list[str]
    observed_power_w: float | None

class EvaluationContent(Output):
    occupancy: Occupancy
    vacancy_seconds: float
    mode: OperationMode
    targets: list[EvaluationTarget]
    eligible_count: int
    modeled_reduction_w: float | None
    savings_claim: Literal[False] = False
    source_mode: Literal["SIMULATED", "MIXED", "UNKNOWN"]
    explanation: str

class EvaluationResponse(Output):
    id: str
    policy_id: str
    space_id: str
    campus_id: str
    at: datetime
    policy_revision: int
    created_by: str
    content: EvaluationContent
    command_ids: list[str]
    dispatched_at: datetime | None
    commands: list[CommandResponse]
    verified_count: int
    unverified_count: int
    failed_count: int
    pending_count: int
    execution_status: Literal["shadow", "not_dispatched", "pending", "verified", "acknowledged_unverified", "partial", "failed"]

class AnomalyEvidence(Output):
    rule_revision: int = 0
    clear_threshold_w: float | None = None
    rule_version: str
    evaluated_at: datetime
    persistence_seconds: float
    required_persistence_seconds: int
    observed_power_w: float | None
    threshold_w: float | None
    baseline_median_w: float | None
    baseline_mad_w: float | None
    baseline_sample_count: int
    baseline_status: Literal["sufficient", "insufficient", "not_applicable"]
    baseline_condition: str
    observation_ids: list[int]
    quality_flags: list[str]
    explanation: str

class AnomalyNote(Output):
    at: datetime
    by: str
    action: str
    text: str

class AnomalyResponse(Output):
    id: str
    space_id: str
    campus_id: str
    building_id: str
    type: str
    severity: str
    status: Literal["open", "acknowledged", "resolved"]
    episode_start: datetime
    last_observed_at: datetime
    resolved_at: datetime | None
    source_mode: SourceMode
    evidence: AnomalyEvidence
    notes: list[AnomalyNote]

class EvaluateAnomaliesIn(Input):
    campus_id: ID | None = None
    building_id: ID | None = None
    space_id: ID | None = None


class ChannelDefinition(ChannelIn):
    introduced_at: datetime | None = None
    last_control_at: datetime | None = None
    campus_id: str
    created_at: datetime


class ChannelReceipt(Output):
    channel_id: str
    observation_id: int
    status: Literal["stored", "duplicate"]
    quality: str


class ChannelBatchReceipt(Output):
    durable: Literal[True]
    receipts: list[ChannelReceipt]


class IoTEventReceipt(Output):
    durable: Literal[True]
    event_id: str
    device_id: str
    boot_id: str
    sequence: str
    status: Literal["stored", "duplicate"]
    server_received_at: datetime


class IoTAckReceipt(Output):
    durable: Literal[True]
    device_id: str
    id: str
    seq: str
    channel: int
    status: Literal["stored", "duplicate"]
    physical_verification: Literal[False]


class PolicyPatch(Input):
    enabled: StrictBool
    reason: str = Field(min_length=3, max_length=1000)


class AnomalyRuleConfig(Input):
    enabled: StrictBool = True
    vacant_power_threshold_w: Finite = Field(default=50., ge=0, le=10000000)
    vacant_persistence_seconds: int = Field(default=300, ge=30, le=7200, strict=True)
    data_quality_persistence_seconds: int = Field(default=300, ge=30, le=86400, strict=True)
    high_load_minimum_w: Finite = Field(default=100., ge=0, le=10000000)
    baseline_multiplier: Finite = Field(default=1.8, ge=1, le=10)
    baseline_mad_multiplier: Finite = Field(default=3., ge=0, le=20)
    high_load_persistence_seconds: int = Field(default=600, ge=30, le=7200, strict=True)
    clear_hysteresis_ratio: Finite = Field(default=.1, ge=0, le=.9)


class AnomalyRulePatch(AnomalyRuleConfig):
    expected_revision: int = Field(ge=0, strict=True)
    reason: str = Field(min_length=3, max_length=1000)


class AnomalyRuleResponse(Output):
    space_id: str
    revision: int
    config: AnomalyRuleConfig
    updated_at: datetime | None
    updated_by: str | None
    reason: str
    defaults_are_engineering_assumptions: Literal[True] = True


class AnomalyRuleBatchPatch(AnomalyRuleConfig):
    room_ids: list[ID] = Field(min_length=1, max_length=500)
    expected_revisions: dict[str, int]
    reason: str = Field(min_length=3, max_length=1000)
    @model_validator(mode="after")
    def exact_revision_scope(self):
        if len(set(self.room_ids)) != len(self.room_ids) or set(self.room_ids) != set(self.expected_revisions):
            raise ValueError("One explicit expected revision is required for each unique room")
        if any(type(v) is not int or v < 0 for v in self.expected_revisions.values()):
            raise ValueError("Revisions must be nonnegative integers")
        return self
