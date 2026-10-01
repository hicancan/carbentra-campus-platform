import { useMemo, useRef, useState } from 'react'
import { LocateFixed, Minus, Plus } from 'lucide-react'
import type { SpatialFeature, SpatialGeoJSON, SpatialContextGeoJSON } from '../lib/spatial'
import { polygonRings } from '../lib/spatial'
import { EmptyState, IconButton } from './ui'
import CampusContext2D from './CampusContext2D'
import MapAttribution from './MapAttribution'
export default function CampusMap2D({
  data,
  context,
  allowedIds,
  selected,
  onSelect,
}: {
  data: SpatialGeoJSON
  context?: SpatialContextGeoJSON
  allowedIds: Set<string>
  selected?: string
  onSelect: (id: string) => void
}) {
  const features = useMemo(
    () =>
      data.features.filter((f) => {
        if (!allowedIds.has(f.properties.building_id)) return false
        const rings = polygonRings(f)
        return (
          rings.length > 0 &&
          rings.every(
            (ring) =>
              ring.length >= 3 &&
              ring.every((point) => Number.isFinite(point[0]) && Number.isFinite(point[1])),
          )
        )
      }),
    [data, allowedIds],
  )
  const [showContext, setShowContext] = useState(true)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [hover, setHover] = useState<SpatialFeature | null>(null)
  const start = useRef<{
    x: number
    y: number
    panX: number
    panY: number
  } | null>(null)
  const coordinates = features.flatMap(polygonRings).flat()
  const xs = coordinates.map((c) => c[0])
  const ys = coordinates.map((c) => c[1])
  const minX = Math.min(...xs),
    maxX = Math.max(...xs),
    minY = Math.min(...ys),
    maxY = Math.max(...ys)
  const width = 1000,
    height = 680
  const scale = Math.min((width - 100) / (maxX - minX || 1), (height - 100) / (maxY - minY || 1))
  const dx = (width - (maxX - minX) * scale) / 2,
    dy = (height - (maxY - minY) * scale) / 2
  const point = (p: number[]) => `${(p[0] - minX) * scale + dx},${(maxY - p[1]) * scale + dy}`
  if (!features.length)
    return (
      <div className="map-empty">
        <EmptyState
          title="该范围尚无已发布的室外几何"
          description="楼栋与室内空间仍可在左侧完整浏览，不以推测位置替代地图。"
        />
      </div>
    )
  return (
    <div className="campus-map">
      <svg
        className="map-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="group"
        aria-label="校园楼栋二维地图"
        onPointerDown={(event) => {
          if (event.target === event.currentTarget) {
            start.current = {
              x: event.clientX,
              y: event.clientY,
              panX: pan.x,
              panY: pan.y,
            }
            event.currentTarget.setPointerCapture(event.pointerId)
          }
        }}
        onPointerMove={(event) => {
          if (start.current) {
            const ratio = width / event.currentTarget.getBoundingClientRect().width
            setPan({
              x: start.current.panX + (event.clientX - start.current.x) * ratio,
              y: start.current.panY + (event.clientY - start.current.y) * ratio,
            })
          }
        }}
        onPointerUp={() => {
          start.current = null
        }}
        onPointerCancel={() => {
          start.current = null
        }}
        onLostPointerCapture={() => {
          start.current = null
        }}
      >
        <defs>
          <pattern
            id="campus-grid"
            x="0"
            y="0"
            width="24"
            height="24"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".8" fill="currentColor" opacity=".12" />
          </pattern>
          <filter id="building-shadow">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity=".07" />
          </filter>
        </defs>
        <rect width={width} height={height} fill="url(#campus-grid)" pointerEvents="none" />
        <g
          transform={`translate(${width / 2 + pan.x} ${height / 2 + pan.y}) scale(${zoom}) translate(${-width / 2} ${-height / 2})`}
        >
          {context && showContext && (
            <CampusContext2D data={context} project={point} scale={scale} />
          )}
          {features.map((feature) => {
            const rings = polygonRings(feature)
            const path = rings.map((ring) => `M${ring.map(point).join(' L')}Z`).join(' ')
            const active = selected === feature.properties.building_id
            return (
              <g
                key={feature.properties.asset_id}
                role="button"
                aria-label={`选择楼栋 ${feature.properties.name}`}
                tabIndex={0}
                className={`map-building ${active ? 'selected' : ''}`}
                onClick={() => onSelect(feature.properties.building_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelect(feature.properties.building_id)
                  }
                }}
                onMouseEnter={() => setHover(feature)}
                onMouseLeave={() => setHover(null)}
              >
                <path
                  d={path}
                  fillRule="evenodd"
                  filter="url(#building-shadow)"
                  strokeWidth={active ? 2 : 1.1}
                  vectorEffect="non-scaling-stroke"
                />
                <title>{feature.properties.name}</title>
              </g>
            )
          })}
        </g>
      </svg>
      {context && (
        <label className="map-layer-toggle">
          <input
            type="checkbox"
            checked={showContext}
            onChange={(e) => setShowContext(e.target.checked)}
          />
          道路 · 绿地 · 水系
        </label>
      )}
      <div className="map-compass">
        <span>N</span>
        <div>↑</div>
      </div>
      <div className="map-controls">
        <IconButton
          label="放大地图"
          disabled={zoom >= 5}
          onClick={() => setZoom((z) => Math.min(5, z * 1.35))}
        >
          <Plus size={17} />
        </IconButton>
        <IconButton
          label="缩小地图"
          disabled={zoom <= 0.6}
          onClick={() => setZoom((z) => Math.max(0.6, z / 1.35))}
        >
          <Minus size={17} />
        </IconButton>
        <IconButton
          label="重置视角"
          onClick={() => {
            setZoom(1)
            setPan({ x: 0, y: 0 })
          }}
        >
          <LocateFixed size={17} />
        </IconButton>
      </div>
      {hover && (
        <div className="map-hover">
          <strong>{hover.properties.name}</strong>
          <span>点击进入楼栋</span>
        </div>
      )}
      <MapAttribution />
      <div className="map-instructions">拖动空白处平移 · 点击楼栋查看</div>
    </div>
  )
}
