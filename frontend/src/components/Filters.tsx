import { useEffect } from 'react'
import { browserTimezone } from '../lib/timezone'
import { CalendarDays } from 'lucide-react'
import { useResource } from '../lib/hooks'
import { queryString } from '../lib/api'
import type { Building } from '../lib/types'
import { useScope } from '../lib/scope'
export function BuildingFilter({
  value,
  onChange,
  allLabel = '全部楼栋',
  campusId,
}: {
  value: string
  onChange: (value: string) => void
  allLabel?: string
  campusId?: string
}) {
  const scope = useScope()
  const buildings = useResource<Building[]>(
    `/buildings${queryString({ campus_id: campusId ?? scope.campusId, limit: 500 })}`,
  )
  useEffect(() => {
    if (value && buildings.data && !buildings.data.some((building) => building.id === value))
      onChange('')
  }, [value, buildings.data, onChange])
  return (
    <select
      aria-label="筛选楼栋"
      value={value}
      disabled={buildings.isLoading || !!buildings.error}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">
        {buildings.isLoading ? '正在读取楼栋…' : buildings.error ? '楼栋目录暂不可用' : allLabel}
      </option>
      {buildings.data?.map((b) => (
        <option key={b.id} value={b.id}>
          {b.name}
        </option>
      ))}
    </select>
  )
}
export type TimeRange = { start: string; end: string }
export function initialRange(hours = 24): TimeRange {
  return {
    start: new Date(Date.now() - hours * 3600000).toISOString(),
    end: new Date().toISOString(),
  }
}
export function PeriodFilter({
  value,
  onChange,
}: {
  value: TimeRange
  onChange: (range: TimeRange) => void
}) {
  const local = (date: string) => {
    const d = new Date(date)
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  }
  return (
    <div className="period-filter" title="时间按当前浏览器时区显示，发送 UTC 时间至平台">
      <CalendarDays size={15} />
      <input
        aria-label="统计开始时间"
        type="datetime-local"
        value={local(value.start)}
        max={local(value.end)}
        onChange={(e) =>
          e.target.value && onChange({ ...value, start: new Date(e.target.value).toISOString() })
        }
      />
      <span>至</span>
      <input
        aria-label="统计结束时间"
        type="datetime-local"
        value={local(value.end)}
        min={local(value.start)}
        onChange={(e) =>
          e.target.value && onChange({ ...value, end: new Date(e.target.value).toISOString() })
        }
      />
      <select
        aria-label="快速选择统计期"
        value=""
        onChange={(e) => e.target.value && onChange(initialRange(Number(e.target.value)))}
      >
        <option value="">快捷选择</option>
        <option value="24">近 24 小时</option>
        <option value="168">近 7 天</option>
        <option value="720">近 30 天</option>
      </select>
      <span className="timezone-hint">输入时区：{browserTimezone()}</span>
    </div>
  )
}
