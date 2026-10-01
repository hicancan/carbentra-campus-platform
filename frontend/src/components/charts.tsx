import { useEffect, useId, useRef, useState } from 'react'
import { browserTimezone } from '../lib/timezone'
import { formatDate, formatNumber, formatTime } from '../lib/format'
import { EmptyState } from './ui'
export interface ChartPoint {
  timestamp: string
  value: number | null
  secondary?: number | null
  lower?: number | null
  upper?: number | null
}
export function chartXCoordinates(points: ChartPoint[], width: number): number[] {
  const times = points.map((point) => Date.parse(point.timestamp))
  const valid =
    times.every(Number.isFinite) &&
    times.every((time, index) => index === 0 || time >= times[index - 1])
  const span = times.length > 1 ? times[times.length - 1] - times[0] : 0
  return points.map((_, index) =>
    valid && span > 0
      ? ((times[index] - times[0]) / span) * width
      : points.length === 1
        ? width / 2
        : (index / Math.max(points.length - 1, 1)) * width,
  )
}
export function chartSegments(
  points: ChartPoint[],
  width: number,
  height: number,
  max: number,
  min = 0,
): string[] {
  const segments: string[] = []
  let current = ''
  const coordinates = chartXCoordinates(points, width)
  points.forEach((point, index) => {
    if (point.value === null || !Number.isFinite(point.value)) {
      if (current) segments.push(current)
      current = ''
      return
    }
    const x = coordinates[index]
    const y = height - ((point.value - min) / (max - min || 1)) * height
    current += `${current ? ' L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`
  })
  if (current) segments.push(current)
  return segments
}
export function LineChart({
  points,
  unit = 'kW',
  label = '功率',
  secondaryLabel,
  height = 240,
}: {
  points: ChartPoint[]
  unit?: string
  label?: string
  secondaryLabel?: string
  height?: number
}) {
  const id = useId().replaceAll(':', '')
  const [hover, setHover] = useState<number | null>(null)
  const container = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(860)
  const valid = points.some((p) => p.value !== null && Number.isFinite(p.value))
  useEffect(() => {
    if (!container.current || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver((entries) => {
      const measured = entries[0]?.contentRect.width
      if (measured && measured > 0) setWidth(Math.max(230, Math.round(measured)))
    })
    observer.observe(container.current)
    return () => observer.disconnect()
  }, [valid])
  if (!valid)
    return (
      <EmptyState
        title="暂无可绘制的有效数据"
        description="缺测不会被填充为零；接入数据后将显示趋势。"
      />
    )
  const pad = 48,
    w = width - pad - 12,
    h = height - 50
  const finite = points
    .flatMap((p) => [p.value, p.secondary, p.lower, p.upper])
    .filter((v): v is number => typeof v === 'number' && Number.isFinite(v))
  const dataMin = Math.min(0, ...finite),
    dataMax = Math.max(0, ...finite)
  const span = dataMax - dataMin || 1
  const minimum = dataMin < 0 ? dataMin - span * 0.1 : 0
  const maximum = dataMax > 0 ? dataMax + span * 0.1 : dataMin === 0 ? 1 : 0
  const y = (value: number) => h - ((value - minimum) / (maximum - minimum)) * h
  const coordinates = chartXCoordinates(points, w)
  const x = (index: number) => coordinates[index]
  const segments = chartSegments(points, w, h, maximum, minimum)
  const secondary = chartSegments(
    points.map((p) => ({ ...p, value: p.secondary ?? null })),
    w,
    h,
    maximum,
    minimum,
  )
  const active = hover !== null ? points[hover] : undefined
  const area =
    segments.length === 1 && points.every((p) => p.value !== null && Number.isFinite(p.value))
      ? `${segments[0]} L${w},${y(0)} L0,${y(0)} Z`
      : null
  const band = points.every(
    (p) =>
      p.lower != null && p.upper != null && Number.isFinite(p.lower) && Number.isFinite(p.upper),
  )
    ? points.map((p, i) => `${x(i)},${y(p.upper!)}`).join(' ') +
      ' ' +
      [...points]
        .reverse()
        .map((p, i) => `${x(points.length - 1 - i)},${y(p.lower!)}`)
        .join(' ')
    : null
  return (
    <div ref={container} className="chart" style={{ minHeight: height }}>
      <div className="chart-legend">
        <span>
          <i className="legend-dot" />
          {label}
        </span>
        {secondaryLabel && (
          <span>
            <i className="legend-dot pale" />
            {secondaryLabel}
          </span>
        )}
        {band && (
          <span>
            <i className="legend-dot band" />
            预测区间
          </span>
        )}
        <small>
          {unit} · {browserTimezone()}
        </small>
      </div>
      <svg
        role="img"
        aria-label={`${label}趋势，共 ${points.length} 个时间点，单位 ${unit}。方向键可查看观测值`}
        tabIndex={0}
        onFocus={() => setHover(0)}
        onKeyDown={(event) => {
          if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
            event.preventDefault()
            setHover((current) =>
              Math.max(
                0,
                Math.min(points.length - 1, (current ?? 0) + (event.key === 'ArrowRight' ? 1 : -1)),
              ),
            )
          }
        }}
        viewBox={`0 0 ${w + pad + 12} ${h + 38}`}
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id={`area-${id}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--teal)" stopOpacity=".18" />
            <stop offset="100%" stopColor="var(--teal)" stopOpacity=".01" />
          </linearGradient>
        </defs>
        {[0, 1, 2, 3, 4].map((tick) => (
          <g key={tick}>
            <line
              x1={pad}
              y1={(tick / 4) * h}
              x2={w + pad}
              y2={(tick / 4) * h}
              stroke="var(--border)"
              strokeDasharray="3 5"
            />
            <text x={pad - 10} y={(tick / 4) * h + 4} textAnchor="end" className="chart-label">
              {formatNumber(maximum - (tick / 4) * (maximum - minimum), 1)}
            </text>
          </g>
        ))}
        <g transform={`translate(${pad} 0)`}>
          {band && <polygon points={band} fill="var(--teal)" opacity=".1" />}
          {area && <path d={area} fill={`url(#area-${id})`} />}
          {secondary.map((d, i) => (
            <path
              key={`s-${i}`}
              d={d}
              fill="none"
              stroke="var(--chart-secondary)"
              strokeWidth="2"
              strokeDasharray="5 5"
            />
          ))}
          {segments.map((d, i) => (
            <path
              key={i}
              d={d}
              fill="none"
              stroke="var(--teal)"
              strokeWidth="2.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ))}
          {points.length === 1 && (
            <circle cx={w / 2} cy={y(points[0].value || 0)} r="4" fill="var(--teal)" />
          )}
          {hover !== null && active?.value != null && Number.isFinite(active.value) && (
            <g>
              <line
                x1={x(hover)}
                y1="0"
                x2={x(hover)}
                y2={h}
                stroke="var(--text-muted)"
                strokeDasharray="3 3"
              />
              <circle
                cx={x(hover)}
                cy={y(active.value)}
                r="5"
                fill="var(--teal)"
                stroke="var(--surface)"
                strokeWidth="2"
              />
            </g>
          )}
          {points.map((_, index) => (
            <rect
              key={index}
              x={index === 0 ? 0 : (x(index - 1) + x(index)) / 2}
              y="0"
              width={
                (index === points.length - 1 ? w : (x(index) + x(index + 1)) / 2) -
                (index === 0 ? 0 : (x(index - 1) + x(index)) / 2)
              }
              height={h}
              fill="transparent"
              onMouseEnter={() => setHover(index)}
            />
          ))}
        </g>
        {[
          0,
          ...(width < 430 ? [] : [Math.floor((points.length - 1) / 4)]),
          Math.floor((points.length - 1) / 2),
          ...(width < 430 ? [] : [Math.floor((points.length - 1) * 0.75)]),
          points.length - 1,
        ]
          .filter((v, i, a) => a.indexOf(v) === i)
          .map((index) => (
            <text
              key={index}
              x={pad + x(index)}
              y={h + 28}
              textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
              className="chart-label"
            >
              {new Date(points[0].timestamp).toLocaleDateString() !==
              new Date(points[points.length - 1].timestamp).toLocaleDateString()
                ? formatDate(points[index].timestamp)
                : formatTime(points[index].timestamp)}
            </text>
          ))}
      </svg>
      {active && (
        <div className="chart-tooltip">
          {formatDate(active.timestamp)}
          <strong>
            {formatNumber(active.value)} {unit}
          </strong>
          {active.secondary != null && (
            <span>
              {secondaryLabel}: {formatNumber(active.secondary)} {unit}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
export function BarList({
  rows,
  unit = 'kWh',
  onClick,
}: {
  rows: { id: string; name: string; value: number | null; note?: string }[]
  unit?: string
  onClick?: (id: string) => void
}) {
  const max = Math.max(...rows.map((r) => r.value || 0), 0.001)
  return rows.length ? (
    <div className="bar-list">
      {rows.map((row, index) => (
        <button
          key={row.id}
          className="bar-row"
          disabled={!onClick}
          onClick={() => onClick?.(row.id)}
        >
          <span className="bar-rank">{String(index + 1).padStart(2, '0')}</span>
          <span className="bar-label">
            <span>{row.name}</span>
            <span className="bar-track">
              <span style={{ width: `${((row.value || 0) / max) * 100}%` }} />
            </span>
            {row.note && <small>{row.note}</small>}
          </span>
          <strong>
            {formatNumber(row.value)}
            <small>{unit}</small>
          </strong>
        </button>
      ))}
    </div>
  ) : (
    <EmptyState />
  )
}
export function Ring({
  ratio,
  label,
  size = 120,
}: {
  ratio: number | null
  label?: string
  size?: number
}) {
  const value = ratio === null || !Number.isFinite(ratio) ? null : Math.max(0, Math.min(1, ratio))
  return (
    <div className="ring" style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <circle
          cx="50"
          cy="50"
          r="43"
          fill="none"
          stroke="currentColor"
          opacity=".12"
          strokeWidth="7"
        />
        <circle
          cx="50"
          cy="50"
          r="43"
          fill="none"
          stroke="currentColor"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={`${(value || 0) * 270.18} 270.18`}
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div>
        <strong>{value === null ? '—' : `${Math.round(value * 100)}%`}</strong>
        {label && <span>{label}</span>}
      </div>
    </div>
  )
}
