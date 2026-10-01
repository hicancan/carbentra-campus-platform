/** Application ontology v1. Schemas in ../schemas are authoritative at boundaries. */
export const IOT_SCHEMA_VERSION = 1 as const
export type ProductFamily = 'PLUG' | 'SWITCH' | 'PRESENCE'
export type SourceMode = 'REAL' | 'SIMULATED' | 'REPLAYED'
export type Quality = 'valid' | 'partial' | 'invalid' | 'stale' | 'unknown' | 'unavailable' | 'uncalibrated'
export type SourceProtocol = 'plug-wire-v2' | 'switch-mqtt-v1' | 'presence-ble-v2' | 'presence-gatt-v1' | 'virtual-v1'
export type ChannelId = 'relay.1' | 'relay.2' | 'relay.3' | 'meter.aggregate' | 'sensor.pir' | 'sensor.radar' | 'sensor.light' | 'sensor.buffer' | 'button.1' | 'button.2' | 'button.3' | 'device'
export type Capability = 'power.active' | 'voltage.rms' | 'current.rms' | 'energy.import' | 'energy.export' | 'relay.commanded' | 'relay.feedback' | 'presence.pir' | 'presence.radar' | 'illuminance.raw' | 'button.local' | 'buffer.voltage' | 'device.health' | 'control.mode' | 'control.manual_hold_until'
export type Unit = 'W' | 'V' | 'A' | 'Wh' | 'boolean' | 'raw_count' | 'mV' | 'status' | 'mode' | 'monotonic_ms'
export interface CapabilityDeclaration { capability: Capability; access: 'read' | 'write' | 'read_write'; unit: Unit; available: boolean }
export interface ChannelDescriptor { channel_id: ChannelId; label: string; capabilities: CapabilityDeclaration[] }
export interface DeviceDescriptor { schema_version: 1; device_id: string; product_family: ProductFamily; model: string; protocol: SourceProtocol; channels: ChannelDescriptor[] }
export interface Reading { capability: Capability; channel_id: ChannelId; value: number | boolean | string | null; unit: Unit; quality: Quality; details?: Record<string, unknown> }
export interface DeviceEvent {
  schema_version: 1; event_id: string; device_id: string; product_family: ProductFamily;
  boot_id: string; sequence: string; observed_at: string | null; received_at: string;
  monotonic_ms: number | null; source_mode: SourceMode; source_protocol: SourceProtocol;
  time_quality: 'authenticated' | 'device_clock' | 'gateway_received' | 'unknown';
  quality: Quality; readings: Reading[]; raw: Record<string, unknown>
}
export interface DeviceCommand {
  /** ASCII [A-Za-z0-9_-]: SWITCH 1–48, PLUG 1–47; enforce the JSON Schema at boundaries. */
  schema_version: 1; id: string; device_id: string; product_family: 'PLUG' | 'SWITCH';
  channel_id: 'relay.1' | 'relay.2' | 'relay.3'; capability: 'relay.commanded'; value: boolean;
  sequence: string; issued_at: string; expires_at: string; boot_id: string; manual_hold_seconds?: number;
  source_mode: 'REAL' | 'SIMULATED';
  authority: { kind: 'cloud' | 'local_rule' | 'manual'; lease_id: string; lease_expires_at: string; rule_id?: string; release_id?: string }
}
