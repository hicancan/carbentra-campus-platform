import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, ClipboardList, Clock3 } from 'lucide-react'
import type { RoomInterval, TimelineResponse } from '../lib/classroom-types'
import { durationLabel, roomStateLabel, stateClass } from '../lib/classroom-display'
import { formatDate, formatNumber } from '../lib/format'
import { LineChart } from './charts'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionList,
  EmptyState,
  Modal,
  SourceBadge,
  StatusBadge,
} from './ui'
import { ClassroomState, BooleanState } from './ClassroomState'

export default function ClassroomTimeline({ data }: { data: TimelineResponse }) {
  const [visibleEvents, setVisibleEvents] = useState(50)
  const [selected, setSelected] = useState<RoomInterval | null>(null)
  const events = data.events || []
  const seconds = (Date.parse(data.end) - Date.parse(data.start)) / 1000
  const dimensions = [
    { key: 'occupancy' as const, name: '实际占用' },
    { key: 'lighting' as const, name: '照明执行' },
    { key: 'sockets' as const, name: '插座反馈' },
  ]
  const points = data.intervals.flatMap((interval) => [
    { timestamp: interval.start, value: interval.observed_power_w },
    { timestamp: interval.end, value: interval.observed_power_w },
  ])
  return (
    <>
      <Card>
        <CardHeader
          title="功率与状态历史"
          subtitle="按观测 / 知识有效期还原；过期断开，不延展最后已知状态"
          actions={
            <div className="inline-gap">
              {data.source_modes.map((mode) => (
                <SourceBadge key={mode} value={mode} />
              ))}
            </div>
          }
        />
        <div className="room-panel-body">
          <LineChart points={points} unit="W" label="已知教室功率" height={230} />
          <div className="room-intervals">
            {dimensions.map((dimension) => (
              <div className="room-interval-row" key={dimension.key}>
                <span>{dimension.name}</span>
                <div
                  className="room-interval-track"
                  role="group"
                  aria-label={`${dimension.name}历史时间线`}
                >
                  {data.intervals.map((interval, index) => (
                    <button
                      key={`${interval.start}-${index}`}
                      type="button"
                      className={`state-${stateClass(interval[dimension.key])}`}
                      style={{
                        width: `${seconds > 0 ? (interval.duration_seconds / seconds) * 100 : 0}%`,
                      }}
                      aria-label={`${formatDate(interval.start)} 至 ${formatDate(interval.end)} ${roomStateLabel(interval[dimension.key])}`}
                      title={`${formatDate(interval.start)} → ${formatDate(interval.end)} · ${roomStateLabel(interval[dimension.key])}`}
                      onClick={() => setSelected(interval)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="room-history-scale">
            <span>{formatDate(data.start)}</span>
            <span>{formatDate(data.end)}</span>
          </div>
          <div className="room-state-legend" style={{ margin: '16px 0' }}>
            <span>
              <i className="room-state-dot occupied" />
              有人 / 开启
            </span>
            <span>
              <i className="room-state-dot vacant" />
              无人 / 关闭
            </span>
            <span>
              <i className="room-state-dot mixed" />
              部分开启
            </span>
            <span>
              <i className="room-state-dot unknown" />
              未知 / 过期
            </span>
          </div>
          <div className="room-duration-grid">
            <div>
              <span>有效有人时长</span>
              <strong>{durationLabel(data.durations.occupancy.occupied ?? 0)}</strong>
            </div>
            <div>
              <span>占用未知时长</span>
              <strong>{durationLabel(data.durations.occupancy.unknown ?? 0)}</strong>
            </div>
            <div>
              <span>照明回报开启时长</span>
              <strong>{durationLabel(data.durations.lighting.on ?? 0)}</strong>
            </div>
            <div>
              <span>插座开启时长</span>
              <strong>{durationLabel(data.durations.sockets.on ?? 0)}</strong>
            </div>
            <div>
              <span>有功率证据</span>
              <strong>{durationLabel(data.durations.observed_power_seconds)}</strong>
            </div>
            <div>
              <span>功率未知时长</span>
              <strong>{durationLabel(data.durations.unknown_power_seconds)}</strong>
            </div>
          </div>
          <p className="small text-muted">
            {data.semantics} 没有设备 UTC
            的认证相对龄样本以平台知识边界进入历史，不伪造设备观测时刻。
          </p>
        </div>
      </Card>
      <Card>
        <CardHeader
          title="请求与反馈时间线"
          subtitle="命令历史与观测反馈逐条追溯；受理、应答与验证分别展示"
          actions={<Badge>{events.length ?? 0} 条</Badge>}
        />
        <div className="room-panel-body">
          {events.length ? (
            <div className="room-event-list">
              {events.slice(-visibleEvents).map((event, index) => (
                <div className="room-event" key={`${event.id}-${index}`}>
                  <ClipboardList size={16} />
                  <div>
                    <div className="inline-gap">
                      <strong>{event.description || event.type}</strong>
                      {event.status && <StatusBadge value={event.status} />}
                      <SourceBadge value={event.source_mode} />
                    </div>
                    <time>{formatDate(event.at)}</time>
                    <p>
                      {event.device_id || '空间事件'}
                      {event.channel_id ? ` · ${event.channel_id}` : ''}
                    </p>
                    {(event.requested_on != null ||
                      event.actuator_reported_on != null ||
                      event.output_present != null) && (
                      <div className="inline-gap section-space">
                        <span className="small">请求</span>
                        <BooleanState value={event.requested_on} />
                        <span className="small">执行回报</span>
                        <BooleanState value={event.actuator_reported_on} />
                        <span className="small">物理反馈</span>
                        <BooleanState value={event.output_present} />
                      </div>
                    )}
                    {event.command_id && (
                      <Link
                        className="text-link"
                        to={`/commands?command=${encodeURIComponent(event.command_id)}`}
                      >
                        命令详情
                        <ArrowUpRight size={12} />
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="此时间范围没有请求或反馈事件"
              description="没有事件不表示设备已关闭；请结合上方观测覆盖与有效期。"
              icon={<Clock3 size={26} />}
            />
          )}
          {events.length > visibleEvents && (
            <Button variant="ghost" onClick={() => setVisibleEvents((value) => value + 50)}>
              显示更早事件（当前 {Math.min(visibleEvents, events.length)} / {events.length}）
            </Button>
          )}
        </div>
      </Card>
      {selected && (
        <Modal title="历史区间证据" onClose={() => setSelected(null)}>
          <DefinitionList
            items={[
              ['区间开始（包含）', formatDate(selected.start)],
              ['区间结束（不包含）', formatDate(selected.end)],
              ['持续时间', durationLabel(selected.duration_seconds)],
              ['实际占用', <ClassroomState value={selected.occupancy} />],
              ['照明执行', <ClassroomState value={selected.lighting} />],
              [
                '照明依据',
                selected.lighting_verification_kind === 'independent_feedback'
                  ? '独立输出反馈'
                  : selected.lighting_verification_kind === 'unknown'
                    ? '无有效证据'
                    : '执行器回报或混合依据，未证明物理灯亮',
              ],
              ['插座反馈', <ClassroomState value={selected.sockets} />],
              ['观测功率', `${formatNumber(selected.observed_power_w)} W`],
              ['功率覆盖', `${formatNumber(selected.power_coverage * 100)}%`],
              ['来源', <SourceBadge value={selected.source_mode} />],
              ['质量', <StatusBadge value={selected.quality} />],
              [
                '原始观测 ID',
                selected.observation_ids.length
                  ? selected.observation_ids.join(' · ')
                  : '无有效证据',
              ],
            ]}
          />
        </Modal>
      )}
    </>
  )
}
