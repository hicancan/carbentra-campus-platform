import {
  ArrowRight,
  ArrowUpRight,
  Bell,
  Building2,
  CircleDollarSign,
  Gauge,
  Leaf,
  RadioTower,
  ShieldCheck,
  Zap,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useResource } from '../lib/hooks'
import { permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { displayBuildingName } from '../lib/registry-display'
import type { Overview as OverviewData } from '../lib/types'
import { useScope } from '../lib/scope'
import { formatDate, formatNumber, formatTime } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Metric,
  PageHeader,
  RefreshButton,
  SkeletonCards,
  SourceBadge,
  StatusBadge,
} from '../components/ui'
import { BarList, LineChart, Ring } from '../components/charts'
export default function Overview() {
  const { campusId } = useScope()
  const auth = useAuth()
  const navigate = useNavigate()
  const query = useResource<OverviewData>(`/overview${queryString({ campus_id: campusId })}`)
  const d = query.data
  return (
    <>
      <PageHeader
        eyebrow="CAMPUS OVERVIEW"
        title="校园运行，一目了然"
        description="让空间、能源与行动连接起来，从这里掌握校园的每一次变化。"
        actions={
          <>
            <RefreshButton
              onClick={() => {
                void query.refetch()
              }}
              fetching={query.isFetching}
            />
            <Link className="button button-primary" to="/reports">
              <ArrowUpRight size={15} />
              {permissions.analyze(auth.session?.user.role) ? '生成运行报告' : '查看运行报告'}
            </Link>
          </>
        }
      />
      {query.error && (
        <ErrorState
          error={query.error}
          retry={() => {
            void query.refetch()
          }}
        />
      )}
      {query.isLoading ? (
        <SkeletonCards />
      ) : (
        d && (
          <>
            <section className="overview-hero">
              <div className="hero-copy">
                <div className="hero-eyebrow">
                  <span
                    className={`live-dot freshness-${d.freshness.status}`}
                    title={`数据新鲜度：${d.freshness.status}`}
                  />
                  CAMPUS ENERGY INTELLIGENCE
                  <SourceBadge value={d.source_mode} />
                </div>
                <h2>
                  看见能量的流动，
                  <br />
                  迈向更可持续的校园。
                </h2>
                <p>
                  {formatNumber(d.counts.buildings, 0)} 份建筑档案 ·{' '}
                  {formatNumber(d.counts.spaces, 0)} 个空间条目 ·{' '}
                  {formatNumber(d.counts.devices, 0)} 台登记设备
                </p>
                <Link to="/campus" className="hero-link">
                  探索校园空间
                  <ArrowRight size={16} />
                </Link>
              </div>
              <div className="hero-orbit" aria-hidden="true">
                <div className="orbit-one" />
                <div className="orbit-two" />
                <div className="orbit-core">
                  <Leaf size={52} />
                </div>
                <span className="orbit-node node-one">
                  <Building2 size={19} />
                </span>
                <span className="orbit-node node-two">
                  <Zap size={19} />
                </span>
                <span className="orbit-node node-three">
                  <RadioTower size={19} />
                </span>
              </div>
              <div className="hero-quality">
                <Ring ratio={d.energy.coverage_ratio} label="有效数据覆盖" size={118} />
                <span>已知计量区间</span>
                <small>缺测始终保持未知</small>
              </div>
            </section>
            <div className="metric-grid">
              <Metric
                label="统计期已知用电"
                value={d.energy.known_kwh}
                unit="kWh"
                icon={<Zap size={19} />}
                note={
                  <>
                    <SourceBadge value={d.energy.source_mode} />
                    <StatusBadge value={d.energy.quality} />
                    <span>{formatDate(d.energy.period_start)} 起</span>
                  </>
                }
                accent
              />
              <Metric
                label="当前总有功功率"
                value={d.power.active_kw}
                unit="kW"
                icon={<Gauge size={19} />}
                note={
                  <>
                    <SourceBadge value={d.power.source_mode} />
                    <StatusBadge value={d.power.quality} />
                    <span>排除上下级重复计量</span>
                  </>
                }
              />
              <Metric
                label="位置法碳排放"
                value={d.carbon.kg_co2e}
                unit="kgCO₂e"
                icon={<Leaf size={19} />}
                note={
                  <>
                    <StatusBadge value={d.carbon.quality} />
                    <span>核算值，非减排量</span>
                  </>
                }
              />
              <Metric
                label="估算用能成本"
                value={d.cost.amount}
                unit={d.cost.currency || '—'}
                icon={<CircleDollarSign size={19} />}
                note={
                  <>
                    <StatusBadge value={d.cost.quality} />
                    <span>按有效电价版本计算</span>
                  </>
                }
              />
            </div>
            <div className="overview-main-grid">
              <Card>
                <CardHeader
                  title="能源运行趋势"
                  subtitle="有效观测点聚合 · 无效或缺失数据不补零"
                  actions={<Badge tone="teal">有功功率 · kW</Badge>}
                />
                <div className="chart-pad">
                  <LineChart
                    points={d.trend.map((t) => ({ timestamp: t.timestamp, value: t.active_kw }))}
                    height={250}
                  />
                </div>
                <div className="chart-footer">
                  <span>
                    <span className="live-dot" />
                    最近观测 {formatTime(d.freshness.latest_sample_at)}
                  </span>
                  <Link to="/energy">
                    查看能耗分析
                    <ArrowRight size={14} />
                  </Link>
                </div>
              </Card>
              <Card>
                <CardHeader
                  title="待办与告警"
                  subtitle="先处理重要的事情"
                  actions={
                    <Badge tone={d.counts.active_alarms ? 'amber' : 'teal'}>
                      {d.counts.active_alarms} 项待处理
                    </Badge>
                  }
                />
                <div className="alarm-preview">
                  {d.alarms.slice(0, 4).map((alarm) => (
                    <Link to={`/alarms?alarm=${encodeURIComponent(alarm.id)}`} key={alarm.id}>
                      <span className={`alarm-icon severity-${alarm.severity}`}>
                        <Bell size={17} />
                      </span>
                      <div>
                        <strong>
                          <SourceBadge value={alarm.source_mode} /> {alarm.title}
                        </strong>
                        <span>
                          {formatDate(alarm.created_at)} · {alarm.device_id}
                        </span>
                      </div>
                      <ArrowUpRight size={14} />
                    </Link>
                  ))}
                  {!d.alarms.length && (
                    <EmptyState
                      title="当前没有待处理告警"
                      description="保持关注数据质量与设备在线状态"
                      icon={<ShieldCheck size={28} />}
                    />
                  )}
                </div>
                <div className="card-bottom">
                  <Link to="/alarms">
                    打开告警工作台
                    <ArrowRight size={14} />
                  </Link>
                </div>
              </Card>
            </div>
            <div className="overview-bottom-grid">
              <Card>
                <CardHeader
                  title="楼宇用能排行"
                  subtitle="按统计期已知电量排序"
                  actions={
                    <Link className="text-link" to="/energy">
                      全部楼宇
                      <ArrowUpRight size={14} />
                    </Link>
                  }
                />
                <BarList
                  rows={[...d.buildings]
                    .sort((a, b) => (b.known_kwh ?? -1) - (a.known_kwh ?? -1))
                    .slice(0, 5)
                    .map((b) => ({
                      id: b.id,
                      name: displayBuildingName(b.name),
                      value: b.known_kwh,
                      note: `${b.device_count} 台设备${b.alarm_count ? ` · ${b.alarm_count} 条告警` : ''}`,
                    }))}
                  onClick={(id) => navigate(`/campus?building=${encodeURIComponent(id)}`)}
                />
              </Card>
              <Card>
                <CardHeader
                  title="连接健康度"
                  subtitle="云边端运行的可信基础"
                  actions={<RadioTower size={19} className="text-muted" />}
                />
                <div className="health-layout">
                  <Ring
                    ratio={d.counts.devices ? d.counts.online_devices / d.counts.devices : null}
                    label="设备在线率"
                    size={136}
                  />
                  <div className="health-counts">
                    <div>
                      <span>
                        <i className="health-dot teal" />
                        在线
                      </span>
                      <strong>{d.counts.online_devices}</strong>
                    </div>
                    <div>
                      <span>
                        <i className="health-dot amber" />
                        数据过期
                      </span>
                      <strong>{d.counts.stale_devices}</strong>
                    </div>
                    <div>
                      <span>
                        <i className="health-dot gray" />
                        离线
                      </span>
                      <strong>{d.counts.offline_devices}</strong>
                    </div>
                    {!!d.counts.unknown_devices && (
                      <div>
                        <span>
                          <i className="health-dot" />
                          未见观测
                        </span>
                        <strong>{d.counts.unknown_devices}</strong>
                      </div>
                    )}
                  </div>
                </div>
                <div className="quality-strip">
                  <ShieldCheck size={17} />
                  <div>
                    <strong>
                      数据新鲜度 <StatusBadge value={d.freshness.status} />
                    </strong>
                    <small>
                      更新于 {formatDate(d.generated_at)} · 阈值 {d.freshness.stale_after_seconds}{' '}
                      秒
                    </small>
                  </div>
                </div>
              </Card>
              <Card className="operations-card">
                <div className="eyebrow">QUICK ACTIONS</div>
                <h2>常用操作</h2>
                <p>继续处理当前校区的设备、告警与分析任务</p>
                <Button variant="ghost" onClick={() => navigate('/devices')}>
                  <Zap size={15} />
                  设备台账
                  <ArrowRight size={14} />
                </Button>
                <Button variant="ghost" onClick={() => navigate('/alarms')}>
                  <Bell size={15} />
                  {permissions.operate(auth.session?.user.role) ? '处理待办告警' : '查看告警'}
                  <span>{d.counts.active_alarms}</span>
                  <ArrowRight size={14} />
                </Button>
                <Button variant="ghost" onClick={() => navigate('/strategies')}>
                  <Gauge size={15} />
                  预测与策略
                  <ArrowRight size={14} />
                </Button>
                <Button variant="ghost" onClick={() => navigate('/reports')}>
                  <ArrowUpRight size={15} />
                  {permissions.analyze(auth.session?.user.role) ? '生成运行报告' : '查看运行报告'}
                  <ArrowRight size={14} />
                </Button>
              </Card>
            </div>
          </>
        )
      )}
    </>
  )
}
