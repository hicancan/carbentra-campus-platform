import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Layers3 } from 'lucide-react'
import { queryString } from '../lib/api'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { DistributionResponse } from '../lib/classroom-types'
import { durationLabel, validTimestamp } from '../lib/classroom-display'
import { formatDate, formatNumber } from '../lib/format'
import { initialRange, PeriodFilter } from './Filters'
import { Badge, Card, CardHeader, EmptyState, ErrorState, Loading, Notice, SourceBadge } from './ui'
export default function ClassroomDistribution({
  buildingId,
  floorId,
  at,
}: {
  buildingId?: string
  floorId?: string
  at?: string
}) {
  const scope = useScope()
  const [range, setRange] = useState(() => {
    const end = validTimestamp(at || null)
    return end
      ? { end, start: new Date(Date.parse(end) - 86400000).toISOString() }
      : initialRange(24)
  })
  const groupBy = buildingId ? 'floor' : 'building'
  const query = useResource<DistributionResponse>(
    `/classrooms/distribution${queryString({ campus_id: scope.campusId, building_id: buildingId, floor_id: floorId, group_by: groupBy, ...range })}`,
    { interval: false },
  )
  return (
    <Card>
      <CardHeader
        title="区间状态分布"
        subtitle="把一段时间的空间状态汇总到楼栋与楼层，未知时长始终单独保留"
        actions={
          <div className="inline-gap">
            {query.data?.source_modes.map((mode) => (
              <SourceBadge key={mode} value={mode} />
            ))}
            <Badge>{query.data?.total_rooms ?? '—'} 间空间</Badge>
          </div>
        }
      />
      <div className="room-panel-body">
        <PeriodFilter value={range} onChange={setRange} />
        <Notice>
          时长按“房间 ×
          时间”汇总，不等于单个房间经过的时长。历史占用不反推人数，负载时长不直接换算实测节能。
        </Notice>
        {query.isLoading ? (
          <Loading label="正在还原区间空间分布…" />
        ) : query.error ? (
          <ErrorState error={query.error} retry={() => void query.refetch()} />
        ) : !query.data?.groups.length ? (
          <EmptyState title="此范围暂无空间分布" />
        ) : (
          <div className="room-distribution-list">
            {query.data.groups.map((group) => {
              const durations = group.durations?.occupancy
              const total = durations
                ? Object.values(durations).reduce((sum, value) => sum + value, 0)
                : 0
              return (
                <article key={group.id} className="room-distribution-row">
                  <div>
                    <strong>
                      <Layers3 size={15} />
                      {group.name}
                    </strong>
                    <small>
                      {group.room_count} 间 · 区间截止{' '}
                      {formatDate(query.data!.end || query.data!.at)}
                    </small>
                  </div>
                  <div>
                    <div
                      className="room-distribution-track"
                      aria-label={`${group.name}区间占用分布`}
                    >
                      {['occupied', 'vacant', 'unknown'].map((state) => (
                        <span
                          key={state}
                          className={`state-${state}`}
                          style={{
                            width: `${total > 0 ? ((durations?.[state] ?? 0) / total) * 100 : 0}%`,
                          }}
                          title={`${state} ${durationLabel(durations?.[state])}`}
                        />
                      ))}
                    </div>
                    <div className="room-state-legend">
                      <span>
                        <i className="room-state-dot occupied" />
                        有人 {durationLabel(durations?.occupied ?? 0)}
                      </span>
                      <span>
                        <i className="room-state-dot vacant" />
                        无人 {durationLabel(durations?.vacant ?? 0)}
                      </span>
                      <span>
                        <i className="room-state-dot unknown" />
                        未知 {durationLabel(durations?.unknown ?? 0)}
                      </span>
                    </div>
                  </div>
                  <div className="room-distribution-power">
                    <strong>
                      {formatNumber(group.observed_power_w)} <small>W</small>
                    </strong>
                    <small>截止快照 · {group.known_power_rooms} 间有证据</small>
                  </div>
                  <Link
                    className="text-link"
                    to={`/classrooms${queryString({ building: buildingId || group.id, floor: buildingId ? group.id : undefined, at: query.data!.end || query.data!.at })}`}
                  >
                    查看快照
                    <ArrowUpRight size={13} />
                  </Link>
                </article>
              )
            })}
          </div>
        )}
        {query.data && <p className="small text-muted section-space">{query.data.semantics}</p>}
      </div>
    </Card>
  )
}
