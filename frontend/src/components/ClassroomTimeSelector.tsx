import { Clock3, Radio } from 'lucide-react'
import { browserTimezone } from '../lib/timezone'
import { localDateTime, validTimestamp } from '../lib/classroom-display'
import { Button } from './ui'

export default function ClassroomTimeSelector({
  at,
  onChange,
}: {
  at?: string
  onChange: (at?: string) => void
}) {
  return (
    <div className="classroom-time-selector">
      <span className={`snapshot-indicator ${at ? 'historical' : ''}`}>
        <span />
        {at ? '历史快照' : '当前状态'}
      </span>
      <label>
        <Clock3 size={15} />
        <span className="sr-only">选择空间状态时间</span>
        <input
          type="datetime-local"
          aria-label="选择空间状态时间"
          value={at ? localDateTime(at) : ''}
          max={localDateTime(new Date().toISOString())}
          onChange={(event) => onChange(validTimestamp(event.target.value))}
        />
      </label>
      {at && (
        <Button variant="ghost" onClick={() => onChange(undefined)}>
          <Radio size={14} />
          返回当前
        </Button>
      )}
      <small>{browserTimezone()}</small>
    </div>
  )
}
