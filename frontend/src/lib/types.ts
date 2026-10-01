import type { components } from './generated-api'
import type { SourceMode } from './api'
export interface Provenance {
  [key: string]: unknown
}
export interface Campus {
  id: string
  name: string
  timezone: string
  source: string
  source_mode: SourceMode
  provenance: Provenance
}
export interface Geometry {
  type: 'Polygon' | 'MultiPolygon'
  coordinates: number[][][] | number[][][][]
}
export interface Building {
  id: string
  campus_id: string
  name: string
  category: string
  floors: number | null
  area_m2: number | null
  centroid: [number, number] | null
  geometry: Geometry | null
  external_space_id?: string
  source: string
  source_mode: SourceMode
  provenance: Provenance
  device_count: number
}
export interface Floor {
  id: string
  building_id: string
  name: string
  level: number
  source: string
  provenance: Provenance
}
export interface Space {
  id: string
  campus_id: string
  building_id: string
  floor_id: string
  name: string
  kind: string
  source: string
  confidence: string
  provenance: Provenance
}
export type Telemetry = components['schemas']['TelemetryResponse']
export type Device = components['schemas']['DeviceResponse']
export type DeviceDetail = components['schemas']['DeviceDetailResponse']
export interface Alarm {
  id: string
  device_id: string
  campus_id: string
  building_id: string
  space_id: string | null
  type: string
  severity: string
  status: string
  title: string
  description: string
  source_mode: SourceMode
  created_at: string
  acknowledged_at: string | null
  resolved_at: string | null
  acknowledged_by: string | null
  resolved_by: string | null
  notes: { at: string; by: string; text: string }[]
}
export interface Overview {
  scope: { campus_id: string | null; building_id: string | null }
  source_mode: SourceMode
  generated_at: string
  freshness: { status: string; latest_sample_at: string | null; stale_after_seconds: number }
  counts: {
    buildings: number
    spaces: number
    devices: number
    online_devices: number
    stale_devices: number
    offline_devices: number
    unknown_devices?: number
    active_alarms: number
  }
  energy: {
    known_kwh: number | null
    coverage_ratio: number | null
    quality: string
    period_start: string
    period_end: string
    source_mode: SourceMode
  }
  power: { active_kw: number | null; quality: string; source_mode: SourceMode }
  carbon: { kg_co2e: number | null; factor_id: string | null; quality: string }
  cost: {
    amount: number | null
    currency: string | null
    tariff_id: string | null
    quality: string
  }
  trend: { timestamp: string; known_kwh: number | null; active_kw: number | null }[]
  buildings: {
    id: string
    name: string
    active_kw: number | null
    power_source_mode: SourceMode
    known_kwh: number | null
    device_count: number
    alarm_count: number
    quality: string
  }[]
  alarms: Alarm[]
  provenance: Provenance
}
export type EnergySummary = components['schemas']['EnergySummaryResponse']
export type EnergyBreakdown = components['schemas']['EnergyBreakdownResponse']
export type Balance = components['schemas']['EnergyBalanceResponse']
export type Factor = components['schemas']['FactorResponse']
export type Tariff = components['schemas']['TariffResponse']
export type CarbonSummary = components['schemas']['CarbonSummaryResponse']
export type CostSummary = components['schemas']['CostSummaryResponse']
export type Command = components['schemas']['CommandResponse']
export interface Evaluation {
  id: string
  strategy_id: string
  created_at: string
  mode: 'SHADOW'
  candidate_device_ids: string[]
  rejected_devices: { device_id: string; reason: string }[]
  estimated_reduction_kw: number | null
  baseline_kw: number | null
  quality: string
  source_mode: SourceMode
  dispatch_performed: false
}
export interface Strategy {
  id: string
  name: string
  description: string
  campus_id: string
  building_id: string | null
  target_reduction_pct: number
  max_devices: number
  status: string
  mode: 'SHADOW'
  created_at: string
  created_by: string
  approved_at: string | null
  approved_by: string | null
  latest_evaluation: Evaluation | null
}
export type Forecast = components['schemas']['ForecastResponse']
export interface Circuit {
  id: string
  campus_id: string
  building_id: string | null
  space_id: string | null
  parent_id: string | null
  name: string
  meter_device_id: string | null
  kind: string
  source_mode: SourceMode
}
export interface Topology {
  circuits: Circuit[]
  devices: Device[]
}
export interface Report {
  id: string
  name: string
  type: string
  created_at: string
  created_by: string
  source_mode: SourceMode
  parameters: Record<string, unknown>
  summary: Record<string, unknown>
  content?: unknown
}
export interface Audit {
  id: string
  actor: string
  action: string
  entity_type: string
  entity_id: string
  at: string
  details: Record<string, unknown>
}
export interface SystemStatus {
  mode: string
  version: string
  database: { status: string; dialect: string }
  worker: { status: string; last_tick_at: string }
  ingestion: { last_received_at: string; total_samples: number }
  physical_control: { enabled: boolean; reason: string }
  spatial: Record<string, unknown>
  simulation: { enabled: boolean; source_mode: SourceMode }
  warnings: string[]
}
