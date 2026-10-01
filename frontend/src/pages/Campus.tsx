import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  Box,
  Building2,
  ChevronRight,
  Layers3,
  Map,
  MapPin,
  LocateFixed,
  Minus,
  Plus,
  Search,
  ShieldQuestion,
  Zap,
} from 'lucide-react'
import { useResource } from '../lib/hooks'
import type { RoomSnapshot } from '../lib/classroom-types'
import { classroomPath, roomStateLabel, stateClass, validTimestamp } from '../lib/classroom-display'
import ClassroomTimeSelector from '../components/ClassroomTimeSelector'
import { ClassroomState } from '../components/ClassroomState'
import { queryString } from '../lib/api'
import type { Building, Device, Floor, Space } from '../lib/types'
import type {
  Floorplan,
  SpatialGeoJSON,
  SpatialManifest,
  SpatialContextGeoJSON,
} from '../lib/spatial'
import { useSpatial } from '../lib/spatial'
import { displayBuildingName, sortBuildings } from '../lib/registry-display'
import { useScope } from '../lib/scope'
import { formatNumber } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionList,
  Drawer,
  EmptyState,
  ErrorState,
  IconButton,
  Loading,
  Modal,
  Notice,
  PageHeader,
  SourceBadge,
  StatusBadge,
  Tabs,
} from '../components/ui'
import CampusMap2D from '../components/CampusMap2D'
const CampusMap3D = lazy(() => import('../components/CampusMap3D'))
export function FloorMap({
  path,
  version,
  selected,
  onSelect,
  roomStates,
}: {
  path: string
  version?: string
  selected: string | null
  onSelect: (id: string) => void
  roomStates?: Record<string, RoomSnapshot>
}) {
  const query = useSpatial<Floorplan>(path, version)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null)
  useEffect(() => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
    drag.current = null
  }, [path])
  const eventPoint = (svg: SVGSVGElement, clientX: number, clientY: number) => {
    const matrix = svg.getScreenCTM()
    return matrix
      ? new DOMPoint(clientX, clientY).matrixTransform(matrix.inverse())
      : { x: clientX, y: clientY }
  }
  if (query.isLoading) return <Loading label="正在读取楼层图面…" />
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch()
        }}
      />
    )
  if (!query.data) return null
  const d = query.data
  const units = d.space_units.filter(
    (s) =>
      Array.isArray(s.polygon) &&
      s.polygon.length >= 3 &&
      s.polygon.every((p) => p.length >= 2 && Number.isFinite(p[0]) && Number.isFinite(p[1])) &&
      s.label_point?.every(Number.isFinite),
  )
  if (!units.length)
    return <EmptyState title="该图面没有有效几何" description="请使用下方空间清单继续浏览" />
  const all = units.flatMap((s) => s.polygon)
  const minX = Math.min(...all.map((p) => p[0])) - 0.03
  const minY = Math.min(...all.map((p) => p[1])) - 0.03
  const maxX = Math.max(...all.map((p) => p[0])) + 0.03
  const maxY = Math.max(...all.map((p) => p[1])) + 0.03
  const aspect =
    d.view_box && d.view_box[0] > 0 && d.view_box[1] > 0 ? d.view_box[1] / d.view_box[0] : 0.65
  const centerX = (minX + maxX) * 500,
    centerY = (minY + maxY) * 500 * aspect
  return (
    <div className="floor-map">
      <div className="floor-note">
        <Layers3 size={15} />
        独立室内示意坐标 · 未与室外地图精确配准
      </div>
      <svg
        viewBox={`${minX * 1000} ${minY * 1000 * aspect} ${(maxX - minX) * 1000} ${(maxY - minY) * 1000 * aspect}`}
        aria-label="楼层房间示意图"
        onPointerDown={(event) => {
          if (event.target === event.currentTarget) {
            const point = eventPoint(event.currentTarget, event.clientX, event.clientY)
            drag.current = { x: point.x, y: point.y, panX: pan.x, panY: pan.y }
            event.currentTarget.setPointerCapture(event.pointerId)
          }
        }}
        onPointerMove={(event) => {
          if (drag.current) {
            const point = eventPoint(event.currentTarget, event.clientX, event.clientY)
            setPan({
              x: drag.current.panX + point.x - drag.current.x,
              y: drag.current.panY + point.y - drag.current.y,
            })
          }
        }}
        onPointerUp={() => {
          drag.current = null
        }}
        onPointerCancel={() => {
          drag.current = null
        }}
        onLostPointerCapture={() => {
          drag.current = null
        }}
      >
        <g
          className="floor-map-content"
          transform={`translate(${centerX + pan.x} ${centerY + pan.y}) scale(${zoom}) translate(${-centerX} ${-centerY})`}
        >
          {units.map((space, index) => (
            <g
              key={space.id || index}
              className={`floor-room state-${stateClass(space.space_id ? roomStates?.[space.space_id]?.occupancy : 'unknown')} ${selected === space.space_id ? 'selected' : ''} ${!space.space_id ? 'unresolved' : ''}`}
              tabIndex={space.space_id ? 0 : undefined}
              role={space.space_id ? 'button' : undefined}
              aria-label={`${space.name}，占用${roomStateLabel(space.space_id ? roomStates?.[space.space_id]?.occupancy : 'unknown')}`}
              onClick={() => space.space_id && onSelect(space.space_id)}
              onKeyDown={(e) => {
                if (space.space_id && (e.key === 'Enter' || e.key === ' ')) {
                  e.preventDefault()
                  onSelect(space.space_id)
                }
              }}
            >
              <polygon
                points={space.polygon
                  .map((p) => `${p[0] * 1000},${p[1] * 1000 * aspect}`)
                  .join(' ')}
              />
              <text
                x={space.label_point[0] * 1000}
                y={space.label_point[1] * 1000 * aspect}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {space.name.split('-').pop()}
              </text>
              <title>
                {space.name} · 占用
                {roomStateLabel(
                  space.space_id ? roomStates?.[space.space_id]?.occupancy : 'unknown',
                )}{' '}
                · {space.geometry_status}
              </title>
            </g>
          ))}
        </g>
      </svg>
      <div className="map-controls floor-controls">
        <IconButton
          label="放大楼层图"
          disabled={zoom >= 6}
          onClick={() => setZoom((v) => Math.min(6, v * 1.35))}
        >
          <Plus size={17} />
        </IconButton>
        <IconButton
          label="缩小楼层图"
          disabled={zoom <= 0.75}
          onClick={() => setZoom((v) => Math.max(0.75, v / 1.35))}
        >
          <Minus size={17} />
        </IconButton>
        <IconButton
          label="重置楼层视角"
          onClick={() => {
            setZoom(1)
            setPan({ x: 0, y: 0 })
          }}
        >
          <LocateFixed size={17} />
        </IconButton>
      </div>
      <div className="floor-legend">
        <span>
          <i className="room-state-dot occupied" />
          有效有人
        </span>
        <span>
          <i className="room-state-dot vacant" />
          有效无人
        </span>
        <span>
          <i />
          未观测空间
        </span>
        <span>
          <i className="active" />
          已选空间
        </span>
        <span>
          <ShieldQuestion size={13} />
          未知不等于无人
        </span>
      </div>
    </div>
  )
}
export default function Campus() {
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const at = validTimestamp(params.get('at')) || params.get('at') || undefined
  const selectedBuilding = params.get('building') || ''
  const selectedFloor = params.get('floor') || ''
  const selectedSpace = params.get('space') || ''
  const [search, setSearch] = useState('')
  const [view, setView] = useState('2d')
  const [sourceOpen, setSourceOpen] = useState(false)
  const closeSource = useCallback(() => setSourceOpen(false), [])
  const buildings = useResource<Building[]>(
    `/buildings${queryString({ campus_id: scope.campusId, limit: 500 })}`,
  )
  const detail = useResource<Building>(`/buildings/${encodeURIComponent(selectedBuilding)}`, {
    enabled: !!selectedBuilding,
  })
  const floors = useResource<Floor[]>(
    `/floors${queryString({ building_id: selectedBuilding, limit: 500 })}`,
    { enabled: !!selectedBuilding },
  )
  const spaces = useResource<Space[]>(
    `/spaces${queryString({ building_id: selectedBuilding, floor_id: selectedFloor, limit: 500 })}`,
    { enabled: !!selectedBuilding },
  )
  const devices = useResource<Device[]>(
    `/devices${queryString({ building_id: selectedBuilding, space_id: selectedSpace, limit: 500 })}`,
    { enabled: !!selectedBuilding },
  )
  const roomQuery = useResource<RoomSnapshot[]>(
    `/classrooms${queryString({ building_id: selectedBuilding, at, limit: 2000 })}`,
    { enabled: !!selectedBuilding, interval: at ? false : 30_000 },
  )
  const roomStates = useMemo(
    () => Object.fromEntries((roomQuery.data || []).map((room) => [room.id, room])),
    [roomQuery.data],
  )
  const roomState = roomStates[selectedSpace]
  const manifest = useResource<SpatialManifest>('/assets/manifest', {
    interval: false,
  })
  const geo = useSpatial<SpatialGeoJSON>(manifest.data?.local_geojson_url, manifest.data?.version)
  const context = useSpatial<SpatialContextGeoJSON>(
    manifest.data?.context_local_geojson_url,
    manifest.data?.version,
  )
  const buildingIdsKey = (buildings.data || [])
    .map((building) => building.id)
    .sort()
    .join('|')
  const allowedIds = useMemo(
    () => new Set(buildingIdsKey.split('|').filter(Boolean)),
    [buildingIdsKey],
  )
  const campusNames = useMemo(
    () => new globalThis.Map(scope.campuses.map((campus) => [campus.id, campus.name])),
    [scope.campuses],
  )
  const visibleBuildings = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    return sortBuildings(buildings.data || []).filter((building) =>
      `${building.name} ${displayBuildingName(building.name)} ${campusNames.get(building.campus_id) || ''}`
        .toLowerCase()
        .includes(keyword),
    )
  }, [buildings.data, search, campusNames])
  const selected = detail.data
  const space = spaces.data?.find((s) => s.id === selectedSpace)
  const selectBuilding = useCallback(
    (id: string) => {
      setParams({ building: id, ...(at ? { at } : {}) })
    },
    [setParams, at],
  )
  const closeSpace = useCallback(() => {
    const next = new URLSearchParams(params)
    next.delete('space')
    setParams(next)
  }, [params, setParams])
  const floorSourceId = selectedFloor.replace(/^floor:search:/, '')
  const floorpath = manifest.data?.floorplans?.[floorSourceId]
  return (
    <>
      <PageHeader
        eyebrow="SPATIAL INTELLIGENCE"
        title="校园空间"
        description="从校园到楼宇、楼层与房间，建立空间和设备之间可追溯的连接。"
        actions={<Badge tone="blue">空间参考数据</Badge>}
      />
      <div className="classroom-toolbar" style={{ marginBottom: 18 }}>
        <Link
          className="text-link"
          to={`/classrooms${queryString({ building: selectedBuilding, at })}`}
        >
          全校教室状态矩阵
          <ArrowRight size={14} />
        </Link>
        <ClassroomTimeSelector
          at={at}
          onChange={(value) => {
            const next = new URLSearchParams(params)
            value ? next.set('at', value) : next.delete('at')
            setParams(next)
          }}
        />
      </div>
      {selectedBuilding && roomQuery.error && (
        <ErrorState error={roomQuery.error} compact retry={() => void roomQuery.refetch()} />
      )}
      <div className="campus-workspace">
        <Card className="building-browser">
          <div className="building-browser-head">
            <div>
              <h2>空间目录</h2>
              <Badge>{buildings.data?.length ?? '—'} 条</Badge>
            </div>
            <label className="search-field">
              <Search size={16} />
              <input
                aria-label="筛选楼栋"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索楼栋或校区…"
              />
            </label>
          </div>
          {buildings.isLoading ? (
            <Loading compact />
          ) : buildings.error ? (
            <ErrorState
              error={buildings.error}
              compact
              retry={() => {
                void buildings.refetch()
              }}
            />
          ) : (
            <div className="building-list">
              {visibleBuildings.map((b) => (
                <button
                  key={b.id}
                  className={selectedBuilding === b.id ? 'selected' : ''}
                  onClick={() => selectBuilding(b.id)}
                >
                  <span className="building-icon">
                    <Building2 size={18} />
                  </span>
                  <div>
                    <strong title={`来源名称：${b.name} · ${b.id}`}>
                      {displayBuildingName(b.name)}
                    </strong>
                    <small>
                      {scope.campuses.find((campus) => campus.id === b.campus_id)?.name ||
                        '校区资料未载入'}{' '}
                      · {b.device_count} 台设备
                    </small>
                  </div>
                  <ChevronRight size={14} />
                </button>
              ))}
              {!visibleBuildings.length && (
                <EmptyState title="未找到楼栋" description="试试其他关键词" />
              )}
            </div>
          )}
          <div className="browser-foot">
            <MapPin size={13} />
            {visibleBuildings.length} 条档案 · 可按名称或校区检索
          </div>
        </Card>
        <Card className="map-card">
          <div className="map-toolbar">
            <div className="map-title">
              <span className="live-dot" />
              <strong>{selected ? displayBuildingName(selected.name) : '校园空间全景'}</strong>
              <span>
                {selectedFloor
                  ? floors.data?.find((f) => f.id === selectedFloor)?.name
                  : '室外场景'}
              </span>
            </div>
            {selectedFloor ? (
              <Button
                variant="ghost"
                onClick={() => setParams({ building: selectedBuilding, ...(at ? { at } : {}) })}
              >
                <ArrowLeft size={14} />
                返回室外
              </Button>
            ) : (
              <div className="segmented">
                <button className={view === '2d' ? 'active' : ''} onClick={() => setView('2d')}>
                  <Map size={14} />
                  二维
                </button>
                <button className={view === '3d' ? 'active' : ''} onClick={() => setView('3d')}>
                  <Box size={14} />
                  三维
                </button>
              </div>
            )}
          </div>
          {selectedFloor ? (
            floorpath ? (
              <FloorMap
                path={floorpath}
                version={manifest.data?.version}
                roomStates={roomStates}
                selected={selectedSpace}
                onSelect={(id) => {
                  const next = new URLSearchParams(params)
                  next.set('space', id)
                  setParams(next)
                }}
              />
            ) : (
              <div className="map-empty">
                <EmptyState
                  title="该楼层尚无已发布图面"
                  description="请在下方空间清单选择房间，平台不会生成没有依据的平面图。"
                />
              </div>
            )
          ) : manifest.error || geo.error ? (
            <ErrorState
              error={manifest.error || geo.error}
              retry={() => {
                void manifest.refetch()
                void geo.refetch()
              }}
            />
          ) : manifest.isLoading || geo.isLoading ? (
            <Loading label="正在加载已发布的校园空间…" />
          ) : manifest.data && geo.data ? (
            view === '2d' ? (
              <CampusMap2D
                data={geo.data}
                context={context.data}
                allowedIds={allowedIds}
                selected={selectedBuilding}
                onSelect={selectBuilding}
              />
            ) : (
              <Suspense fallback={<Loading label="正在加载三维引擎…" />}>
                <CampusMap3D
                  manifest={manifest.data}
                  allowedIds={allowedIds}
                  selected={selectedBuilding}
                  onSelect={selectBuilding}
                />
              </Suspense>
            )
          ) : (
            <EmptyState title="空间产物暂不可用" />
          )}
          {context.error && !selectedFloor && (
            <div className="map-context-note" role="status">
              背景参考加载失败，楼栋导航仍可使用{' '}
              <button
                onClick={() => {
                  void context.refetch()
                }}
              >
                重试背景
              </button>
            </div>
          )}
          <div className="map-source-strip">
            <span>
              <Layers3 size={14} />
              {selectedFloor ? '楼层平面示意' : view === '3d' ? '三维校园视图' : '二维校园视图'}
            </span>
            <Button
              variant="ghost"
              className="source-details-button"
              onClick={() => setSourceOpen(true)}
            >
              数据来源
            </Button>
          </div>
        </Card>
      </div>
      {sourceOpen && (
        <Modal title="空间数据来源" onClose={closeSource}>
          <Notice>
            校园地图与外观用于空间参考。高度和外观含来源推断，不代表测绘或结构
            BIM；楼层图保持独立示意坐标，不据此推定现场占用。
          </Notice>
          <DefinitionList
            items={[
              [
                '发布版本',
                <span className="monospace">{manifest.data?.version || '尚未载入'}</span>,
              ],
              ['室外资料', 'OpenStreetMap / hicancan · njupt-map'],
              ['室内资料', '源项目的楼层与空间档案；北向与室外配准未确认'],
              ['详细外观', '按建筑单独加载来源模型，保留作者材质与稳定身份'],
            ]}
          />
          <Link className="text-link" to="/system" onClick={closeSource}>
            查看平台资料与来源说明
            <ArrowRight size={14} />
          </Link>
        </Modal>
      )}
      {selectedBuilding && (
        <Card className="building-detail">
          <CardHeader
            title={selected ? displayBuildingName(selected.name) : '楼栋详情'}
            subtitle={selected ? `${selected.category} · ${selected.source}` : '正在读取楼栋'}
            actions={
              <Link
                className="button button-secondary"
                to={`/devices?building=${encodeURIComponent(selectedBuilding)}`}
              >
                <Zap size={15} />
                查看楼栋设备
                <ArrowUpRightIcon />
              </Link>
            }
          />
          {detail.error && <ErrorState error={detail.error} />}
          {selected && (
            <>
              <div className="building-summary">
                <div>
                  <span>关联登记设备</span>
                  <strong>
                    {selected.device_count}
                    <small>台</small>
                  </strong>
                </div>
                <div>
                  <span>参考楼层</span>
                  <strong>
                    {floors.data?.length ?? '—'}
                    <small>层</small>
                  </strong>
                </div>
                <div>
                  <span>当前空间清单</span>
                  <strong>
                    {spaces.data?.length ?? '—'}
                    <small>个</small>
                  </strong>
                </div>
                <div>
                  <span>已观测有人 / 未知</span>
                  <strong className="unknown-value">
                    {roomQuery.data
                      ? `${roomQuery.data.filter((r) => r.occupancy === 'occupied').length} / ${roomQuery.data.filter((r) => r.occupancy === 'unknown').length}`
                      : '未知'}
                    <small>按有效观测统计</small>
                  </strong>
                </div>
              </div>
              <div className="floor-tabs">
                <Tabs
                  active={selectedFloor}
                  items={[
                    { id: '', label: '全部空间' },
                    ...(floors.data || []).map((f) => ({
                      id: f.id,
                      label: f.name,
                    })),
                  ]}
                  onChange={(id) =>
                    setParams({
                      building: selectedBuilding,
                      ...(at ? { at } : {}),
                      ...(id ? { floor: id } : {}),
                    })
                  }
                />
              </div>
              {spaces.isLoading ? (
                <Loading />
              ) : spaces.error ? (
                <ErrorState error={spaces.error} />
              ) : spaces.data?.length ? (
                <div className="space-grid">
                  {spaces.data.map((s) => (
                    <button
                      className={`space-card ${selectedSpace === s.id ? 'selected' : ''}`}
                      key={s.id}
                      onClick={() => {
                        const next = new URLSearchParams(params)
                        next.set('space', s.id)
                        next.set('floor', s.floor_id)
                        setParams(next)
                      }}
                    >
                      <div>
                        <Layers3 size={16} />
                        <ClassroomState value={roomStates[s.id]?.occupancy} prefix="占用" />
                      </div>
                      <strong>{s.name}</strong>
                      <small>
                        {s.kind} · {s.confidence || '参考身份'}
                      </small>
                      <span>
                        查看空间
                        <ArrowRight size={13} />
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="该楼栋尚无已确认的房间参考"
                  description="楼栋级设备仍可管理；新增房间需要经过空间身份核验。"
                />
              )}
            </>
          )}
        </Card>
      )}
      {selectedSpace && (
        <Drawer title={space?.name || '空间详情'} subtitle={selectedSpace} onClose={closeSpace}>
          <div className="inline-gap section-space">
            <ClassroomState value={roomState?.occupancy} prefix="占用" />
            <ClassroomState value={roomState?.lighting} prefix="照明" />
            <SourceBadge value={roomState?.source_mode} />
          </div>
          <Link
            className="button button-primary section-space"
            to={classroomPath(selectedSpace, at)}
          >
            打开教室工作台
            <ArrowRight size={15} />
          </Link>
          <Notice
            tone={roomState?.occupancy === 'unknown' || !roomState ? 'warning' : 'info'}
            title={at ? '历史快照' : '房间观测'}
          >
            {roomState
              ? `快照 ${new Date(roomState.at).toLocaleString('zh-CN')} · 观测功率 ${formatNumber(roomState.observed_power_w)} W。`
              : '没有有效房间状态。'}
            无课表不等于无人；房间摘要不授权断电。
          </Notice>
          {space && (
            <DefinitionList
              items={[
                ['空间类型', space.kind],
                ['参考来源', space.source],
                ['置信度', space.confidence],
                ['楼栋', selected?.name],
                ['坐标状态', '独立归一化示意图，未实测配准'],
              ]}
            />
          )}
          <CardHeader title="空间关联设备" subtitle="设备数据来源与安装授权分别核验" />
          {devices.isLoading ? (
            <Loading compact />
          ) : devices.error ? (
            <ErrorState error={devices.error} />
          ) : devices.data?.length ? (
            <div className="device-mini-list">
              {devices.data.map((device) => (
                <Link key={device.id} to={`/devices?device=${encodeURIComponent(device.id)}`}>
                  <span className="device-mini-icon">
                    <Zap size={19} />
                  </span>
                  <div>
                    <strong>{device.name}</strong>
                    <span>
                      <SourceBadge value={device.source_mode} />
                      <StatusBadge value={device.status} />
                    </span>
                  </div>
                  <strong>
                    {formatNumber(device.latest?.active_power_w)}
                    <small>W</small>
                  </strong>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="该空间暂无关联设备"
              description="可在设备详情中完成经过核验的空间绑定"
            />
          )}
        </Drawer>
      )}
    </>
  )
}
function ArrowUpRightIcon() {
  return <ArrowRight size={14} />
}
