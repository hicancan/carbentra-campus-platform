import { describe, expect, it } from 'vitest'
import { clockMinute, minuteClock, parseRateBands } from './pricing'
import type { DraftRateBand } from './pricing'
const row = (start: string, end: string, rate = '0.6'): DraftRateBand => ({
  key: `${start}-${end}`,
  start,
  end,
  rate,
  label: '示例时段',
})
describe('explicit daily tariff bands', () => {
  it('supports 24:00 only as a closing boundary', () => {
    expect(clockMinute('24:00', true)).toBe(1440)
    expect(clockMinute('24:00')).toBeNull()
    expect(clockMinute('23:59')).toBe(1439)
    expect(minuteClock(1440)).toBe('24:00')
  })
  it('rejects malformed times and implicit overnight ranges', () => {
    expect(clockMinute('7:0')).toBeNull()
    expect(clockMinute('12:99')).toBeNull()
    expect(parseRateBands([row('22:00', '07:00')]).error).toContain('跨午夜')
  })
  it('allows adjacent bands and an uncovered base-rate interval', () => {
    const result = parseRateBands([row('10:00', '12:00', '0.8'), row('07:00', '10:00', '0.5')])
    expect(result.error).toBeNull()
    expect(result.bands.map((r) => r.start_minute)).toEqual([420, 600])
    expect(result.bands[0].end_minute).toBe(600)
  })
  it('rejects overlapping, blank and nonfinite rates', () => {
    expect(parseRateBands([row('07:00', '10:00'), row('09:00', '11:00')]).error).toContain('重叠')
    expect(parseRateBands([row('00:00', '24:00', '')]).error).not.toBeNull()
    expect(parseRateBands([row('00:00', '24:00', 'NaN')]).error).not.toBeNull()
    expect(parseRateBands([row('00:00', '24:00', 'Infinity')]).error).not.toBeNull()
  })
  it('retains legitimate zero pricing and flat-rate operation', () => {
    expect(parseRateBands([row('00:00', '24:00', '0')]).bands[0].rate_per_kwh).toBe(0)
    expect(parseRateBands([])).toEqual({ bands: [], error: null })
  })
})
