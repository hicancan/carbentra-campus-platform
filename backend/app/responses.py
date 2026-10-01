"""Explicit public API contracts. These DTOs never expose ORM/internal secret fields.

Request schemas live in schemas.py; response schemas are attached directly to routes,
validated at runtime, and exported to OpenAPI for the generated TypeScript client.
"""
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue
from .schemas import Mode, RateBand

Action = Literal["hold", "shed", "restore"]
SourceMode = Literal["SIMULATED", "REPLAYED", "REAL", "UNKNOWN", "MIXED"]
DispatchMode = Literal["IN_PROCESS", "VIRTUAL", "PHYSICAL", "DISABLED"]
CommandStatus = Literal["requested", "dispatched", "acknowledged", "verified", "acknowledged_unverified", "rejected", "failed", "timed_out"]


def _uint64(value: str) -> str:
    if int(value) > 2**64 - 1:
        raise ValueError("Counter exceeds uint64")
    return value


UInt64Decimal = Annotated[str, Field(strict=True, pattern=r"^(0|[1-9][0-9]{0,19})$", description="Exact unsigned 64-bit counter encoded as a canonical decimal string, never a JSON number", json_schema_extra={"x-maximum-value": "18446744073709551615"}), AfterValidator(_uint64)]


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, hide_input_in_errors=True)


T = TypeVar("T")


class Envelope(Output, Generic[T]):
    data: T
    meta: dict[str, JsonValue] | None = None


class ErrorDetails(Output):
    code: str
    message: str
    request_id: str
    details: JsonValue = None


class ErrorEnvelope(Output):
    error: ErrorDetails


class UserResponse(Output):
    id: str
    username: str
    display_name: str
    role: Literal["admin", "operator", "analyst", "viewer"]
    campus_ids: list[str] | None


class AuthResponse(Output):
    user: UserResponse
    csrf_token: str
    expires_at: datetime


class LogoutResponse(Output):
    logged_out: Literal[True]


class BindingResponse(Output):
    id: int
    device_id: str
    campus_id: str
    building_id: str | None
    floor_id: str | None
    space_id: str | None
    circuit_id: str | None
    valid_from: datetime
    valid_to: datetime | None
    reason: str
    actor: str


class TelemetryResponse(Output):
    id: int
    device_id: str
    boot_epoch: str
    sample_seq: UInt64Decimal
    correlation_command_id: str | None
    observed_at: datetime
    received_at: datetime
    time_source: Literal["authenticated", "simulated", "received_only", "reconstructed"]
    time_uncertainty_ms: float | None
    active_power_w: float | None
    voltage_v: float | None
    current_a: float | None
    energy_import_wh: float | None
    energy_export_wh: float | None
    board_temperature_c: float | None
    desired_on: bool | None
    output_present: bool | None
    fault_latched: bool | None
    quality: str
    quality_flags: list[str]
    source_mode: Mode
    source_version: str
    campus_id: str
    building_id: str | None
    space_id: str | None
    circuit_id: str | None
    binding_id: int | None


class DeviceResponse(Output):
    id: str
    name: str
    campus_id: str
    building_id: str | None
    floor_id: str | None
    space_id: str | None
    circuit_id: str | None
    kind: Literal["smart_plug", "meter", "sensor", "switch", "presence", "light"]
    source_mode: Mode
    dispatch_mode: DispatchMode
    physical_release_id: str | None
    commissioned: bool
    critical: bool
    allow_control: bool
    profile_id: str
    profile_revision: int
    capabilities: list[str]
    minimum_dwell_seconds: int
    last_seen_at: datetime | None
    provenance: dict[str, JsonValue]
    created_at: datetime
    updated_at: datetime
    status: Literal["online", "stale", "offline", "unknown"]
    latest: TelemetryResponse | None


class DeviceDetailResponse(DeviceResponse):
    binding_history: list[BindingResponse]
    command_count: int


class CommandHistoryResponse(Output):
    status: CommandStatus
    at: datetime
    reason: str
    evidence: dict[str, JsonValue]


class CommandResultResponse(Output):
    desired_on: bool
    output_present: bool
    voltage_absence_proven: Literal[False]
    simulated: bool
    observation_id: int
    observed_at: datetime
    boot_epoch: str
    sequence: UInt64Decimal


class CommandResponse(Output):
    channel_id: str | None
    channel_key: str
    product_family: Literal["PLUG", "SWITCH"]
    manual_hold_seconds: int | None
    id: str
    device_id: str
    campus_id: str
    building_id: str | None
    dispatch_mode: DispatchMode
    lease_id: str | None
    lease_expires_at: datetime | None
    delivery_receipt: dict[str, JsonValue] | None
    expected_boot_epoch: str | None
    action: Action
    sequence: UInt64Decimal
    status: CommandStatus
    reason: str
    source_mode: Mode
    issued_at: datetime
    expires_at: datetime
    created_by: str
    idempotency_key: str
    simulation_scenario: Literal["success", "reject", "fail", "timeout"]
    profile_revision: int
    history: list[CommandHistoryResponse]
    result: CommandResultResponse | None


class EnergySummaryResponse(Output):
    known_kwh: float | None
    export_kwh: float | None
    coverage_ratio: float | None
    quality: str
    period_start: datetime
    period_end: datetime
    device_count: int
    interval_count: int
    excluded_intervals: int
    source_mode: SourceMode
    warnings: list[str]
    method: str
    selected_device_ids: list[str]
    queried_sample_count: int


class EnergyBreakdownResponse(Output):
    id: str | None
    name: str
    known_kwh: float | None
    coverage_ratio: float
    quality: str
    source_mode: SourceMode
    device_count: int


class EnergyBalanceResponse(Output):
    parent_kwh: float | None
    children_kwh: float | None
    residual_kwh: float | None
    quality: str
    warnings: list[str]


class FactorResponse(Output):
    id: str
    name: str
    region: str
    year: int
    kg_co2e_per_kwh: float
    valid_from: datetime
    valid_to: datetime
    source_url: str
    source_mode: Mode
    version: int
    created_at: datetime


class TariffResponse(Output):
    id: str
    name: str
    currency: str
    rate_per_kwh: float
    timezone: str
    bands: list[RateBand]
    valid_from: datetime
    valid_to: datetime
    source_url: str
    source_mode: Mode
    version: int
    created_at: datetime


class CarbonSummaryResponse(EnergySummaryResponse):
    kg_co2e: float | None
    factor_id: str | None
    factor: FactorResponse | None
    factors_used: list[str]
    reduction_claim: Literal[False]


class PricingError(Output):
    code: str
    message: str
    details: JsonValue


class CostSummaryResponse(EnergySummaryResponse):
    amount: float | None
    currency: str | None
    tariff_id: str | None
    tariff: TariffResponse | None
    tariffs_used: list[str]
    pricing_mode: Literal["strict", "proportional_estimate"]
    boundary_estimated_intervals: int
    boundary_unresolved_intervals: int | None
    pricing_coverage_ratio: float | None
    charge_type: Literal["configured_energy_charge_estimate"]
    settlement_bill: Literal[False]
    excluded_components: list[str]
    allocation_method: str | None = None
    derived_price_windows: int | None = None
    pricing_error: PricingError | None = None


class ControlLoadResponse(Output):
    id: str | None
    name: str | None
    profile_id: str


class ControlReleaseResponse(Output):
    id: str
    status: str
    valid_until: datetime
    basis: Literal["operator_attestation"]


class ControlReasonsResponse(Output):
    hold: str | None
    shed: str | None
    restore: str | None


class ControlEligibilityResponse(Output):
    channel_id: str | None = None
    channel_key: str = "relay.1"
    product_family: Literal["PLUG", "SWITCH"] = "PLUG"
    verification_kind: Literal["independent_feedback", "actuator_reported_only"] = "independent_feedback"
    device_id: str
    profile_revision: int
    device_name: str
    source_mode: Mode
    dispatch_mode: DispatchMode
    eligible: bool
    allowed_actions: list[Action]
    reasons: ControlReasonsResponse
    physical_deployment_enabled: bool
    load: ControlLoadResponse
    release: ControlReleaseResponse | None
    checked_at: datetime
    server_rechecks_on_submission_and_lease: Literal[True]
    consequence: str


ForecastMethod = Literal["seasonal_naive", "ridge_regression"]


class ForecastPointResponse(Output):
    timestamp: datetime
    predicted_kw: float | None
    lower_kw: float | None
    upper_kw: float | None


class ForecastMetricsResponse(Output):
    mae_kw: float | None
    rmse_kw: float | None


class ForecastFoldResponse(Output):
    issued_at: datetime
    training_end: datetime | None
    target_start: datetime
    target_end: datetime
    sample_count: int


class ForecastModelsResponse(Output):
    seasonal_naive: ForecastMetricsResponse
    ridge_regression: ForecastMetricsResponse


class ForecastBacktestResponse(Output):
    start: datetime
    end: datetime
    sample_count: int
    expected_hours: int
    coverage_ratio: float | None
    models: ForecastModelsResponse
    folds: list[ForecastFoldResponse]


class ForecastBandResponse(Output):
    method: Literal["empirical_absolute_holdout_residual"]
    quantile: float
    radius_kw: float | None
    guaranteed: Literal[False]


class ForecastHoldoutResponse(ForecastBacktestResponse):
    selected_method: ForecastMethod
    baseline_improvement_pct: float | None
    band: ForecastBandResponse
    selection_used_holdout: Literal[False]
    protocol: str


class ForecastModelResponse(Output):
    version: str
    algorithm: Literal["standardized_ridge_regression"]
    trained: bool
    selected_method: ForecastMethod
    selection_reason: str
    feature_names: list[str]
    ridge_alpha: float
    training_sample_count: int
    minimum_history_hours: int
    validation: ForecastBacktestResponse | None
    calendar_timezone: str | None = None
    training_start: datetime | None = None
    prediction_origin: datetime | None = None
    bridge_hours: int | None = None
    id: str | None = None
    standardized_coefficients: dict[str, float] | None = None
    feature_centers: list[float] | None = None
    feature_scales: list[float] | None = None
    intercept_kw: float | None = None
    prediction_upper_cap_kw: float | None = None
    outlier_policy: str | None = None


class ForecastExcludedDeviceResponse(Output):
    device_id: str
    reasons: list[str]


class ForecastCoverageResponse(Output):
    selected_device_count: int
    eligible_device_count: int
    device_ratio: float | None
    selected_device_ids: list[str]
    eligible_device_ids: list[str]
    excluded_devices: list[ForecastExcludedDeviceResponse]
    complete_hours: int
    expected_hours: int
    hour_ratio: float | None
    scope_complete: bool
    source_records: int | None
    aggregated_rows: int | None = None
    excluded_records_and_intervals: dict[str, int]
    window_start: datetime
    window_end: datetime


class ForecastFreshnessResponse(Output):
    status: Literal["unknown", "fresh", "stale"]
    latest_sample_at: datetime | None
    oldest_cohort_sample_at: datetime | None
    latest_complete_hour: datetime | None
    age_seconds: float | None
    age_basis: str


class ForecastScopeResponse(Output):
    campus_id: str | None
    building_id: str | None


class ForecastProvenanceResponse(Output):
    source_modes: list[Mode]
    source_versions: list[str]
    training_data: SourceMode
    measurement: str
    aggregation: str
    reverse_power: str
    missing_values: str
    maximum_gap_seconds: dict[str, int]
    hour_coverage_required: float
    as_of_filters: list[str]
    query_row_budget: int
    query_row_budget_unit: str
    cache: str
    external_features: list[str]
    maximum_trailing_forecast_bridge_hours: int
    dispatch_performed: Literal[False]
    measured_savings_claim: Literal[False]
    real_campus_accuracy_claim: Literal[False]
    reader: str | None = None
    sql_dialect: str | None = None
    reverse_power_samples: int | None = None
    cohort_selection: str | None = None


class ForecastEvaluationResponse(Output):
    id: str | None
    status: Literal["queued", "running", "ready", "failed", "stale"]
    worker_status: Literal["queued", "running", "ready", "failed"]
    requested_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    input_revision: str | None
    result_input_revision: str | None
    projection_pending_hours: int
    retry_after_seconds: int
    error_code: str | None
    cached: bool


class ForecastResponse(Output):
    method: ForecastMethod
    trained_until: datetime | None
    generated_at: datetime
    scope: ForecastScopeResponse
    source_mode: SourceMode
    quality: Literal["insufficient_data", "model_estimate", "baseline_estimate", "partial_estimate"]
    mae_kw: float | None
    rmse_kw: float | None
    points: list[ForecastPointResponse]
    warnings: list[str]
    model: ForecastModelResponse
    holdout: ForecastHoldoutResponse | None
    coverage: ForecastCoverageResponse
    freshness: ForecastFreshnessResponse
    provenance: ForecastProvenanceResponse
    evaluation: ForecastEvaluationResponse | None = None
