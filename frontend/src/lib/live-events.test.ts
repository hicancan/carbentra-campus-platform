import { describe, expect, it } from 'vitest'
import { eventResourcePrefixes } from './live-events'
describe('scoped live invalidation', () => {
  it('refreshes telemetry-dependent state without refetching static assets or model training', () => {
    const prefixes = eventResourcePrefixes('telemetry.ingested')
    expect(prefixes).toContain('/overview')
    expect(prefixes).toContain('/devices')
    expect(prefixes).not.toContain('/assets/manifest')
    expect(prefixes).not.toContain('/forecasts')
    expect(prefixes).not.toContain('/users')
  })
  it('refreshes command evidence separately from telemetry throttling', () => {
    expect(eventResourcePrefixes('command.verified')).toContain('/commands')
    expect(eventResourcePrefixes('command.verified')).toContain('/audit')
  })
  it('refreshes room authority and evidence changes without geometry reload', () => {
    for (const type of [
      'room.mode_changed',
      'room_policy.disabled',
      'room_evaluation.dispatched',
      'room_anomaly.opened',
      'channel.ingested',
    ]) {
      expect(eventResourcePrefixes(type)).toContain('/classrooms')
      expect(eventResourcePrefixes(type)).not.toContain('/assets')
    }
  })
  it('ignores unrecognized events without broad data refresh', () => {
    expect(eventResourcePrefixes('untrusted.command')).toEqual([])
  })
})
