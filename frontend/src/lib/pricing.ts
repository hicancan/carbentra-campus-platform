import type { components } from './generated-api'
export type CostAllocationMode = components['schemas']['CostSummaryResponse']['pricing_mode']
export type RateBand = components['schemas']['RateBand']
export interface DraftRateBand {
  key: string
  start: string
  end: string
  rate: string
  label: string
}
export function clockMinute(value: string, allowEnd = false): number | null {
  if (allowEnd && value === '24:00') return 1440
  if (!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)) return null
  const [hour, minute] = value.split(':').map(Number)
  return hour * 60 + minute
}
export function minuteClock(value: number): string {
  return Number.isInteger(value) && value >= 0 && value <= 1440
    ? `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
    : '—'
}
export function parseRateBands(rows: DraftRateBand[]): { bands: RateBand[]; error: string | null } {
  if (rows.length > 24) return { bands: [], error: '每日最多配置 24 个分时区间' }
  const bands: RateBand[] = []
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i],
      start = clockMinute(row.start),
      end = clockMinute(row.end, true),
      rate = Number(row.rate)
    if (start === null || end === null)
      return { bands: [], error: `第 ${i + 1} 行时间应为 HH:mm，截止可使用 24:00` }
    if (end <= start) return { bands: [], error: `第 ${i + 1} 行结束需晚于开始；跨午夜请拆成两行` }
    if (!row.rate.trim() || !Number.isFinite(rate) || rate < 0 || rate > 1000)
      return { bands: [], error: `第 ${i + 1} 行请填写 0–1000 的有效单价` }
    bands.push({
      start_minute: start,
      end_minute: end,
      rate_per_kwh: rate,
      label: row.label.trim(),
    })
  }
  const sorted = [...bands].sort((a, b) => a.start_minute - b.start_minute)
  if (sorted.some((band, index) => index > 0 && sorted[index - 1].end_minute > band.start_minute))
    return { bands: [], error: '分时区间不能重叠，交接端点可以相同' }
  return { bands: sorted, error: null }
}
