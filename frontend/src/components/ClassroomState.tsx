import { Badge } from './ui'
import { roomStateLabel, stateTone } from '../lib/classroom-display'
export function ClassroomState({ value, prefix }: { value?: string | null; prefix?: string }) {
  return (
    <Badge tone={stateTone(value)} dot>
      {prefix ? `${prefix} · ` : ''}
      {roomStateLabel(value)}
    </Badge>
  )
}
export function BooleanState({
  value,
  unavailable = false,
}: {
  value?: boolean | null
  unavailable?: boolean
}) {
  return (
    <ClassroomState
      value={unavailable ? '无反馈能力' : value == null ? 'unknown' : value ? 'on' : 'off'}
    />
  )
}
