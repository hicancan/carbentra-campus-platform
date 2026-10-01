import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  ChevronRight,
  DoorOpen,
  Layers3,
  Lightbulb,
  Plus,
  PlugZap,
  Users,
} from 'lucide-react'
import { permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { ChannelSnapshot, RoomSnapshot, TimelineResponse } from '../lib/classroom-types'
import type { Building, Floor } from '../lib/types'
import { classroomCampusPath, classroomPath, validTimestamp } from '../lib/classroom-display'
import { displayBuildingName } from '../lib/registry-display'
import { formatDate, formatNumber, statusLabel } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionList,
  EmptyState,
  ErrorState,
  Loading,
  Notice,
  SourceBadge,
  StatusBadge,
  Tabs,
} from '../components/ui'
import { initialRange, PeriodFilter } from '../components/Filters'
import ClassroomTimeSelector from '../components/ClassroomTimeSelector'
import { ClassroomState } from '../components/ClassroomState'
import ClassroomDeviceCard from '../components/ClassroomDeviceCard'
import ClassroomTimeline from '../components/ClassroomTimeline'
import ClassroomMode from '../components/ClassroomMode'
import ClassroomPolicies from '../components/ClassroomPolicies'
import ClassroomAnomalies from '../components/ClassroomAnomalies'
import { ScheduleForm, ScheduleDetail } from './Schedules'
import type { Schedule } from './Schedules'

function RoomSchedules({ room, historical }: { room: RoomSnapshot; historical: boolean }) {
  const auth = useAuth()
  const [create, setCreate] = useState(false)
  const [selected, setSelected] = useState<Schedule | null>(null)
  const [editing, setEditing] = useState<Schedule | undefined>()
  const dayStart = new Date(room.at)
  dayStart.setHours(0, 0, 0, 0)
  const query = useResource<Schedule[]>(
    `/schedules${queryString({ space_id: room.id, start: dayStart.toISOString(), end: new Date(dayStart.getTime() + 7 * 86400000).toISOString(), limit: 100 })}`,
  )
  return (
    <Card>
      <CardHeader
        title="空间计划与检修"
        subtitle="教室范围 · 所选日期起 7 天的参考安排"
        actions={
          <Button
            variant="ghost"
            disabled={historical || !permissions.operate(auth.session?.user.role)}
            onClick={() => {
              setEditing(undefined)
              setCreate(true)
            }}
          >
            <Plus size={14} />
            登记
          </Button>
        }
      />
      <div className="room-panel-body">
        <Notice>课表不等于占用。计划未安排、人数为零或节假日，都不是断电授权。</Notice>
        {query.isLoading ? (
          <Loading compact />
        ) : query.error ? (
          <ErrorState error={query.error} compact />
        ) : !query.data?.length ? (
          <EmptyState
            title="此范围没有教室计划"
            description="实际占用仍以存在传感器的有效证据为准"
            icon={<CalendarDays size={25} />}
          />
        ) : (
          query.data.map((schedule) => (
            <button
              className="room-policy-item"
              style={{ width: '100%', textAlign: 'left', background: 'var(--surface)' }}
              key={schedule.id}
              onClick={() => setSelected(schedule)}
            >
              <h3>{schedule.title}</h3>
              <div className="inline-gap">
                <Badge tone={schedule.kind === 'maintenance' ? 'amber' : 'blue'}>
                  {statusLabel(schedule.kind)}
                </Badge>
                <StatusBadge value={schedule.status} />
                <SourceBadge value={schedule.source_mode} />
              </div>
              <p>
                {formatDate(schedule.starts_at)} → {formatDate(schedule.ends_at)}
              </p>
            </button>
          ))
        )}
        <Link
          className="text-link section-space"
          to={`/schedules${queryString({ building: room.building_id, space: room.id })}`}
        >
          查看完整计划工作台
          <ArrowUpRight size={13} />
        </Link>
      </div>
      {create && (
        <ScheduleForm
          schedule={editing}
          initialSpace={{ id: room.id, campus_id: room.campus_id, building_id: room.building_id }}
          onClose={() => setCreate(false)}
        />
      )}
      {selected && (
        <ScheduleDetail
          readOnly={historical}
          schedule={selected}
          onClose={() => setSelected(null)}
          onEdit={() => {
            setEditing(selected)
            setSelected(null)
            setCreate(true)
          }}
        />
      )}
    </Card>
  )
}
export default function Classroom() {
  const { spaceId = '' } = useParams()
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const at = validTimestamp(params.get('at')) || params.get('at') || undefined
  const tab = ['history', 'plans'].includes(params.get('tab') || '') ? params.get('tab')! : 'home'
  const [range, setRange] = useState(() => initialRange(24))
  const room = useResource<RoomSnapshot>(
    `/classrooms/${encodeURIComponent(spaceId)}${queryString({ at })}`,
    { enabled: !!spaceId, interval: at ? false : 15_000 },
  )
  const building = useResource<Building>(
    `/buildings/${encodeURIComponent(room.data?.building_id || '')}`,
    { enabled: !!room.data?.building_id },
  )
  const floors = useResource<Floor[]>(
    `/floors${queryString({ building_id: room.data?.building_id, limit: 500 })}`,
    { enabled: !!room.data?.building_id },
  )
  const timeline = useResource<TimelineResponse>(
    `/classrooms/${encodeURIComponent(spaceId)}/timeline${queryString(range)}`,
    { enabled: !!spaceId && tab === 'history', interval: at ? false : 30_000 },
  )
  useEffect(() => {
    const end = validTimestamp(at || null) || new Date().toISOString()
    setRange({ end, start: new Date(Date.parse(end) - 86400000).toISOString() })
  }, [spaceId, at])
  const grouped = useMemo(() => {
    const devices = new Map<string, ChannelSnapshot[]>()
    for (const channel of room.data?.channels || []) {
      if (!devices.has(channel.device_id)) devices.set(channel.device_id, [])
      devices.get(channel.device_id)!.push(channel)
    }
    return [...devices.entries()].sort(
      ([, a], [, b]) =>
        ['PRESENCE', 'SWITCH', 'PLUG', 'METER', 'SENSOR'].indexOf(a[0].product_family) -
        ['PRESENCE', 'SWITCH', 'PLUG', 'METER', 'SENSOR'].indexOf(b[0].product_family),
    )
  }, [room.data?.channels])
  const update = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes))
      value ? next.set(key, value) : next.delete(key)
    setParams(next)
  }
  const d = room.data
  if (room.isLoading) return <Loading label="正在打开教室工作台…" />
  if (room.error)
    return (
      <>
        <Link className="text-link" to="/classrooms">
          <ArrowLeft size={14} />
          返回教室工作台
        </Link>
        <ErrorState error={room.error} retry={() => void room.refetch()} />
      </>
    )
  if (!d)
    return (
      <EmptyState
        title="没有可访问的教室档案"
        action={<Link to="/classrooms">返回空间目录</Link>}
      />
    )
  return (
    <div className="classroom-workspace">
      <div>
        <nav className="room-navigation" aria-label="教室位置">
          <Link to="/classrooms">教室工作台</Link>
          <ChevronRight size={12} />
          <span>{scope.campuses.find((c) => c.id === d.campus_id)?.name || d.campus_id}</span>
          <ChevronRight size={12} />
          <Link to={`/classrooms${queryString({ building: d.building_id, at })}`}>
            {building.data ? displayBuildingName(building.data.name) : d.building_id}
          </Link>
          <ChevronRight size={12} />
          <span>{floors.data?.find((f) => f.id === d.floor_id)?.name || '楼层资料'}</span>
          <ChevronRight size={12} />
          <span>{d.name}</span>
        </nav>
        <div className="room-hero">
          <div>
            <div className="eyebrow">
              CLASSROOM · {at ? 'HISTORICAL SNAPSHOT' : 'LIVE WORKSPACE'}
            </div>
            <h1>{d.name}</h1>
            <div className="room-hero-status">
              <ClassroomState value={d.occupancy} prefix="占用" />
              <ClassroomState value={d.mode} />
              <SourceBadge value={d.source_mode} />
              <StatusBadge value={d.quality} />
            </div>
            <p>
              {d.kind} · {d.channels.length} 个已登记通道 · 快照 {formatDate(d.at)}
            </p>
            <Link className="text-link" to={classroomCampusPath(d, at)}>
              <Layers3 size={14} />
              定位楼层图
              <ArrowUpRight size={12} />
            </Link>
          </div>
          <div className="room-hero-power">
            <span>当前已知教室功率</span>
            <strong>
              {formatNumber(d.observed_power_w)}
              <small>W</small>
            </strong>
            <span>有效计量覆盖 {formatNumber(d.power_coverage * 100)}%</span>
            <span style={{ marginTop: 6 }}>非能耗 / 碳排结算总表</span>
          </div>
        </div>
      </div>
      <div className="classroom-toolbar">
        <Tabs
          active={tab}
          onChange={(value) => update({ tab: value === 'home' ? undefined : value })}
          items={[
            { id: 'home', label: '教室设备' },
            { id: 'history', label: '历史与证据' },
            { id: 'plans', label: '计划与策略' },
          ]}
        />
        <ClassroomTimeSelector at={at} onChange={(value) => update({ at: value })} />
      </div>
      {at && (
        <Notice>
          历史快照只读。设备控制、模式修改与策略评估已关闭；历史事件和观测按真实发生时间追溯。
          <Link className="text-link" to={classroomPath(d.id)}>
            返回当前工作台
          </Link>
        </Notice>
      )}
      {d.occupancy === 'unknown' && (
        <Notice title="实际占用未知">
          没有足够的有效存在证据，不能把“未知”解释为“无人”。计划人数{' '}
          {d.planned_occupancy == null ? '未知' : d.planned_occupancy}，不参与自动断电授权。
        </Notice>
      )}
      {tab === 'home' && (
        <>
          <div className="room-summary-grid room-overview-summary">
            {[
              { label: '实际占用', value: d.occupancy, icon: Users, note: '来自有效存在通道' },
              {
                label: '照明执行状态',
                value: d.lighting,
                icon: Lightbulb,
                note:
                  d.lighting_verification_kind === 'independent_feedback'
                    ? '独立输出反馈，非安全隔离证明'
                    : d.lighting_verification_kind === 'unknown'
                      ? '没有有效执行或反馈证据'
                      : '执行回报不等于灯具点亮验证',
              },
              { label: '插座输出反馈', value: d.sockets, icon: PlugZap, note: '反馈缺失保持未知' },
            ].map((metric) => (
              <Card className="room-summary" key={metric.label}>
                <div>
                  <span>{metric.label}</span>
                  <metric.icon size={17} />
                </div>
                <div style={{ margin: '17px 0' }}>
                  <ClassroomState value={metric.value} />
                </div>
                <p>{metric.note}</p>
              </Card>
            ))}
          </div>
          <section>
            <div className="room-section-heading">
              <div>
                <h2>教室设备与通道</h2>
                <p>按设备声明能力组织，只展示已登记、已绑定的真实接口</p>
              </div>
              <Link
                className="text-link"
                to={`/devices${queryString({ space: d.id, building: d.building_id })}`}
              >
                设备工作台
                <ArrowUpRight size={13} />
              </Link>
            </div>
            {grouped.length ? (
              <div className="room-device-grid">
                {grouped.map(([deviceId, channels]) => (
                  <ClassroomDeviceCard
                    key={`${deviceId}:${at || 'live'}`}
                    channels={channels}
                    historical={!!at}
                  />
                ))}
              </div>
            ) : (
              <Card>
                <EmptyState
                  title="此教室尚未绑定设备"
                  description="空间档案已可浏览；设备接入与安装核验后才会产生占用、功率和输出反馈。不生成占位传感读数。"
                  icon={<DoorOpen size={30} />}
                />
              </Card>
            )}
          </section>
          <div className="room-detail-columns">
            <div>
              <ClassroomMode key={`${d.id}:${at || 'live'}`} room={d} historical={!!at} />
              <RoomSchedules key={`${d.id}:${at || 'live'}`} room={d} historical={!!at} />
            </div>
            <div>
              <Card>
                <CardHeader title="状态为什么可信" subtitle="空间、设备与观测三层分别核验" />
                <div className="room-panel-body">
                  <DefinitionList
                    items={[
                      ['稳定空间身份', d.id],
                      ['观测来源', <SourceBadge value={d.source_mode} />],
                      ['观测质量', <StatusBadge value={d.quality} />],
                      ['功率覆盖', `${formatNumber(d.power_coverage * 100)}%`],
                      ['本时刻计划', d.scheduled_titles.join(' · ') || '没有匹配计划；不表示无人'],
                      ['活动异常', d.active_anomaly_ids.length],
                      ['控制授权', '房间摘要不授予执行权限'],
                    ]}
                  />
                </div>
              </Card>
              <ClassroomAnomalies readOnly={!!at} key={d.id} spaceId={d.id} compact />
            </div>
          </div>
        </>
      )}
      {tab === 'history' && (
        <>
          <div className="classroom-toolbar">
            <PeriodFilter value={range} onChange={setRange} />
            <Badge>区间按半开语义 [开始, 结束)</Badge>
          </div>
          <div className="room-detail-columns" style={{ marginTop: 0 }}>
            <div>
              {timeline.isLoading ? (
                <Loading label="正在还原教室历史…" />
              ) : timeline.error ? (
                <ErrorState error={timeline.error} retry={() => void timeline.refetch()} />
              ) : timeline.data ? (
                <ClassroomTimeline key={d.id} data={timeline.data} />
              ) : (
                <EmptyState title="历史暂不可用" />
              )}
            </div>
            <div>
              <ClassroomAnomalies readOnly={!!at} key={d.id} spaceId={d.id} />
              <Card>
                <CardHeader title="历史读取原则" />
                <div className="room-panel-body">
                  <Notice>
                    占用、输出反馈和功率按各自有效期回溯。缺测区间保留未知；时间范围内的计划不会补写为传感数据。
                  </Notice>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
      {tab === 'plans' && (
        <div className="room-detail-columns" style={{ marginTop: 0 }}>
          <div>
            <ClassroomPolicies key={`${d.id}:${at || 'live'}`} room={d} historical={!!at} />
            <RoomSchedules key={`${d.id}:${at || 'live'}`} room={d} historical={!!at} />
          </div>
          <div>
            <ClassroomMode key={`${d.id}:${at || 'live'}`} room={d} historical={!!at} />
            <Card>
              <CardHeader title="执行前的每一道检查" />
              <div className="room-panel-body">
                <ol className="small" style={{ lineHeight: 2.1, paddingLeft: 18 }}>
                  <li>明确的房间与通道身份</li>
                  <li>持续有效的无人观测</li>
                  <li>新鲜的功率与输出反馈</li>
                  <li>无检修、人工接管或故障闭锁</li>
                  <li>设备能力、权限、驻留时间与有效期</li>
                  <li>申请、应答、验证分别追踪</li>
                </ol>
                <Notice tone="warning">当前策略支持影子评估或模拟执行，不自动激活真实硬件。</Notice>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
