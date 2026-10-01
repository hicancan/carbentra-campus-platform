import { queryString } from './api'

export const classroomPath = (id: string, at?: string | null) =>
  `/classrooms/${encodeURIComponent(id)}${queryString({ at })}`
export const classroomCampusPath = (
  room: { building_id: string; floor_id: string | null; id: string },
  at?: string | null,
) =>
  `/campus${queryString({ building: room.building_id, floor: room.floor_id, space: room.id, at })}`

export function localDateTime(value: string) {
  const date = new Date(value)
  return Number.isFinite(date.getTime())
    ? new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    : ''
}
export function validTimestamp(value: string | null): string | undefined {
  if (!value) return undefined
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? new Date(timestamp).toISOString() : undefined
}
export function durationLabel(seconds: number | null | undefined) {
  if (seconds == null || !Number.isFinite(seconds)) return '未知'
  if (seconds < 60) return `${Math.round(seconds)} 秒`
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours ? `${hours} 小时 ${minutes} 分` : `${minutes} 分钟`
}
export function roomStateLabel(state: string | null | undefined) {
  return (
    (
      {
        occupied: '有人',
        vacant: '无人',
        on: '开启',
        off: '关闭',
        mixed: '部分开启',
        unknown: '未知',
        manual: '人工接管',
        automatic: '自动策略',
        maintenance: '检修保护',
        fault: '故障闭锁',
      } as Record<string, string>
    )[state || ''] ||
    state ||
    '未知'
  )
}
export function stateTone(
  state: string | null | undefined,
): 'teal' | 'amber' | 'red' | 'blue' | 'muted' {
  if (['occupied', 'on', 'automatic'].includes(state || '')) return 'teal'
  if (['manual', 'mixed'].includes(state || '')) return 'blue'
  if (state === 'maintenance') return 'amber'
  if (state === 'fault') return 'red'
  return 'muted'
}
export function stateClass(state: string | null | undefined) {
  return [
    'occupied',
    'vacant',
    'on',
    'off',
    'mixed',
    'manual',
    'automatic',
    'maintenance',
    'fault',
  ].includes(state || '')
    ? state
    : 'unknown'
}
