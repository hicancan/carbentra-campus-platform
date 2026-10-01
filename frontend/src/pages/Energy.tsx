import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Activity, ArrowDownUp, CheckCheck, Gauge, Zap } from 'lucide-react'
import { useResource } from '../lib/hooks'
import { queryString } from '../lib/api'
import type { Balance, EnergyBreakdown, EnergySummary, Telemetry } from '../lib/types'
import { useScope } from '../lib/scope'
import { downloadJson, formatDate, formatNumber } from '../lib/format'
import {
  Badge,
  Card,
  CardHeader,
  DataTable,
  DefinitionList,
  ErrorState,
  ExportButton,
  Loading,
  Metric,
  Notice,
  PageHeader,
  SourceBadge,
  StatusBadge,
  Tabs,
} from '../components/ui'
import { BarList, LineChart } from '../components/charts'
import { BuildingFilter, initialRange, PeriodFilter } from '../components/Filters'
export default function Energy() {
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const building = params.get('building') || ''
  const [range, setRange] = useState(initialRange)
  const [group, setGroup] = useState('building')
  const [view, setView] = useState('ranking')
  const filters = { campus_id: scope.campusId, building_id: building, ...range }
  const summary = useResource<EnergySummary>(`/energy/summary${queryString(filters)}`)
  const breakdown = useResource<EnergyBreakdown[]>(
    `/energy/breakdown${queryString({ ...filters, group_by: group })}`,
  )
  const balance = useResource<Balance>(`/energy/balance${queryString(filters)}`)
  const telemetry = useResource<Telemetry[]>(
    `/telemetry${queryString({ campus_id: scope.campusId, building_id: building, ...range, limit: 120 })}`,
  )
  const d = summary.data
  return (
    <>
      <PageHeader
        eyebrow="ENERGY ANALYTICS"
        title="能耗分析"
        description="在明确的计量边界内核算用能，追踪缺测、覆盖与上下级平衡。"
        actions={
          <ExportButton
            onClick={() =>
              downloadJson(
                { scope: filters, summary: d, breakdown: breakdown.data, balance: balance.data },
                `energy-analysis-${new Date().toISOString().slice(0, 10)}.json`,
              )
            }
          />
        }
      />
      <div className="filter-bar">
        <BuildingFilter value={building} onChange={(id) => setParams(id ? { building: id } : {})} />
        <PeriodFilter value={range} onChange={setRange} />
      </div>
      {summary.error && (
        <ErrorState
          error={summary.error}
          retry={() => {
            void summary.refetch()
          }}
        />
      )}
      {summary.isLoading ? (
        <Loading />
      ) : (
        d && (
          <>
            <div className="metric-grid">
              <Metric
                label="统计期已知输入电量"
                value={d.known_kwh}
                unit="kWh"
                icon={<Zap size={19} />}
                accent
                note={
                  <>
                    <SourceBadge value={d.source_mode} />
                    <StatusBadge value={d.quality} />
                  </>
                }
              />
              <Metric
                label="有效数据覆盖"
                value={d.coverage_ratio == null ? null : d.coverage_ratio * 100}
                unit="%"
                icon={<CheckCheck size={19} />}
                note={`${d.interval_count} 个有效区间 · ${d.excluded_intervals} 个排除区间`}
              />
              <Metric
                label="已知输出电量"
                value={d.export_kwh}
                unit="kWh"
                icon={<ArrowDownUp size={19} />}
                note="输入与输出分别保留，不以净值掩盖反向电量"
              />
              <Metric
                label="纳入计量设备"
                value={d.device_count}
                unit="台"
                icon={<Gauge size={19} />}
                note="父子计量去重后的核算边界"
              />
            </div>
            {d.warnings.length > 0 && (
              <Notice tone="warning" title="核算边界提示">
                {d.warnings.join('；')}
              </Notice>
            )}
            <div className="two-col-grid energy-grid">
              <Card>
                <CardHeader
                  title="用能分布"
                  subtitle="仅展示服务端核算的已知电量"
                  actions={
                    <select
                      aria-label="用能分组维度"
                      value={group}
                      onChange={(e) => setGroup(e.target.value)}
                    >
                      <option value="building">按楼栋</option>
                      <option value="device">按设备</option>
                      <option value="circuit">按回路</option>
                    </select>
                  }
                />
                <Tabs
                  active={view}
                  onChange={setView}
                  items={[
                    { id: 'ranking', label: '排序视图' },
                    { id: 'table', label: '详细数据' },
                  ]}
                />
                {breakdown.isLoading ? (
                  <Loading />
                ) : breakdown.error ? (
                  <ErrorState error={breakdown.error} />
                ) : view === 'ranking' ? (
                  <BarList
                    rows={[...(breakdown.data || [])]
                      .sort((a, b) => (b.known_kwh ?? -1) - (a.known_kwh ?? -1))
                      .slice(0, 12)
                      .map((row) => ({
                        id: JSON.stringify(row.id),
                        name: row.name,
                        value: row.known_kwh,
                        note: `覆盖 ${formatNumber(row.coverage_ratio * 100)}%`,
                      }))}
                  />
                ) : (
                  <DataTable
                    rows={breakdown.data || []}
                    rowKey={(row) => JSON.stringify(row.id)}
                    columns={[
                      {
                        key: 'name',
                        title: '核算对象',
                        render: (row) => <strong>{row.name}</strong>,
                      },
                      {
                        key: 'energy',
                        title: '已知电量 / kWh',
                        render: (row) => formatNumber(row.known_kwh),
                      },
                      {
                        key: 'coverage',
                        title: '覆盖率',
                        render: (row) => `${formatNumber(row.coverage_ratio * 100)}%`,
                      },
                      {
                        key: 'quality',
                        title: '质量',
                        render: (row) => <StatusBadge value={row.quality} />,
                      },
                    ]}
                  />
                )}
              </Card>
              <div className="card-stack">
                <Card>
                  <CardHeader
                    title="计量平衡"
                    subtitle="父级与子级分别对照，避免重复叠加"
                    actions={<Activity size={19} className="text-muted" />}
                  />
                  {balance.isLoading ? (
                    <Loading compact />
                  ) : balance.error ? (
                    <ErrorState error={balance.error} compact />
                  ) : (
                    balance.data && (
                      <div className="card-pad">
                        <div className="balance-flow">
                          <div>
                            <span>父级计量</span>
                            <strong>
                              {formatNumber(balance.data.parent_kwh)}
                              <small>kWh</small>
                            </strong>
                          </div>
                          <ArrowDownUp size={24} />
                          <div>
                            <span>子级合计</span>
                            <strong>
                              {formatNumber(balance.data.children_kwh)}
                              <small>kWh</small>
                            </strong>
                          </div>
                        </div>
                        <div className="balance-result">
                          <span>残差</span>
                          <strong>{formatNumber(balance.data.residual_kwh)} kWh</strong>
                          <StatusBadge value={balance.data.quality} />
                        </div>
                        {balance.data.warnings.map((w, i) => (
                          <p key={i} className="text-muted small">
                            {w}
                          </p>
                        ))}
                      </div>
                    )
                  )}
                </Card>
                <Card>
                  <CardHeader title="可复核的核算口径" subtitle="每一份报告都保留相同口径" />
                  <div className="card-pad">
                    <DefinitionList
                      items={[
                        ['计算方法', d.method],
                        ['统计开始', formatDate(d.period_start)],
                        ['统计结束', formatDate(d.period_end)],
                        ['原始累计单位', 'Wh（计算后换算为 kWh）'],
                        ['无效区间', `${d.excluded_intervals} 个`],
                        ['来源模式', <SourceBadge value={d.source_mode} />],
                      ]}
                    />
                    <Notice>
                      观测中断、计数器重启与缺测区间不会自动插值为已知消耗。绝对用电量不等同于节能量。
                    </Notice>
                  </div>
                </Card>
              </div>
            </div>
            <Card>
              <CardHeader
                title="遥测观测样本"
                subtitle="按设备原始观测展示，避免将不同设备曲线误连为总负荷"
                actions={<Badge>最多 120 条最新样本</Badge>}
              />
              {telemetry.isLoading ? (
                <Loading />
              ) : telemetry.error ? (
                <ErrorState error={telemetry.error} />
              ) : (
                <div className="card-pad">
                  {telemetry.data?.length ? (
                    <>
                      <LineChart
                        label={`${telemetry.data[0].device_id} · 原始功率`}
                        unit="W"
                        points={telemetry.data
                          .filter((t) => t.device_id === telemetry.data![0].device_id)
                          .sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at))
                          .map((t) => ({
                            timestamp: t.observed_at,
                            value: t.quality === 'invalid' ? null : t.active_power_w,
                          }))}
                      />
                      <p className="small text-muted">
                        该曲线仅为设备 {telemetry.data[0].device_id}{' '}
                        的观测样本；校园聚合趋势见运行总览。
                      </p>
                    </>
                  ) : (
                    <Notice>当前时间范围没有原始遥测样本</Notice>
                  )}
                </div>
              )}
            </Card>
          </>
        )
      )}
    </>
  )
}
