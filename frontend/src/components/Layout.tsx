import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  ArrowUpRight,
  Bell,
  CalendarDays,
  Building2,
  DoorOpen,
  ChartNoAxesCombined,
  Check,
  ChevronDown,
  ChevronRight,
  FileChartColumn,
  Gauge,
  Leaf,
  LogOut,
  Menu,
  Moon,
  Network,
  Search,
  Settings2,
  Sun,
  Terminal,
  Workflow,
  X,
  Zap,
} from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useScope } from '../lib/scope'
import { useDebounced, useLiveEvents, useResource } from '../lib/hooks'
import { queryString } from '../lib/api'
import type { Building, Device } from '../lib/types'
import { readTheme, writeTheme } from '../lib/preferences'
import { roleLabel } from '../lib/format'
import { Badge, Button, ErrorState, IconButton, Loading } from './ui'
export const navigation = [
  { path: '/', name: '运行总览', english: 'Overview', icon: Gauge },
  { path: '/campus', name: '校园空间', english: 'Campus', icon: Building2 },
  { path: '/classrooms', name: '教室工作台', english: 'Classrooms', icon: DoorOpen },
  { path: '/schedules', name: '空间计划与检修', english: 'Calendar', icon: CalendarDays },
  { path: '/energy', name: '能耗分析', english: 'Energy', icon: ChartNoAxesCombined },
  { path: '/carbon', name: '碳与成本', english: 'Accounting', icon: Leaf },
  { path: '/devices', name: '设备与边缘', english: 'Devices', icon: Zap },
  { path: '/topology', name: '配电拓扑', english: 'Topology', icon: Network },
  { path: '/alarms', name: '告警工单', english: 'Alarms', icon: Bell },
  { path: '/strategies', name: '预测与策略', english: 'Intelligence', icon: Workflow },
  { path: '/commands', name: '命令追踪', english: 'Commands', icon: Terminal },
  { path: '/reports', name: '报表与审计', english: 'Reports', icon: FileChartColumn },
  { path: '/system', name: '系统管理', english: 'System', icon: Settings2 },
]
function CommandPalette({ onClose }: { onClose: () => void }) {
  const scope = useScope()
  const dialogRef = useRef<HTMLDivElement>(null)
  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const navigate = useNavigate()
  const buildings = useResource<Building[]>(
    `/buildings${queryString({ q, campus_id: scope.campusId, limit: 8 })}`,
    {
      enabled: !!q,
      interval: false,
    },
  )
  const devices = useResource<Device[]>(
    `/devices${queryString({ q, campus_id: scope.campusId, limit: 8 })}`,
    {
      enabled: !!q,
      interval: false,
    },
  )
  const go = (path: string) => {
    navigate(path)
    onClose()
  }
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const nodes = dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not([disabled]),input,a[href]',
        )
        if (!nodes?.length) return
        const first = nodes[0],
          last = nodes[nodes.length - 1]
        if (event.shiftKey && document.activeElement === first) {
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
      window.removeEventListener('keydown', key)
      document.body.style.overflow = overflow
      previous?.focus()
    }
  }, [onClose])
  return (
    <div
      className="palette-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={dialogRef}
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="全局搜索"
      >
        <div className="palette-input">
          <Search size={20} />
          <input
            aria-label="搜索页面、楼栋或设备"
            autoFocus
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索页面、楼栋或设备…"
          />
          <button onClick={onClose}>ESC</button>
        </div>
        <div className="palette-results">
          <div className="eyebrow">快速导航</div>
          {navigation
            .filter((n) => `${n.name}${n.english}`.toLowerCase().includes(search.toLowerCase()))
            .map((n) => (
              <button key={n.path} onClick={() => go(n.path)}>
                <n.icon size={18} />
                <span>{n.name}</span>
                <ChevronRight size={15} />
              </button>
            ))}
          {q && (
            <>
              <div className="eyebrow">楼栋与设备</div>
              {(buildings.isLoading || devices.isLoading) && <Loading compact />}
              {(buildings.error || devices.error) && (
                <ErrorState error={buildings.error || devices.error} compact />
              )}
              {buildings.data?.map((b) => (
                <button
                  key={b.id}
                  onClick={() => go(`/campus?building=${encodeURIComponent(b.id)}`)}
                >
                  <Building2 size={18} />
                  <span>
                    {b.name}
                    <small>校园楼栋</small>
                  </span>
                  <ArrowUpRight size={15} />
                </button>
              ))}
              {devices.data?.map((d) => (
                <button
                  key={d.id}
                  onClick={() => go(`/devices?device=${encodeURIComponent(d.id)}`)}
                >
                  <Zap size={18} />
                  <span>
                    {d.name}
                    <small>{d.id}</small>
                  </span>
                  <ArrowUpRight size={15} />
                </button>
              ))}
              {!buildings.isLoading &&
                !devices.isLoading &&
                !buildings.data?.length &&
                !devices.data?.length && <p className="text-muted">没有匹配的楼栋或设备</p>}
            </>
          )}
        </div>
        <div className="palette-footer">
          <Search size={13} />
          Tab 选择 · Enter 打开 · Esc 关闭
        </div>
      </div>
    </div>
  )
}
export default function Layout() {
  const auth = useAuth()
  const scope = useScope()
  const location = useLocation()
  const navigate = useNavigate()
  const live = useLiveEvents()
  const [menu, setMenu] = useState(false)
  const [palette, setPalette] = useState(false)
  const [theme, setTheme] = useState(readTheme)
  const [logoutError, setLogoutError] = useState<unknown>(null)
  const [loggingOut, setLoggingOut] = useState(false)
  const current = navigation.find(
    (n) =>
      n.path === location.pathname ||
      (n.path === '/classrooms' && location.pathname.startsWith('/classrooms/')),
  )
  useEffect(() => {
    setMenu(false)
  }, [location.pathname])
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    writeTheme(theme)
  }, [theme])
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setPalette((v) => !v)
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        跳转到主要内容
      </a>
      {menu && (
        <button className="mobile-scrim" aria-label="关闭导航" onClick={() => setMenu(false)} />
      )}
      <aside className={`sidebar ${menu ? 'open' : ''}`}>
        <Link className="brand" to="/">
          <span className="brand-mark">
            <Leaf size={23} />
          </span>
          <div>
            <strong>碳迹未来</strong>
            <span>CARBENTRA CAMPUS</span>
          </div>
        </Link>
        <div className="workspace-label">
          <span className="workspace-icon">
            <Building2 size={15} />
          </span>
          <div>
            <strong>高校能碳工作空间</strong>
            <small>Campus operations</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <nav aria-label="主要导航">
          <div className="nav-caption">工作空间</div>
          {navigation.slice(0, 6).map((n) => (
            <NavLink end={n.path === '/'} to={n.path} key={n.path}>
              <n.icon size={18} />
              <span>{n.name}</span>
              {n.path === '/' && <span className="nav-active-dot" />}
            </NavLink>
          ))}
          <div className="nav-caption">运营与控制</div>
          {navigation.slice(6, 11).map((n) => (
            <NavLink to={n.path} key={n.path}>
              <n.icon size={18} />
              <span>{n.name}</span>
            </NavLink>
          ))}
          <div className="nav-caption">治理与交付</div>
          {navigation.slice(11).map((n) => (
            <NavLink to={n.path} key={n.path}>
              <n.icon size={18} />
              <span>{n.name}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>
            Powered by <b>CARBENTRA</b>
          </span>
          <span>v1.0</span>
        </div>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <div className="topbar-start">
            <IconButton label={menu ? '关闭导航' : '打开导航'} onClick={() => setMenu((v) => !v)}>
              {menu ? <X size={20} /> : <Menu size={20} />}
            </IconButton>
            <span className="breadcrumb-root">工作空间</span>
            <ChevronRight size={13} />
            <span>{current?.name || '页面'}</span>
          </div>
          <div className="topbar-end">
            <button className="global-search" onClick={() => setPalette(true)}>
              <Search size={15} />
              <span>搜索任何内容</span>
              <kbd>⌘ K</kbd>
            </button>
            <Badge tone={live === 'live' ? 'teal' : live === 'polling' ? 'amber' : 'muted'} dot>
              {live === 'live' ? '实时连接' : live === 'polling' ? '实时断开 · 轮询' : '连接中'}
            </Badge>
            <IconButton
              label={theme === 'light' ? '切换深色主题' : '切换浅色主题'}
              onClick={() => setTheme((v) => (v === 'light' ? 'dark' : 'light'))}
            >
              {theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}
            </IconButton>
            <details className="account-menu">
              <summary>
                <span className="avatar">
                  {(auth.session?.user.display_name || 'U').slice(0, 1)}
                </span>
                <ChevronDown size={12} />
              </summary>
              <div className="account-popover">
                <strong>{auth.session?.user.display_name}</strong>
                <span>{roleLabel(auth.session?.user.role)}</span>
                <small>
                  <Check size={12} />
                  安全会话已启用
                </small>
                {!!logoutError && <ErrorState error={logoutError} compact />}
                <Button
                  onClick={async () => {
                    setLoggingOut(true)
                    try {
                      await auth.logout()
                    } catch (e) {
                      setLogoutError(e)
                    } finally {
                      setLoggingOut(false)
                    }
                  }}
                  loading={loggingOut}
                >
                  <LogOut size={14} />
                  退出登录
                </Button>
              </div>
            </details>
          </div>
        </header>
        <div className="scope-bar">
          <div>
            <span className="scope-label">当前范围</span>
            <Building2 size={14} />
            <select
              aria-label="选择校区"
              value={scope.campusId}
              disabled={location.pathname === '/system'}
              title={
                location.pathname === '/system'
                  ? '系统页面展示全局运行状态与账户授权，不按此筛选'
                  : '选择校区范围'
              }
              onChange={(event) => {
                scope.setCampusId(event.target.value)
                navigate({
                  pathname: location.pathname.startsWith('/classrooms/')
                    ? '/classrooms'
                    : location.pathname,
                  search: '',
                })
              }}
            >
              <option value="">全部可访问校区</option>
              {scope.campuses.map((campus) => (
                <option key={campus.id} value={campus.id}>
                  {campus.name}
                </option>
              ))}
            </select>
          </div>
          <span>
            <Activity size={13} />
            以服务端时间与数据质量为准
          </span>
        </div>
        <main id="main-content" className="page-content">
          {!!auth.error && <ErrorState error={auth.error} retry={auth.refresh} compact />}
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>碳迹未来 · 基于 AIoT 云边端协同的高校智慧能碳管理平台</span>
          <Link to="/system">系统状态与平台资料</Link>
        </footer>
      </div>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
    </div>
  )
}
