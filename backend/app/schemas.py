from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

def resource_id(value: str) -> str:
    # These exact segments are normalized by URL resolvers even when encoded.
    # Run after Input's whitespace normalization and preserve ordinary dotted IDs.
    if value in {".", ".."}:
        raise ValueError("Resource ID cannot be a reserved URL dot segment")
    return value


ID = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9:_.-]+$",
    json_schema_extra={"not": {"enum": [".", ".."]}}), AfterValidator(resource_id)]
ShortID = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9:_.-]+$",
    json_schema_extra={"not": {"enum": [".", ".."]}}), AfterValidator(resource_id)]
Finite = Annotated[float, Field(allow_inf_nan=False, strict=True)]
Mode = Literal["SIMULATED", "REPLAYED", "REAL"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, hide_input_in_errors=True)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class BindingIn(Input):
    campus_id: ID
    building_id: ID | None = None
    floor_id: ID | None = None
    space_id: ID | None = None
    circuit_id: ID | None = None
    reason: str = Field(min_length=3, max_length=1000)


class DeviceIn(Input):
    id: ShortID
    name: str = Field(min_length=1, max_length=200)
    campus_id: ID
    building_id: ID | None = None
    floor_id: ID | None = None
    space_id: ID | None = None
    circuit_id: ID | None = None
    kind: Literal["smart_plug", "meter", "sensor", "switch", "presence", "light"] = "smart_plug"
    source_mode: Mode
    critical: StrictBool = True
    allow_control: StrictBool = False
    capabilities: list[Literal["metering", "temperature", "hold", "shed", "restore", "presence", "lighting", "illuminance", "co2", "relay_feedback"]] = Field(default_factory=lambda: ["metering"], max_length=11)


class DevicePatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    commissioned: StrictBool | None = None
    dispatch_mode: Literal["IN_PROCESS", "VIRTUAL", "DISABLED"] | None = None
    critical: StrictBool | None = None
    allow_control: StrictBool | None = None


class CircuitIn(Input):
    id: ID
    campus_id: ID
    building_id: ID | None = None
    space_id: ID | None = None
    parent_id: ID | None = None
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["main", "branch", "load"] = "branch"
    source_mode: Mode = "SIMULATED"


class TelemetryIn(Input):
    device_id: ID
    boot_epoch: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    sample_seq: str = Field(pattern=r"^(0|[1-9][0-9]{0,19})$")
    observed_at: datetime | None
    correlation_command_id: str | None = Field(default=None, max_length=80)
    time_source: Literal["authenticated", "simulated", "received_only", "reconstructed"]
    time_uncertainty_ms: Finite | None = Field(default=None, ge=0, le=86400000)
    active_power_w: Finite | None = Field(default=None, ge=-10000000, le=10000000)
    voltage_v: Finite | None = Field(default=None, ge=0, le=1000)
    current_a: Finite | None = Field(default=None, ge=0, le=50000)
    energy_import_wh: Finite | None = Field(default=None, ge=0, le=1e15)
    energy_export_wh: Finite | None = Field(default=None, ge=0, le=1e15)
    board_temperature_c: Finite | None = Field(default=None, ge=-80, le=250)
    desired_on: StrictBool | None = None
    output_present: StrictBool | None = None
    fault_latched: StrictBool | None = None
    valid: StrictBool
    calibrated: StrictBool
    energy_uncertain_intervals: int = Field(default=0, ge=0, le=2**32-1, strict=True)
    energy_status: Literal["known", "uncertain", "unknown"] = "unknown"
    counter_scope: Literal["bidirectional", "import_only"] = "bidirectional"
    source_mode: Mode
    source_version: str = Field(min_length=1, max_length=100)

    @field_validator("sample_seq")
    @classmethod
    def uint64(cls, value):
        if int(value) > 2**64 - 1:
            raise ValueError("sample_seq exceeds uint64")
        return value

    @field_validator("observed_at")
    @classmethod
    def aware(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("Timestamp must contain a UTC offset")
        return value.astimezone(timezone.utc) if value else value

    @model_validator(mode="after")
    def consistent(self):
        required = [self.active_power_w, self.voltage_v, self.current_a, self.energy_import_wh]
        if self.counter_scope == "bidirectional":
            required.append(self.energy_export_wh)
        elif self.energy_export_wh is not None:
            raise ValueError("Import-only measurement must not fabricate an export counter")
        if self.valid and any(x is None for x in required):
            raise ValueError("Valid samples require power, voltage, current and both Wh counters")
        if self.time_source in {"authenticated", "simulated", "reconstructed"} and self.observed_at is None:
            raise ValueError("Attributed sample time is required for this time source")
        if self.time_source == "simulated" and self.source_mode != "SIMULATED":
            raise ValueError("Simulated clock cannot label real or replayed measurements")
        return self


class IngestIn(Input):
    samples: list[TelemetryIn] = Field(min_length=1, max_length=500)


class PhysicalConfirmation(Input):
    device_id: ID
    release_id: str = Field(min_length=8,max_length=100)
    profile_revision: int = Field(ge=1,strict=True)
    load_id: str = Field(min_length=1, max_length=100)
    action: Literal["hold", "shed", "restore"]
    understands_mains_consequence: StrictBool


class CommandIn(Input):
    channel_id: ID | None = None
    manual_hold_seconds: int | None = Field(default=None, ge=60, le=86400, strict=True)
    device_id: ID
    action: Literal["hold", "shed", "restore"]
    expires_in_seconds: int = Field(default=30, ge=1, le=60, strict=True)
    reason: str = Field(min_length=3, max_length=1000)
    simulation_scenario: Literal["success", "reject", "fail", "timeout"] = "success"
    physical_confirmation: PhysicalConfirmation | None = None


class NoteIn(Input):
    note: str = Field(default="", max_length=2000)


class RequiredNote(Input):
    note: str = Field(min_length=3, max_length=2000)


class FactorIn(Input):
    id: ShortID
    name: str = Field(min_length=1, max_length=200)
    region: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=2000, le=2200, strict=True)
    kg_co2e_per_kwh: Finite = Field(ge=0, le=10)
    valid_from: datetime
    valid_to: datetime
    source_url: str = Field(min_length=1, max_length=2000, pattern=r"^https://")
    source_mode: Mode
    version: int = Field(ge=1, le=2**31-1, strict=True)

    @model_validator(mode="after")
    def interval(self):
        if self.valid_from.tzinfo is None or self.valid_to.tzinfo is None or self.valid_to <= self.valid_from:
            raise ValueError("A positive timezone-aware validity interval is required")
        return self


class RateBand(Input):
    start_minute: int = Field(ge=0, le=1439, strict=True)
    end_minute: int = Field(ge=1, le=1440, strict=True)
    rate_per_kwh: Finite = Field(ge=0, le=1000)
    label: str = Field(default="", max_length=80)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_minute <= self.start_minute:
            raise ValueError("Daily bands cannot wrap midnight; use two explicit bands")
        return self


class TariffIn(Input):
    id: ShortID
    name: str = Field(min_length=1, max_length=200)
    currency: str = Field(default="CNY", pattern=r"^[A-Z]{3}$")
    rate_per_kwh: Finite = Field(ge=0, le=1000)
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=80)
    bands: list[RateBand] = Field(default_factory=list, max_length=24)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("An installed IANA timezone is required")
        return value

    valid_from: datetime
    valid_to: datetime
    source_url: str = Field(min_length=1, max_length=2000, pattern=r"^https://")
    source_mode: Mode
    version: int = Field(ge=1, le=2**31-1, strict=True)

    @model_validator(mode="after")
    def interval(self):
        if self.valid_from.tzinfo is None or self.valid_to.tzinfo is None or self.valid_to <= self.valid_from:
            raise ValueError("A positive timezone-aware validity interval is required")
        ordered = sorted(self.bands, key=lambda band: band.start_minute)
        if any(left.end_minute > right.start_minute for left,right in zip(ordered,ordered[1:])):
            raise ValueError("Daily time-of-use rate bands must not overlap")
        self.bands = ordered
        return self


class StrategyIn(Input):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=3000)
    campus_id: ID
    building_id: ID | None = None
    target_reduction_pct: Finite = Field(gt=0, le=50)
    max_devices: int = Field(default=20, ge=1, le=500, strict=True)


class ReportIn(Input):
    name: str = Field(min_length=1, max_length=200)
    type: Literal["energy", "carbon", "cost", "operations"]
    campus_id: ID | None = None
    building_id: ID | None = None
    cost_allocation_mode: Literal["strict", "proportional_estimate"] = "strict"
    start: datetime | None = None
    end: datetime | None = None

    @field_validator("start", "end")
    @classmethod
    def aware(cls, value):
        if value and value.tzinfo is None:
            raise ValueError("Timestamp must contain a UTC offset")
        return value


class SettingsPatch(Input):
    stale_after_seconds: int | None = Field(default=None, ge=10, le=3600, strict=True)
    offline_after_seconds: int | None = Field(default=None, ge=30, le=86400, strict=True)


class DeliveryIn(Input):
    lease_id: str = Field(min_length=1, max_length=80)
    status: Literal["published", "failed", "expired"]
    reason: str = Field(default="", max_length=1000)


class DispatchIn(Input):
    evaluation_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=3, max_length=1000)


class UserIn(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, hide_input_in_errors=True)
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["admin", "operator", "analyst", "viewer"]
    campus_ids: list[ID] | None = Field(default_factory=list)
    password: str = Field(min_length=16, max_length=256)


class UserPatch(Input):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["admin", "operator", "analyst", "viewer"] | None = None
    campus_ids: list[ID] | None = None
    enabled: StrictBool | None = None


class PasswordIn(Input):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False, hide_input_in_errors=True)
    password: str = Field(min_length=16, max_length=256)


class CircuitPatch(Input):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_id: ID | None = None


class ScheduleIn(Input):
    campus_id: ID
    building_id: ID | None = None
    space_id: ID | None = None
    title: str = Field(min_length=1, max_length=200)
    kind: Literal["teaching", "holiday", "event", "maintenance"]
    starts_at: datetime
    ends_at: datetime
    planned_occupancy: int | None = Field(default=None, ge=0, le=100000, strict=True)
    source: str = Field(min_length=3, max_length=500)
    source_mode: Literal["SIMULATED", "REFERENCE"]

    @model_validator(mode="after")
    def window(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None or self.ends_at <= self.starts_at:
            raise ValueError("Schedule requires an ordered timezone-aware interval")
        if (self.ends_at-self.starts_at).total_seconds() > 366*86400:
            raise ValueError("A schedule interval cannot exceed one year")
        return self


class ScheduleImport(Input):
    events: list[ScheduleIn] = Field(min_length=1, max_length=500)


class CommissioningIn(Input):
    id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    profile_id: str = Field(min_length=1, max_length=47, pattern=r"^[A-Za-z0-9_-]+$")
    load_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9:_.-]+$")
    load_name: str = Field(min_length=1, max_length=200)
    hardware_revision: str = Field(min_length=1, max_length=80)
    safety_assessment_ref: str = Field(min_length=10, max_length=1000)
    installation_approval_ref: str = Field(min_length=10, max_length=1000)
    calibration_ref: str = Field(min_length=10, max_length=1000)
    valid_until: datetime

    @field_validator("valid_until")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Release expiration must be timezone-aware")
        return value


class ReleaseIn(RequiredNote):
    release_id: str = Field(min_length=8, max_length=100)
    operator_attested: StrictBool
    noncritical_load_attested: StrictBool


class ForecastRefreshIn(Input):
    campus_id: ID | None = None
    building_id: ID | None = None
    horizon_hours: int = Field(default=24,ge=1,le=72,strict=True)
