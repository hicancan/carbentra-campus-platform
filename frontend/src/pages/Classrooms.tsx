import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ArrowUpRight,
  Building2,
  DoorOpen,
  Layers3,
  Lightbulb,
  Search,
  ShieldQuestion,
  Users,
  Zap,
} from 'lucide-react'
import { useCollection, useResource } from '../lib/hooks'
import { queryString } from '../lib/api'
import { useScope } from '../lib/scope'
import { formatDate, formatNumber } from '../lib/format'
import { displayBuildingName } from '../lib/registry-display'
import { classroomPath, roomStateLabel, stateClass, validTimestamp } from '../lib/classroom-display'
import type { RoomSnapshot } from '../lib/classroom-types'
import type { Building, Floor } from '../lib/types'
import {
  Badge,
  Card,
  CardHeader,
  SourceBadge,
  EmptyState,
  ErrorState,
  Loading,
  Notice,
  PageHeader,
  Pagination,
  Tabs,
} from '../components/ui'
import { BuildingFilter } from '../components/Filters'
import ClassroomTimeSelector from '../components/ClassroomTimeSelector'
import ClassroomDistribution from '../components/ClassroomDistribution'

type Dimension = 'occupancy' | 'lighting' | 'sockets' | 'mode'
const dimensions = [
  { id: 'occupancy', label: '实际占用' },
  { id: 'lighting', label: '照明执行状态' },
  { id: 'sockets', label: '插座反馈' },
  { id: 'mode', label: '运行模式' },
]
export default function Classrooms() {
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const building = params.get('building') || ''
  const floor = params.get('floor') || ''
  const at = validTimestamp(params.get('at')) || params.get('at') || undefined
  const [search, setSearch] = useState('')
  const [dimension, setDimension] = useState<Dimension>('occupancy')
  const [state, setState] = useState('')
  const [distribution, setDistribution] = useState(false)
  const [offset, setOffset] = useState(0)
  const pageSize = 96
  useEffect(() => setOffset(0), [scope.campusId, building, floor, at, search, state, dimension])
  const rooms = useCollection<RoomSnapshot>(
    `/classrooms${queryString({ campus_id: scope.campusId, building_id: building, floor_id: floor, at, limit: 2000 })}`,
    { interval: at ? false : 30_000 },
  )
  const buildings = useResource<Building[]>(
    `/buildings${queryString({ campus_id: scope.campusId, limit: 500 })}`,
  )
  const floors = useResource<Floor[]>(
    `/floors${queryString({ building_id: building, limit: 500 })}`,
    { interval: false },
  )
  const update = (changes: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes))
      value ? next.set(key, value) : next.delete(key)
    setParams(next)
  }
  const rows = rooms.data?.data || []
  const total = Number(rooms.data?.meta?.total ?? rows.length)
  const names = useMemo(
    () => new Map(buildings.data?.map((b) => [b.id, displayBuildingName(b.name)])),
    [buildings.data],
  )
  const floorMetadata = useMemo(
    () => new Map(floors.data?.map((floor) => [floor.id, floor])),
    [floors.data],
  )
  const compareFloorIds = (a: string, b: string) => {
    const first = floorMetadata.get(a)
    const second = floorMetadata.get(b)
    const firstLevel = first && Number.isFinite(first.level) ? first.level : Infinity
    const secondLevel = second && Number.isFinite(second.level) ? second.level : Infinity
    if (firstLevel !== secondLevel) return firstLevel < secondLevel ? -1 : 1
    if (Boolean(first) !== Boolean(second)) return first ? -1 : 1
    return (
      (first?.name || '').localeCompare(second?.name || '', 'zh-CN', { numeric: true }) ||
      // Opaque IDs only break ties; they never supply a floor level.
      (a < b ? -1 : a > b ? 1 : 0)
    )
  }
  const visible = useMemo(
    () =>
      rows
        .filter(
          (room) =>
            (!state || room[dimension] === state) &&
            `${room.name} ${names.get(room.building_id) || ''} ${room.id}`
              .toLowerCase()
              .includes(search.toLowerCase()),
        )
        .sort(
          (a, b) =>
            (names.get(a.building_id) || a.building_id).localeCompare(
              names.get(b.building_id) || b.building_id,
              'zh-CN',
              { numeric: true },
            ) || a.name.localeCompare(b.name, 'zh-CN', { numeric: true }),
        ),
    [rows, state, dimension, search, names],
  )
  const groups = useMemo(() => {
    const result = new Map<string, Map<string, RoomSnapshot[]>>()
    for (const room of visible.slice(offset, offset + pageSize)) {
      if (!result.has(room.building_id)) result.set(room.building_id, new Map())
      const floors = result.get(room.building_id)!
      const key = room.floor_id || ''
      if (!floors.has(key)) floors.set(key, [])
      floors.get(key)!.push(room)
    }
    return [...result.entries()].sort(([a], [b]) =>
      (names.get(a) || a).localeCompare(names.get(b) || b, 'zh-CN', { numeric: true }),
    )
  }, [visible, names, offset])
  const states =
    dimension === 'occupancy'
      ? ['occupied', 'vacant', 'unknown']
      : dimension === 'mode'
        ? ['manual', 'automatic', 'maintenance', 'fault']
        : ['on', 'off', 'mixed', 'unknown']
  const knownPower = rows.filter((room) => room.observed_power_w !== null)
  const power = knownPower.length
    ? knownPower.reduce((sum, room) => sum + room.observed_power_w!, 0)
    : null
  const summaries = [
    {
      label: '可访问空间',
      value: rooms.data ? total : null,
      icon: DoorOpen,
      unit: '间',
      note: '全部来自已发布空间身份',
    },
    {
      label: '已观测有人',
      value: rooms.data ? rows.filter((r) => r.occupancy === 'occupied').length : null,
      icon: Users,
      unit: '间',
      note: '仅有效存在传感证据',
    },
    {
      label: '占用未知',
      value: rooms.data ? rows.filter((r) => r.occupancy === 'unknown').length : null,
      icon: ShieldQuestion,
      unit: '间',
      note: '无设备、过期或冲突均保留未知',
    },
    {
      label: '照明回报开启 / 部分开启',
      value: rooms.data ? rows.filter((r) => ['on', 'mixed'].includes(r.lighting)).length : null,
      icon: Lightbulb,
      unit: '间',
      note: '执行回报不等于灯具点亮验证',
    },
    {
      label: '已知教室功率',
      value: power == null ? null : power / 1000,
      icon: Zap,
      unit: 'kW',
      note: `${knownPower.length} 间有功率证据 · 非校区结算总表`,
    },
  ]
  return (
    <div className="classroom-workspace">
      <PageHeader
        eyebrow="CLASSROOM OPERATIONS"
        title="教室工作台"
        description="同一时刻看全校，同一间教室看完整证据。空间、设备与执行反馈在这里连接。"
        actions={
          <Link className="button button-secondary" to="/campus">
            <Layers3 size={15} />
            校园地图
            <ArrowUpRight size={14} />
          </Link>
        }
      />
      <div className="classroom-intro">
        <div>
          <div className="eyebrow">ONE CAMPUS · EVERY ROOM</div>
          <h2>让每间教室的状态，都有依据</h2>
          <p>
            从房间状态进入 Sense、Switch 与 Plug
            的实际能力，追溯占用、功率和控制反馈。未接入空间也完整保留，未知不会变成“无人”或“已关闭”。
          </p>
        </div>
        <div className="classroom-intro-symbol">
          <DoorOpen size={42} strokeWidth={1.3} />
        </div>
      </div>
      <div className="classroom-toolbar">
        <div className="filter-bar">
          <BuildingFilter
            value={building}
            onChange={(value) => update({ building: value, floor: undefined })}
          />
          <select
            aria-label="筛选楼层"
            disabled={!building || floors.isLoading}
            value={floor}
            onChange={(event) => update({ floor: event.target.value })}
          >
            <option value="">全部楼层</option>
            {floors.data?.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
        <ClassroomTimeSelector at={at} onChange={(value) => update({ at: value })} />
      </div>
      {at && (
        <Notice>
          历史快照 · {formatDate(at)}。只展示该时刻可成立的观测；不能用历史状态申请现场控制。
        </Notice>
      )}
      <div className="room-summary-grid">
        {summaries.map((metric) => (
          <Card className="room-summary" key={metric.label}>
            <div>
              <span>{metric.label}</span>
              <metric.icon size={17} />
            </div>
            <strong>
              {formatNumber(metric.value)}
              <small>{metric.unit}</small>
            </strong>
            <p>{metric.note}</p>
          </Card>
        ))}
      </div>
      <Tabs
        active={distribution ? 'range' : 'snapshot'}
        onChange={(value) => setDistribution(value === 'range')}
        items={[
          { id: 'snapshot', label: '同刻空间快照' },
          { id: 'range', label: '区间状态分布' },
        ]}
      />
      {distribution ? (
        <ClassroomDistribution
          key={`${building}:${floor}:${at || 'live'}`}
          buildingId={building}
          floorId={floor}
          at={at}
        />
      ) : (
        <Card className="room-matrix-card">
          <CardHeader
            title="空间状态矩阵"
            subtitle={
              rows[0]
                ? `状态时刻 ${formatDate(rows[0].at)} · 匹配 ${visible.length} / ${total} 间 · 每页最多 ${pageSize} 间`
                : '按楼栋与楼层组织，选择房间打开工作台'
            }
            actions={
              <div className="inline-gap">
                {[...new Set(rows.map((room) => room.source_mode))].map((mode) => (
                  <SourceBadge key={mode} value={mode} />
                ))}
                <Badge tone="teal">服务端状态</Badge>
              </div>
            }
          />
          <Tabs
            active={dimension}
            items={dimensions}
            onChange={(value) => {
              setDimension(value as Dimension)
              setState('')
            }}
          />
          <div className="room-matrix-controls">
            <label className="search-field">
              <Search size={15} />
              <input
                aria-label="搜索教室"
                placeholder="搜索教室、楼栋或空间 ID…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <select
              aria-label="筛选房间状态"
              value={state}
              onChange={(event) => setState(event.target.value)}
            >
              <option value="">全部状态</option>
              {states.map((value) => (
                <option key={value} value={value}>
                  {roomStateLabel(value)}
                </option>
              ))}
            </select>
            <div className="room-state-legend">
              {states.map((value) => (
                <span key={value}>
                  <i className={`room-state-dot ${value}`} />
                  {roomStateLabel(value)}
                </span>
              ))}
            </div>
          </div>
          {rooms.isLoading ? (
            <Loading label="正在读取全校空间状态…" />
          ) : rooms.error ? (
            <ErrorState error={rooms.error} retry={() => void rooms.refetch()} />
          ) : !visible.length ? (
            <EmptyState
              title="没有匹配的空间"
              description="请调整楼栋、楼层、关键词或状态筛选；没有匹配项不代表校园无人。"
            />
          ) : (
            groups.map(([buildingId, floorGroups]) => (
              <section className="room-building-group" key={buildingId}>
                <div className="room-building-heading">
                  <h3>
                    <Building2 size={17} />
                    {names.get(buildingId) || buildingId}
                    <small>
                      {[...floorGroups.values()].reduce((sum, r) => sum + r.length, 0)} 间
                    </small>
                  </h3>
                  <Link
                    className="text-link"
                    to={`/campus${queryString({ building: buildingId, at })}`}
                  >
                    楼栋地图
                    <ArrowUpRight size={13} />
                  </Link>
                </div>
                {[...floorGroups.entries()]
                  .sort(([a], [b]) => compareFloorIds(a, b))
                  .map(([floorId, floorRooms]) => (
                    <div className="room-floor-row" key={floorId}>
                      <div className="room-floor-label">
                        {floorMetadata.get(floorId)?.name ||
                          (floorId
                            ? floorId
                                .replace(/^floor:search:/, '')
                                .split(/[:-]/)
                                .pop()
                            : '楼层未核验')}
                      </div>
                      <div className="room-matrix">
                        {floorRooms
                          .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN', { numeric: true }))
                          .map((room) => (
                            <Link
                              key={room.id}
                              className={`room-tile state-${stateClass(room[dimension])}`}
                              to={classroomPath(room.id, at)}
                              aria-label={`${room.name}，${roomStateLabel(room[dimension])}，打开教室`}
                            >
                              <strong>{room.name}</strong>
                              <span>
                                <i className={`room-state-dot ${stateClass(room[dimension])}`} />
                                {roomStateLabel(room[dimension])}
                              </span>
                              <small>
                                {room.observed_power_w == null
                                  ? '功率未知'
                                  : `${formatNumber(room.observed_power_w)} W`}{' '}
                                · {room.channels.length} 通道
                              </small>
                              {room.active_anomaly_ids.length > 0 && (
                                <i
                                  className="room-tile-alert"
                                  title={`${room.active_anomaly_ids.length} 条活动异常`}
                                />
                              )}
                            </Link>
                          ))}
                      </div>
                    </div>
                  ))}
              </section>
            ))
          )}
          {total > rows.length && !rooms.isLoading && (
            <Notice tone="warning">
              当前响应仅包含 {rows.length} / {total} 间；上方统计仅针对已载入空间，不代表全量。
            </Notice>
          )}
          {!rooms.isLoading && !rooms.error && (
            <Pagination
              offset={offset}
              limit={pageSize}
              total={visible.length}
              setOffset={setOffset}
            />
          )}
          <p className="room-matrix-foot">
            虚线纹理表示未知，不是关闭；照明执行回报不等于灯具点亮验证。空间身份来自已发布档案；设备来源、安装绑定与观测有效期分别核验。计划人数不替代传感器观测。
          </p>
        </Card>
      )}
    </div>
  )
}
