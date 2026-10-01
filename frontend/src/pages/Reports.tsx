import { useCallback, useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDownToLine,
  Clock3,
  FileChartColumn,
  FileJson,
  Fingerprint,
  Plus,
  ShieldCheck,
} from 'lucide-react'
import { api, API_BASE, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection, useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Audit, Report } from '../lib/types'
import type { CostAllocationMode } from '../lib/pricing'
import { formatDate } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  DataTable,
  DefinitionList,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  JsonView,
  Loading,
  Modal,
  Notice,
  PageHeader,
  Pagination,
  SourceBadge,
  Tabs,
} from '../components/ui'
import { BuildingFilter, initialRange, PeriodFilter } from '../components/Filters'
const reportType = (type: string) =>
  ({ energy: '能耗报告', carbon: '碳核算报告', cost: '成本报告', operations: '运行报告' })[type] ||
  type
function CreateReport({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const scope = useScope()
  const client = useQueryClient()
  const [name, setName] = useState('')
  const [type, setType] = useState('energy')
  const [allocation, setAllocation] = useState<CostAllocationMode>('strict')
  const [building, setBuilding] = useState('')
  const [range, setRange] = useState(initialRange)
  const mutation = useMutation({
    mutationFn: () =>
      api.post<Report>('/reports', {
        name,
        type,
        cost_allocation_mode: type === 'cost' ? allocation : 'strict',
        campus_id: scope.campusId || null,
        building_id: building || null,
        ...range,
      }),
    onSuccess: (result) => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onCreated(result.id)
      onClose()
    },
  })
  return (
    <Modal title="生成核算快照报告" onClose={onClose}>
      <Notice>
        报告将保存当前核算结果、输入范围与版本引用。后续实时数据变化不会覆盖已生成快照。
      </Notice>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <Field label="报告名称">
          <input
            required
            maxLength={150}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如 九月校园用能复核"
          />
        </Field>
        <Field label="报告类型">
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {['energy', 'carbon', 'cost', 'operations'].map((t) => (
              <option key={t} value={t}>
                {reportType(t)}
              </option>
            ))}
          </select>
        </Field>
        {type === 'cost' && (
          <Field label="跨价窗核算方式" hint="仅估算配置电量电费，不含另行计收的需量或固定等费用">
            <select
              value={allocation}
              onChange={(e) => setAllocation(e.target.value as CostAllocationMode)}
            >
              <option value="strict">严格定价（默认，不猜测区间分配）</option>
              <option value="proportional_estimate">按区间时长分摊（显式估算）</option>
            </select>
          </Field>
        )}
        <Field label="楼栋范围">
          <BuildingFilter value={building} onChange={setBuilding} />
        </Field>
        <Field label="统计范围">
          <PeriodFilter value={range} onChange={setRange} />
        </Field>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button onClick={onClose} type="button">
            取消
          </Button>
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            <FileChartColumn size={16} />
            生成快照
          </Button>
        </div>
      </form>
    </Modal>
  )
}
function ReportDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const query = useResource<Report>(`/reports/${encodeURIComponent(id)}`, { interval: false })
  const d = query.data
  const [error, setError] = useState<unknown>(null)
  const [downloading, setDownloading] = useState(false)
  const download = async (format: 'json' | 'csv') => {
    setDownloading(true)
    setError(null)
    try {
      const response = await fetch(
        `${API_BASE}/reports/${encodeURIComponent(id)}/export?format=${format}`,
        { credentials: 'include' },
      )
      if (!response.ok) throw new Error(`导出失败（HTTP ${response.status}）`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${d?.name || id}.${format}`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) {
      setError(e)
    } finally {
      setDownloading(false)
    }
  }
  return (
    <Drawer title={d?.name || '报告快照'} subtitle={id} onClose={onClose} wide>
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : (
        d && (
          <>
            <div className="inline-between section-space">
              <div className="inline-gap">
                <SourceBadge value={d.source_mode} />
                <Badge>{reportType(d.type)}</Badge>
              </div>
              <div className="inline-gap">
                <Button
                  onClick={() => {
                    void download('json')
                  }}
                  loading={downloading}
                >
                  <FileJson size={15} />
                  JSON
                </Button>
                <Button
                  onClick={() => {
                    void download('csv')
                  }}
                  loading={downloading}
                >
                  <ArrowDownToLine size={15} />
                  CSV
                </Button>
              </div>
            </div>
            {error && <ErrorState error={error} />}
            <DefinitionList
              items={[
                ['生成时间', formatDate(d.created_at)],
                ['生成人员', d.created_by],
                ['报告类型', reportType(d.type)],
                ['来源模式', <SourceBadge value={d.source_mode} />],
              ]}
            />
            <h3 className="section-title">报告摘要</h3>
            <JsonView value={d.summary} />
            <h3 className="section-title">核算参数</h3>
            <JsonView value={d.parameters} />
            <details className="details-block">
              <summary>查看完整快照内容</summary>
              <JsonView value={d.content} />
            </details>
            <Notice>此报告记录软件核算证据，不构成现场计量检定、财务账单或实际减排证明。</Notice>
          </>
        )
      )}
    </Drawer>
  )
}
export default function Reports() {
  const auth = useAuth()
  const scope = useScope()
  const [tab, setTab] = useState('reports')
  const [create, setCreate] = useState(false)
  const [selected, setSelected] = useState('')
  const [auditDetail, setAuditDetail] = useState<Audit | null>(null)
  const [entity, setEntity] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 25
  const reports = useCollection<Report>(
    `/reports${queryString({ campus_id: scope.campusId, limit, offset })}`,
    {
      enabled: tab === 'reports',
    },
  )
  const audit = useCollection<Audit>(
    `/audit${queryString({ campus_id: scope.campusId, entity_type: entity, limit, offset })}`,
    { enabled: tab === 'audit' },
  )
  const close = useCallback(() => setSelected(''), [])
  const closeCreate = useCallback(() => setCreate(false), [])
  const closeAudit = useCallback(() => setAuditDetail(null), [])
  useEffect(() => setOffset(0), [tab, entity, scope.campusId])
  const query = tab === 'reports' ? reports : audit
  return (
    <>
      <PageHeader
        eyebrow="REPORTS & AUDIT"
        title="报表与审计"
        description="保存关键时刻的核算快照，让每个数据版本和每次操作都有依据可查。"
        actions={
          permissions.analyze(auth.session?.user.role) && (
            <Button variant="primary" onClick={() => setCreate(true)}>
              <Plus size={15} />
              生成报告
            </Button>
          )
        }
      />
      <div className="report-intro">
        <span className="report-intro-icon">
          <Fingerprint size={29} />
        </span>
        <div>
          <h2>清晰的记录，可信的决策</h2>
          <p>报告保存核算快照，审计保留操作事实。两者相互关联，独立于实时看板。</p>
        </div>
        <ShieldCheck size={26} />
      </div>
      <Card>
        <Tabs
          active={tab}
          onChange={setTab}
          items={[
            { id: 'reports', label: '报告快照' },
            { id: 'audit', label: '操作审计' },
          ]}
        />
        {tab === 'audit' && (
          <div className="filter-bar table-filters">
            <select
              aria-label="审计对象类型"
              value={entity}
              onChange={(e) => setEntity(e.target.value)}
            >
              <option value="">所有对象</option>
              {['device', 'command', 'alarm', 'strategy', 'report', 'auth', 'settings'].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <span className="filter-hint">只读追加日志 · 不提供删除入口</span>
          </div>
        )}
        {query.isLoading ? (
          <Loading />
        ) : query.error ? (
          <ErrorState
            error={query.error}
            retry={() => {
              void query.refetch()
            }}
          />
        ) : tab === 'reports' ? (
          <DataTable
            rows={reports.data?.data || []}
            rowKey={(r) => r.id}
            onRowClick={(r) => setSelected(r.id)}
            columns={[
              {
                key: 'name',
                title: '报告',
                render: (r) => (
                  <div className="table-device">
                    <span>
                      <FileChartColumn size={19} />
                    </span>
                    <strong>
                      {r.name}
                      <small>{r.id}</small>
                    </strong>
                  </div>
                ),
              },
              { key: 'type', title: '类型', render: (r) => reportType(r.type) },
              {
                key: 'source',
                title: '来源',
                render: (r) => <SourceBadge value={r.source_mode} />,
              },
              { key: 'time', title: '生成时间', render: (r) => formatDate(r.created_at) },
              { key: 'user', title: '生成人员', render: (r) => r.created_by },
            ]}
            empty={
              <EmptyState
                title="尚无报告快照"
                description="生成报告后，可下载带有来源与质量信息的 JSON 或 CSV"
                icon={<FileChartColumn size={30} />}
              />
            }
          />
        ) : (
          <DataTable
            rows={audit.data?.data || []}
            rowKey={(a) => a.id}
            onRowClick={setAuditDetail}
            columns={[
              {
                key: 'time',
                title: '操作时间',
                render: (a) => (
                  <span className="inline-gap">
                    <Clock3 size={14} />
                    {formatDate(a.at)}
                  </span>
                ),
              },
              { key: 'actor', title: '操作人员', render: (a) => <strong>{a.actor}</strong> },
              { key: 'action', title: '动作', render: (a) => <Badge>{a.action}</Badge> },
              { key: 'type', title: '对象类型', render: (a) => a.entity_type },
              {
                key: 'id',
                title: '对象标识',
                render: (a) => <span className="monospace ellipsis">{a.entity_id}</span>,
              },
            ]}
          />
        )}
        <Pagination
          offset={offset}
          limit={limit}
          total={Number(query.data?.meta?.total || 0)}
          setOffset={setOffset}
        />
      </Card>
      {create && <CreateReport onClose={closeCreate} onCreated={setSelected} />}
      {selected && <ReportDetail id={selected} onClose={close} />}
      {auditDetail && (
        <Drawer title="操作审计详情" subtitle={auditDetail.id} onClose={closeAudit}>
          <DefinitionList
            items={[
              ['操作人员', auditDetail.actor],
              ['动作', auditDetail.action],
              ['对象类型', auditDetail.entity_type],
              ['对象', auditDetail.entity_id],
              ['时间', formatDate(auditDetail.at)],
            ]}
          />
          <JsonView value={auditDetail.details} />
        </Drawer>
      )}
    </>
  )
}
