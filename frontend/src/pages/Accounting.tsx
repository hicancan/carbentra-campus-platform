import { IDENTIFIER_PATTERN } from '../lib/input-patterns'
import { useCallback, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CircleDollarSign, FileCheck2, Leaf, Plus, Scale, ShieldCheck } from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { CarbonSummary, CostSummary, Factor, Tariff } from '../lib/types'
import TariffBands from '../components/TariffBands'
import type { CostAllocationMode, DraftRateBand } from '../lib/pricing'
import { minuteClock, parseRateBands } from '../lib/pricing'
import { formatDate, formatNumber } from '../lib/format'
import {
  Button,
  Card,
  CardHeader,
  DataTable,
  DefinitionList,
  ErrorState,
  Field,
  Loading,
  Metric,
  Modal,
  Notice,
  PageHeader,
  SourceBadge,
  StatusBadge,
  Tabs,
} from '../components/ui'
import { BuildingFilter, initialRange, PeriodFilter } from '../components/Filters'
function VersionForm({ kind, onClose }: { kind: 'factor' | 'tariff'; onClose: () => void }) {
  const client = useQueryClient()
  const [name, setName] = useState('')
  const [rate, setRate] = useState('')
  const [currency, setCurrency] = useState('CNY')
  const [timezone, setTimezone] = useState('Asia/Shanghai')
  const [bands, setBands] = useState<DraftRateBand[]>([])
  const bandValidation = parseRateBands(bands)
  const [region, setRegion] = useState('')
  const [year, setYear] = useState(new Date().getFullYear())
  const [source, setSource] = useState('')
  const [validFrom, setValidFrom] = useState(new Date().toISOString().slice(0, 16))
  const [version, setVersion] = useState(1)
  const [id, setId] = useState('')
  const [validTo, setValidTo] = useState(
    new Date(new Date().getFullYear() + 1, 0, 1).toISOString().slice(0, 16),
  )
  const [mode, setMode] = useState('SIMULATED')
  const mutation = useMutation({
    mutationFn: () =>
      api.post(kind === 'factor' ? '/carbon/factors' : '/tariffs', {
        id,
        name,
        ...(kind === 'factor'
          ? { region, year, kg_co2e_per_kwh: Number(rate) }
          : { currency, rate_per_kwh: Number(rate), timezone, bands: bandValidation.bands }),
        valid_from: new Date(`${validFrom}Z`).toISOString(),
        valid_to: new Date(`${validTo}Z`).toISOString(),
        source_url: source,
        source_mode: mode,
        version,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Modal title={kind === 'factor' ? '登记排放因子版本' : '登记电价版本'} onClose={onClose}>
      <Notice>新增版本保留历史。请使用可核验来源，真实因子与模拟参数需明确区分。</Notice>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          if (kind === 'tariff' && bandValidation.error) return
          mutation.mutate()
        }}
      >
        <Field label="稳定版本 ID">
          <input
            value={id}
            onChange={(e) => setId(e.target.value)}
            required
            pattern={IDENTIFIER_PATTERN}
            maxLength={100}
            placeholder="例如 factor-cn-2026-v1"
          />
        </Field>
        <Field label="名称">
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        </Field>
        <div className="form-grid">
          <Field
            label={kind === 'factor' ? '排放系数（kgCO₂e/kWh）' : `基础电量单价（${currency}/kWh）`}
          >
            <input
              type="number"
              min="0"
              max={kind === 'factor' ? 10 : 1000}
              step="0.000001"
              required
              value={rate}
              onChange={(e) => setRate(e.target.value)}
            />
          </Field>
          <Field label="版本标识">
            <input
              type="number"
              min="1"
              max="2147483647"
              step="1"
              value={version}
              onChange={(e) => setVersion(Number(e.target.value))}
              required
            />
          </Field>
        </div>
        {kind === 'factor' && (
          <div className="form-grid">
            <Field label="适用地区">
              <input value={region} onChange={(e) => setRegion(e.target.value)} required />
            </Field>
            <Field label="核算年份">
              <input
                type="number"
                value={year}
                min="2000"
                max="2100"
                onChange={(e) => setYear(Number(e.target.value))}
                required
              />
            </Field>
          </div>
        )}
        {kind === 'tariff' && (
          <>
            <div className="form-grid">
              <Field label="电价日历时区（IANA）">
                <input
                  required
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  maxLength={80}
                  list="tariff-timezones"
                />
                <datalist id="tariff-timezones">
                  <option value="Asia/Shanghai" />
                  <option value="Etc/UTC" />
                  <option value="Europe/London" />
                  <option value="America/New_York" />
                </datalist>
              </Field>
              <Field label="币种">
                <input
                  required
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  pattern="[A-Z]{3}"
                  maxLength={3}
                />
              </Field>
            </div>
            <TariffBands value={bands} onChange={setBands} currency={currency} />
          </>
        )}
        <Field label="来源链接">
          <input
            type="url"
            pattern="https://.*"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            required
            placeholder="https://…"
          />
        </Field>
        <div className="form-grid">
          <Field label="生效时间（UTC）">
            <input
              type="datetime-local"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
              required
            />
          </Field>
          <Field label="截止时间（UTC，不含）">
            <input
              type="datetime-local"
              value={validTo}
              min={validFrom}
              onChange={(e) => setValidTo(e.target.value)}
              required
            />
          </Field>
          <Field label="来源模式">
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="SIMULATED">SIMULATED · 模拟参数</option>
              <option value="REAL">REAL · 真实公开参数</option>
            </select>
          </Field>
        </div>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button onClick={onClose} type="button">
            取消
          </Button>
          <Button
            variant="primary"
            type="submit"
            disabled={kind === 'tariff' && !!bandValidation.error}
            loading={mutation.isPending}
          >
            登记新版本
          </Button>
        </div>
      </form>
    </Modal>
  )
}
export default function Accounting() {
  const auth = useAuth()
  const scope = useScope()
  const [building, setBuilding] = useState('')
  const [range, setRange] = useState(initialRange)
  const [tab, setTab] = useState('factors')
  const [allocation, setAllocation] = useState<CostAllocationMode>('strict')
  const [form, setForm] = useState<'factor' | 'tariff' | null>(null)
  const close = useCallback(() => setForm(null), [])
  const filter = queryString({ campus_id: scope.campusId, building_id: building, ...range })
  const carbon = useResource<CarbonSummary>(`/carbon/summary${filter}`)
  const cost = useResource<CostSummary>(
    `/cost/summary${queryString({ campus_id: scope.campusId, building_id: building, ...range, allocation_mode: allocation })}`,
  )
  const factors = useResource<Factor[]>('/carbon/factors?limit=500')
  const tariffs = useResource<Tariff[]>('/tariffs?limit=500')
  return (
    <>
      <PageHeader
        eyebrow="CARBON & COST"
        title="碳与成本核算"
        description="以版本化排放因子与电价，将可信电量转化为可复核的运营指标。"
        actions={<SourceBadge value={carbon.data?.source_mode} />}
      />
      <div className="filter-bar">
        <BuildingFilter value={building} onChange={setBuilding} />
        <PeriodFilter value={range} onChange={setRange} />
        <select
          aria-label="电费跨价窗处理"
          value={allocation}
          onChange={(e) => setAllocation(e.target.value as CostAllocationMode)}
        >
          <option value="strict">严格定价（默认）</option>
          <option value="proportional_estimate">按区间时长分摊（估算）</option>
        </select>
      </div>
      {(carbon.error || cost.error) && (
        <ErrorState
          error={carbon.error || cost.error}
          retry={() => {
            void carbon.refetch()
            void cost.refetch()
          }}
        />
      )}
      {carbon.isLoading || cost.isLoading ? (
        <Loading />
      ) : (
        <>
          <div className="metric-grid">
            <Metric
              label="位置法排放量"
              value={carbon.data?.kg_co2e}
              unit="kgCO₂e"
              icon={<Leaf size={19} />}
              accent
              note={<StatusBadge value={carbon.data?.quality} />}
            />
            <Metric
              label="配置电量电费估算"
              value={cost.data?.amount}
              unit={cost.data?.currency || '—'}
              icon={<CircleDollarSign size={19} />}
              note={<StatusBadge value={cost.data?.quality} />}
            />
            <Metric
              label="核算已知电量"
              value={carbon.data?.known_kwh}
              unit="kWh"
              icon={<Scale size={19} />}
              note="继承计量边界与有效区间"
            />
            <Metric
              label="电量数据覆盖"
              value={carbon.data?.coverage_ratio == null ? null : carbon.data.coverage_ratio * 100}
              unit="%"
              icon={<FileCheck2 size={19} />}
              note="覆盖不足时核算结果同样不完整"
            />
          </div>
          <Notice tone="info" title="核算边界">
            碳排放是位置法核算结果，不是已实现减排量。模拟用能、模拟排放因子或模拟电价均不能作为实际账单或履约证明。电费仅按已配置电量单价估算，不含另行计收的需量、容量或固定服务等费用。
          </Notice>
          <div className="two-col-grid">
            <Card>
              <CardHeader
                title="碳核算链路"
                subtitle="已知电量 × 生效排放系数"
                actions={<Leaf size={19} className="text-teal" />}
              />
              <div className="card-pad">
                <div className="formula">
                  <strong>
                    {formatNumber(carbon.data?.known_kwh)}
                    <small>kWh</small>
                  </strong>
                  <span>×</span>
                  <strong>
                    {formatNumber(carbon.data?.factor?.kg_co2e_per_kwh, 4)}
                    <small>kgCO₂e/kWh</small>
                  </strong>
                  <span>=</span>
                  <strong className="text-teal">
                    {formatNumber(carbon.data?.kg_co2e)}
                    <small>kgCO₂e</small>
                  </strong>
                </div>
                <DefinitionList
                  items={[
                    ['方法', '位置法 Location-based'],
                    ['因子', carbon.data?.factor?.name || '暂无适用因子'],
                    ['因子版本', carbon.data?.factor?.version || '—'],
                    ['适用地区', carbon.data?.factor?.region || '—'],
                    ['数据质量', <StatusBadge value={carbon.data?.quality} />],
                  ]}
                />
              </div>
            </Card>
            <Card>
              <CardHeader
                title="配置电量电费"
                subtitle="按有效计量区间及其时区、费率窗口求和"
                actions={<CircleDollarSign size={19} className="text-teal" />}
              />
              <div className="card-pad">
                <div className="pricing-summary">
                  <div>
                    <span>已知电量</span>
                    <strong>
                      {formatNumber(cost.data?.known_kwh)}
                      <small>kWh</small>
                    </strong>
                  </div>
                  <div>
                    <span>定价覆盖</span>
                    <strong>
                      {formatNumber(
                        cost.data?.pricing_coverage_ratio == null
                          ? null
                          : cost.data.pricing_coverage_ratio * 100,
                      )}
                      <small>%</small>
                    </strong>
                  </div>
                  <div>
                    <span>电量电费估算</span>
                    <strong className="text-teal">
                      {formatNumber(cost.data?.amount, 2)}
                      <small>{cost.data?.currency || '币种未知'}</small>
                    </strong>
                  </div>
                </div>
                <DefinitionList
                  items={[
                    [
                      '电价方案',
                      cost.data?.tariff?.name ||
                        (cost.data?.tariffs_used?.length
                          ? `${cost.data.tariffs_used.length} 个跨期版本`
                          : '暂无适用电价'),
                    ],
                    [
                      '日历时区',
                      cost.data?.tariff?.timezone ||
                        (cost.data?.tariffs_used?.length ? '按各版本指定时区' : '—'),
                    ],
                    [
                      '跨价窗处理',
                      cost.data?.pricing_mode === 'proportional_estimate'
                        ? '按经过的 UTC 时长分摊（估算）'
                        : '严格：跨不同费率时不猜测',
                    ],
                    ['已估算边界区间', cost.data?.boundary_estimated_intervals ?? '—'],
                    ['未定价边界区间', cost.data?.boundary_unresolved_intervals ?? '—'],
                    ['数据质量', <StatusBadge value={cost.data?.quality} />],
                  ]}
                />
                {allocation === 'proportional_estimate' && (
                  <Notice tone="warning">
                    已显式允许把跨费率区间的已知 Wh 按经过的 UTC
                    时长分摊。这是估算，不恢复缺失的分时测量。
                  </Notice>
                )}
                {!!cost.data?.warnings?.length && (
                  <Notice tone="warning">{cost.data.warnings.join('；')}</Notice>
                )}
              </div>
            </Card>
          </div>
        </>
      )}
      <Card>
        <CardHeader
          title="版本登记簿"
          subtitle="全平台参数版本 · 保留历史核算引用"
          actions={
            permissions.configureGlobal(auth.session?.user) && (
              <Button onClick={() => setForm(tab === 'factors' ? 'factor' : 'tariff')}>
                <Plus size={15} />
                登记版本
              </Button>
            )
          }
        />
        <Tabs
          active={tab}
          onChange={setTab}
          items={[
            { id: 'factors', label: '排放因子', count: factors.data?.length },
            { id: 'tariffs', label: '电价方案', count: tariffs.data?.length },
          ]}
        />
        {tab === 'factors' ? (
          factors.isLoading ? (
            <Loading />
          ) : factors.error ? (
            <ErrorState error={factors.error} />
          ) : (
            <DataTable
              rows={factors.data || []}
              rowKey={(f) => f.id}
              columns={[
                {
                  key: 'name',
                  title: '因子名称',
                  render: (f) => (
                    <strong>
                      {f.name}
                      <small>
                        {f.region} · {f.year}
                      </small>
                    </strong>
                  ),
                },
                {
                  key: 'rate',
                  title: 'kgCO₂e / kWh',
                  render: (f) => formatNumber(f.kg_co2e_per_kwh, 6),
                },
                { key: 'version', title: '版本', render: (f) => f.version },
                { key: 'from', title: '有效开始', render: (f) => formatDate(f.valid_from) },
                {
                  key: 'source',
                  title: '来源',
                  render: (f) => (
                    <div className="inline-gap">
                      <SourceBadge value={f.source_mode} />
                      {f.source_url && (
                        <a
                          href={f.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-link"
                        >
                          查看来源
                        </a>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          )
        ) : tariffs.isLoading ? (
          <Loading />
        ) : tariffs.error ? (
          <ErrorState error={tariffs.error} />
        ) : (
          <DataTable
            rows={tariffs.data || []}
            rowKey={(f) => f.id}
            columns={[
              { key: 'name', title: '电价方案', render: (f) => <strong>{f.name}</strong> },
              {
                key: 'rate',
                title: '基础单价 / kWh',
                render: (f) => `${formatNumber(f.rate_per_kwh, 6)} ${f.currency}`,
              },
              { key: 'timezone', title: '日历时区', render: (f) => f.timezone || 'Asia/Shanghai' },
              {
                key: 'bands',
                title: '分时覆盖',
                render: (f) =>
                  f.bands?.length ? (
                    <details className="tariff-band-summary">
                      <summary>{f.bands.length} 个时段</summary>
                      {f.bands.map((band, index) => (
                        <div key={index}>
                          {minuteClock(band.start_minute)}–{minuteClock(band.end_minute)} ·{' '}
                          {formatNumber(band.rate_per_kwh, 6)} {f.currency}/kWh
                          {band.label ? ` · ${band.label}` : ''}
                        </div>
                      ))}
                    </details>
                  ) : (
                    '全日基础单价'
                  ),
              },
              { key: 'version', title: '版本', render: (f) => f.version },
              { key: 'from', title: '有效开始', render: (f) => formatDate(f.valid_from) },
              {
                key: 'source',
                title: '来源',
                render: (f) => (
                  <div className="inline-gap">
                    <SourceBadge value={f.source_mode} />
                    {f.source_url && (
                      <a href={f.source_url} target="_blank" rel="noreferrer" className="text-link">
                        查看来源
                      </a>
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
        <div className="card-bottom">
          <ShieldCheck size={14} />
          仅拥有全部校区权限的全局管理员可登记新版本
        </div>
      </Card>
      {form && permissions.configureGlobal(auth.session?.user) && (
        <VersionForm kind={form} onClose={close} />
      )}
    </>
  )
}
