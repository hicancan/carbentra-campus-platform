import { describe, expect, it } from 'vitest'
import {
  classroomCampusPath,
  classroomPath,
  durationLabel,
  localDateTime,
  roomStateLabel,
  stateClass,
  validTimestamp,
} from './classroom-display'
import { channelMeasurement } from '../components/ClassroomDeviceCard'
import { channelFixture } from '../test-fixtures/classroom'
describe('classroom evidence display boundaries', () => {
  it('uses exact stable space identity and preserves historical timestamp', () => {
    const path = classroomPath('space:test:101', '2026-10-01T03:00:00Z')
    expect(path).toContain('/classrooms/space%3Atest%3A101')
    expect(new URLSearchParams(path.split('?')[1]).get('at')).toBe('2026-10-01T03:00:00Z')
    expect(
      classroomCampusPath({ id: 'space:test:101', building_id: 'b', floor_id: null }),
    ).not.toContain('floor=')
  })
  it('rejects malformed timestamps and preserves zero duration', () => {
    expect(validTimestamp('not-a-date')).toBeUndefined()
    expect(validTimestamp(null)).toBeUndefined()
    expect(localDateTime('broken')).toBe('')
    expect(durationLabel(null)).toBe('未知')
    expect(durationLabel(0)).toBe('0 秒')
    expect(durationLabel(7199)).toBe('2 小时 0 分')
  })
  it('never turns unsupported states into off or vacant', () => {
    expect(roomStateLabel(null)).toBe('未知')
    expect(stateClass('unverified')).toBe('unknown')
  })
  it('does not display stale power as current even if the response contains a number', () => {
    expect(
      channelMeasurement(
        channelFixture({
          kind: 'power',
          unit: 'W',
          quality: 'stale',
          value: { active_power_w: 300 },
        }),
      ),
    ).toBe('未知')
    expect(
      channelMeasurement(
        channelFixture({ kind: 'power', unit: 'W', value: { active_power_w: 0 } }),
      ),
    ).toBe('0 W')
  })
  it('preserves raw light units instead of calling them lux', () => {
    expect(
      channelMeasurement(
        channelFixture({ kind: 'illuminance', unit: 'raw_count', value: { number: 1200 } }),
      ),
    ).toBe('1,200 原始计数')
  })
  it('planned absence cannot invent sensor vacancy', () => {
    expect(
      channelMeasurement(channelFixture({ kind: 'presence', value: { occupancy: 'unknown' } })),
    ).toBe('未知')
  })
})
