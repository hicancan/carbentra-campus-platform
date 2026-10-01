import { apiErrorMessage } from '../lib/error-messages'
import { useEffect, useRef } from 'react'
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react'
import {
  AlertCircle,
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  Check,
  CircleHelp,
  Inbox,
  LoaderCircle,
  RefreshCw,
  X,
} from 'lucide-react'
import { ApiError } from '../lib/api'
import { formatNumber, statusLabel, statusTone } from '../lib/format'
export function Button({
  variant = 'secondary',
  type = 'button',
  className = '',
  children,
  loading,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  loading?: boolean
}) {
  return (
    <button
      className={`button button-${variant} ${className}`}
      type={type}
      {...props}
      disabled={props.disabled || loading}
    >
      {loading && <LoaderCircle size={16} className="spin" />}
      {children}
    </button>
  )
}
export function IconButton({
  label,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button className="icon-button" type="button" title={label} aria-label={label} {...props}>
      {children}
    </button>
  )
}
export function Badge({
  children,
  tone = 'muted',
  dot = false,
}: {
  children: ReactNode
  tone?: 'teal' | 'amber' | 'red' | 'blue' | 'muted'
  dot?: boolean
}) {
  return (
    <span className={`badge badge-${tone}`}>
      {dot && <span className="badge-dot" />}
      {children}
    </span>
  )
}
export function StatusBadge({ value }: { value?: string | null }) {
  return (
    <Badge tone={statusTone(value)} dot>
      {statusLabel(value)}
    </Badge>
  )
}
export function SourceBadge({ value }: { value?: string | null }) {
  return <Badge tone={statusTone(value)}>{value || 'UNKNOWN'}</Badge>
}
export function Card({ className = '', children, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section className={`card ${className}`} {...props}>
      {children}
    </section>
  )
}
export function CardHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  eyebrow?: string
}) {
  return (
    <div className="card-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="card-actions">{actions}</div>}
    </div>
  )
}
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string
  title: string
  description: string
  actions?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="page-actions">{actions}</div>
    </div>
  )
}
export function Metric({
  label,
  value,
  unit,
  icon,
  note,
  accent = false,
}: {
  label: string
  value: number | null | undefined
  unit?: string
  icon: ReactNode
  note?: ReactNode
  accent?: boolean
}) {
  return (
    <Card className={`metric ${accent ? 'metric-accent' : ''}`}>
      <div className="metric-top">
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <div className="metric-value">
        {formatNumber(value)}
        <span>{unit}</span>
      </div>
      <div className="metric-note">{note || '未知数据不参与估算'}</div>
    </Card>
  )
}
export function Loading({
  label = '正在读取数据…',
  compact = false,
}: {
  label?: string
  compact?: boolean
}) {
  return (
    <div role="status" className={`loading-state ${compact ? 'compact' : ''}`}>
      <LoaderCircle className="spin" size={24} />
      <span>{label}</span>
    </div>
  )
}
export function SkeletonCards({ count = 4 }: { count?: number }) {
  return (
    <div className="metric-grid" aria-label="正在加载指标" aria-busy="true">
      {Array.from({ length: count }, (_, index) => (
        <div className="card skeleton-card" key={index}>
          <div className="skeleton skeleton-line" />
          <div className="skeleton skeleton-number" />
          <div className="skeleton skeleton-line small" />
        </div>
      ))}
    </div>
  )
}
export function ErrorState({
  error,
  retry,
  compact = false,
}: {
  error: unknown
  retry?: () => void
  compact?: boolean
}) {
  const e = error instanceof Error ? error : new Error('数据暂时不可用')
  const displayMessage =
    error instanceof ApiError ? apiErrorMessage(error.code, error.status, error.message) : e.message
  return (
    <div role="alert" className={`error-state ${compact ? 'compact' : ''}`}>
      <AlertCircle size={24} />
      <div>
        <strong>暂时无法完成请求</strong>
        <p>{displayMessage}</p>
        {error instanceof ApiError && error.fields.length > 0 && (
          <ul className="validation-errors">
            {error.fields.map((field, index) => (
              <li key={index}>
                {field.location}: {field.message}
              </li>
            ))}
          </ul>
        )}
        {error instanceof ApiError && error.requestId && <small>请求编号：{error.requestId}</small>}
        {error instanceof ApiError && displayMessage !== error.message && (
          <details className="technical-error">
            <summary>技术详情</summary>
            <code>{error.code}</code>
            <p>{error.message}</p>
          </details>
        )}
      </div>
      {retry && (
        <Button onClick={retry}>
          <RefreshCw size={14} />
          重试
        </Button>
      )}
    </div>
  )
}
export function EmptyState({
  title = '暂时没有数据',
  description = '试试调整筛选条件，或等待新的数据接入。',
  icon,
  action,
}: {
  title?: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      {icon || <Inbox size={30} />}
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}
export function Notice({
  children,
  tone = 'info',
  title,
}: {
  children: ReactNode
  tone?: 'info' | 'warning' | 'success'
  title?: string
}) {
  return (
    <div className={`notice notice-${tone}`}>
      {tone === 'success' ? (
        <Check size={18} />
      ) : tone === 'warning' ? (
        <AlertCircle size={18} />
      ) : (
        <CircleHelp size={18} />
      )}
      <div>
        {title && <strong>{title}</strong>}
        <div>{children}</div>
      </div>
    </div>
  )
}
export function Drawer({
  title,
  subtitle,
  children,
  onClose,
  wide = false,
}: {
  title: string
  subtitle?: string
  children: ReactNode
  onClose: () => void
  wide?: boolean
}) {
  const ref = useRef<HTMLDivElement>(null)
  const returnFocus = useRef<HTMLElement | null>(null)
  useEffect(() => {
    returnFocus.current = document.activeElement as HTMLElement
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    ref.current?.focus()
    const key = (event: KeyboardEvent) => {
      const dialogs = document.querySelectorAll('[role="dialog"]')
      if (dialogs[dialogs.length - 1] !== ref.current) return
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const nodes = ref.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex="0"]',
        )
        if (!nodes?.length) {
          event.preventDefault()
          return
        }
        const first = nodes[0]
        const last = nodes[nodes.length - 1]
        if (
          event.shiftKey &&
          (document.activeElement === first || document.activeElement === ref.current)
        ) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    window.addEventListener('keydown', key)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', key)
      returnFocus.current?.focus()
    }
  }, [onClose])
  return (
    <div
      className="overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`drawer ${wide ? 'drawer-wide' : ''}`}
      >
        <div className="drawer-header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <IconButton label="关闭详情" onClick={onClose}>
            <X size={20} />
          </IconButton>
        </div>
        <div className="drawer-body">{children}</div>
      </div>
    </div>
  )
}
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string
  children: ReactNode
  onClose: () => void
}) {
  return (
    <div className="modal-wrap">
      <Drawer title={title} onClose={onClose}>
        {children}
      </Drawer>
    </div>
  )
}
export function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  )
}
export function DefinitionList({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="definition-list">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  onRowClick,
  empty,
  selected,
}: {
  rows: T[]
  columns: { key: string; title: string; render: (row: T) => ReactNode; className?: string }[]
  rowKey: (row: T) => string
  onRowClick?: (row: T) => void
  empty?: ReactNode
  selected?: string
}) {
  if (!rows.length) return <>{empty || <EmptyState />}</>
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.className}>
                {c.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className={`${onRowClick ? 'clickable' : ''} ${selected === rowKey(row) ? 'selected' : ''}`}
              onClick={() => onRowClick?.(row)}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={(event) => {
                if (onRowClick && (event.key === 'Enter' || event.key === ' ')) {
                  event.preventDefault()
                  onRowClick(row)
                }
              }}
            >
              {columns.map((c) => (
                <td key={c.key} className={c.className}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
export function Pagination({
  offset,
  limit,
  total,
  setOffset,
}: {
  offset: number
  limit: number
  total: number
  setOffset: (offset: number) => void
}) {
  return (
    <div className="pagination">
      <span>
        {total ? `${offset + 1}–${Math.min(offset + limit, total)}` : '0'} / 共{' '}
        {formatNumber(total, 0)} 条
      </span>
      <div>
        <IconButton
          label="上一页"
          disabled={offset === 0}
          onClick={() => setOffset(Math.max(0, offset - limit))}
        >
          <ArrowLeft size={16} />
        </IconButton>
        <IconButton
          label="下一页"
          disabled={offset + limit >= total}
          onClick={() => setOffset(offset + limit)}
        >
          <ArrowRight size={16} />
        </IconButton>
      </div>
    </div>
  )
}
export function RefreshButton({ onClick, fetching }: { onClick: () => void; fetching?: boolean }) {
  return (
    <Button onClick={onClick} loading={fetching}>
      {!fetching && <RefreshCw size={15} />}刷新
    </Button>
  )
}
export function ExportButton({ onClick, loading }: { onClick: () => void; loading?: boolean }) {
  return (
    <Button onClick={onClick} loading={loading}>
      <ArrowDownToLine size={15} />
      导出
    </Button>
  )
}
export function JsonView({ value }: { value: unknown }) {
  return <pre className="json-view">{JSON.stringify(value, null, 2)}</pre>
}
export function Tabs({
  items,
  active,
  onChange,
}: {
  items: { id: string; label: string; count?: number }[]
  active: string
  onChange: (id: string) => void
}) {
  return (
    <div className="tabs" role="tablist">
      {items.map((item) => (
        <button
          role="tab"
          aria-selected={active === item.id}
          className={active === item.id ? 'active' : ''}
          key={item.id}
          onClick={() => onChange(item.id)}
        >
          {item.label}
          {item.count !== undefined && <span>{item.count}</span>}
        </button>
      ))}
    </div>
  )
}
