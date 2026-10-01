import { useCallback, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  Check,
  FlaskConical,
  Plus,
  ShieldCheck,
  Sparkles,
  Target,
  Workflow,
} from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Evaluation, Forecast, Strategy } from '../lib/types'
import { formatDate, formatNumber } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DataTable,
  DefinitionList,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  Loading,
  Modal,
  Notice,
  PageHeader,
  SourceBadge,
  StatusBadge,
} from '../components/ui'
import { BuildingFilter } from '../components/Filters'
import ForecastEvidence from '../components/ForecastEvidence'
import ForecastRunStatus from '../components/ForecastRunStatus'
import { forecastRefreshInterval } from '../lib/forecast-state'
import StrategyDispatch from '../components/StrategyDispatch'
import { LineChart } from '../components/charts'
function StrategyCreate({ onClose }: { onClose: () => void }) {
  const scope = useScope()
  const client = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [campus, setCampus] = useState(scope.campusId || scope.campuses[0]?.id || '')
  const [target, setTarget] = useState(10)
  const [max, setMax] = useState(10)
  const mutation = useMutation({
    mutationFn: () =>
      api.post<Strategy>('/strategies', {
        name,
        description,
        campus_id: campus,
        target_reduction_pct: target,
        max_devices: max,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Modal title="创建影子策略" onClose={onClose}>
      <Notice title="先评估，再决策">影子策略只评估候选设备与预计削减，不自动下发控制命令。</Notice>
      <form
        className="form-stack"
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
      >
        <Field label="策略名称">
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
            placeholder="例如 午间非关键负载优化"
          />
        </Field>
        <Field label="策略说明">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={1000}
          />
        </Field>
        <Field label="适用校区">
          <select required value={campus} onChange={(e) => setCampus(e.target.value)}>
            <option value="">选择校区</option>
            {scope.campuses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="form-grid">
          <Field label="目标削减比例（%）">
            <input
              type="number"
              min="0.1"
              max="50"
              step="0.1"
              value={target}
              onChange={(e) => setTarget(Number(e.target.value))}
              required
            />
          </Field>
          <Field label="最多候选设备">
            <input
              type="number"
              min="1"
              max="500"
              value={max}
              onChange={(e) => setMax(Number(e.target.value))}
              required
            />
          </Field>
        </div>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button type="button" onClick={onClose}>
            取消
          </Button>
          <Button variant="primary" type="submit" loading={mutation.isPending}>
            创建影子策略
          </Button>
        </div>
      </form>
    </Modal>
  )
}
function StrategyDetail({ strategy, onClose }: { strategy: Strategy; onClose: () => void }) {
  const auth = useAuth()
  const client = useQueryClient()
  const [evaluation, setEvaluation] = useState<Evaluation | null>(strategy.latest_evaluation)
  const [note, setNote] = useState('')
  const [approved, setApproved] = useState(strategy.status === 'approved')
  const evaluate = useMutation({
    mutationFn: () =>
      api.post<Evaluation>(`/strategies/${encodeURIComponent(strategy.id)}/evaluate`, {}),
    onSuccess: (e) => {
      setEvaluation(e)
      setApproved(false)
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  const approve = useMutation({
    mutationFn: () =>
      api.post<Strategy>(`/strategies/${encodeURIComponent(strategy.id)}/approve`, { note }),
    onSuccess: () => {
      setApproved(true)
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  return (
    <Drawer title={strategy.name} subtitle={strategy.id} onClose={onClose} wide>
      <div className="inline-gap section-space">
        <Badge tone="blue">SHADOW</Badge>
        <StatusBadge value={approved ? 'approved' : strategy.status} />
      </div>
      <p className="detail-description">{strategy.description || '未提供策略说明'}</p>
      <DefinitionList
        items={[
          ['目标削减', `${strategy.target_reduction_pct}%`],
          ['候选设备上限', strategy.max_devices],
          ['创建人员', strategy.created_by],
          ['创建时间', formatDate(strategy.created_at)],
        ]}
      />
      <Notice title="评估不会执行控制">
        候选设备必须通过时效、关键负载、能力与授权检查。未知占用不等于空闲，估计削减不是实测节能。
      </Notice>
      {permissions.analyze(auth.session?.user.role) && (
        <div className="section-space">
          <Button variant="primary" loading={evaluate.isPending} onClick={() => evaluate.mutate()}>
            <FlaskConical size={16} />
            重新运行影子评估
          </Button>
        </div>
      )}
      {evaluate.error && <ErrorState error={evaluate.error} />}
      {evaluation ? (
        <>
          <div className="evaluation-summary">
            <div>
              <span>预计削减</span>
              <strong>
                {formatNumber(evaluation.estimated_reduction_kw)}
                <small>kW</small>
              </strong>
            </div>
            <div>
              <span>基线功率</span>
              <strong>
                {formatNumber(evaluation.baseline_kw)}
                <small>kW</small>
              </strong>
            </div>
            <div>
              <span>合格候选</span>
              <strong>
                {evaluation.candidate_device_ids.length}
                <small>台</small>
              </strong>
            </div>
          </div>
          <div className="inline-gap">
            <SourceBadge value={evaluation.source_mode} />
            <StatusBadge value={evaluation.quality} />
            <Badge>未执行下发</Badge>
          </div>
          <p className="small text-muted">
            评估时间 {formatDate(evaluation.created_at)} · {evaluation.id}
          </p>
          <h3 className="section-title">候选设备</h3>
          {evaluation.candidate_device_ids.length ? (
            <div className="tag-list">
              {evaluation.candidate_device_ids.map((id) => (
                <span key={id}>{id}</span>
              ))}
            </div>
          ) : (
            <EmptyState
              title="没有合格的候选设备"
              description="安全条件不足时保持零下发，不放宽边界来满足目标"
            />
          )}
          <h3 className="section-title">被排除的设备与原因</h3>
          <DataTable
            rows={evaluation.rejected_devices}
            rowKey={(r) => r.device_id}
            columns={[
              { key: 'device', title: '设备', render: (r) => r.device_id },
              { key: 'reason', title: '排除原因', render: (r) => r.reason },
            ]}
          />
          {permissions.administer(auth.session?.user.role) && !approved && (
            <form
              className="form-stack"
              onSubmit={(e) => {
                e.preventDefault()
                approve.mutate()
              }}
            >
              <Field label="审批说明">
                <textarea
                  required
                  minLength={3}
                  maxLength={500}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="记录对评估结果和适用边界的审核意见…"
                />
              </Field>
              {approve.error && <ErrorState error={approve.error} />}
              <Button variant="primary" type="submit" loading={approve.isPending}>
                <ShieldCheck size={16} />
                批准影子策略
              </Button>
              <p className="small text-muted">批准只记录审核结论，不触发自动执行</p>
            </form>
          )}
          {approved && (
            <Notice tone="success" title="已批准影子策略">
              审批不等于调度，实际命令仍需要独立授权和完整安全检查。
            </Notice>
          )}
          {approved && permissions.operate(auth.session?.user.role) && (
            <StrategyDispatch key={evaluation.id} strategy={strategy} evaluation={evaluation} />
          )}
        </>
      ) : (
        <EmptyState
          title="尚无评估结果"
          description="运行影子评估后可查看候选设备、排除原因与估计削减"
          icon={<FlaskConical size={30} />}
        />
      )}
    </Drawer>
  )
}
export default function Strategies() {
  const auth = useAuth()
  const scope = useScope()
  const [building, setBuilding] = useState('')
  const [horizon, setHorizon] = useState(24)
  const [create, setCreate] = useState(false)
  const [selected, setSelected] = useState<Strategy | null>(null)
  const client = useQueryClient()
  const forecastPath = `/forecasts${queryString({ campus_id: scope.campusId, building_id: building, horizon_hours: horizon })}`
  const forecasts = useResource<Forecast>(forecastPath, { interval: forecastRefreshInterval })
  const retryForecast = useMutation({
    mutationFn: async (scope: {
      path: string
      campus_id?: string
      building_id?: string
      horizon_hours: number
    }) => {
      const { path, ...body } = scope
      return { path, data: await api.post<Forecast>('/forecasts/refresh', body) }
    },
    onSuccess: ({ path, data }) => client.setQueryData(['resource', path], data),
  })
  const strategies = useResource<Strategy[]>(
    `/strategies${queryString({ campus_id: scope.campusId, limit: 500 })}`,
  )
  const close = useCallback(() => setSelected(null), [])
  const closeCreate = useCallback(() => setCreate(false), [])
  return (
    <>
      <PageHeader
        eyebrow="FORECAST & OPTIMIZE"
        title="预测与策略"
        description="保留不确定性，在影子模式中验证优化思路，谨慎迈向每一次行动。"
        actions={
          permissions.analyze(auth.session?.user.role) && (
            <Button variant="primary" onClick={() => setCreate(true)}>
              <Plus size={15} />
              创建影子策略
            </Button>
          )
        }
      />
      <Card>
        <CardHeader
          title="负荷预测"
          subtitle="以独立历史评估选择模型 · 保留预测不确定性"
          actions={
            <>
              <BuildingFilter value={building} onChange={setBuilding} />
              <select
                aria-label="预测时间范围"
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
              >
                <option value="6">未来 6 小时</option>
                <option value="12">未来 12 小时</option>
                <option value="24">未来 24 小时</option>
                <option value="48">未来 48 小时</option>
              </select>
            </>
          }
        />
        {forecasts.isLoading ? (
          <Loading />
        ) : forecasts.error ? (
          <ErrorState
            error={forecasts.error}
            retry={() => {
              void forecasts.refetch()
            }}
          />
        ) : (
          forecasts.data && (
            <>
              <ForecastRunStatus
                forecast={forecasts.data}
                retrying={retryForecast.variables?.path === forecastPath && retryForecast.isPending}
                retryError={
                  retryForecast.variables?.path === forecastPath ? retryForecast.error : null
                }
                onRetry={() =>
                  retryForecast.mutate({
                    path: forecastPath,
                    campus_id: scope.campusId || undefined,
                    building_id: building || undefined,
                    horizon_hours: horizon,
                  })
                }
              />
              <div className="forecast-meta">
                <span>
                  <Sparkles size={16} />
                  {forecasts.data.method}
                </span>
                <SourceBadge value={forecasts.data.source_mode} />
                <StatusBadge value={forecasts.data.quality} />
                <span>所选方法测试 MAE：{formatNumber(forecasts.data.mae_kw)} kW</span>
                <span>训练截至 {formatDate(forecasts.data.trained_until)}</span>
              </div>
              <div className="chart-pad">
                <LineChart
                  label="预测输入负荷"
                  points={forecasts.data.points.map((p) => ({
                    timestamp: p.timestamp,
                    value: p.predicted_kw,
                    lower: p.lower_kw,
                    upper: p.upper_kw,
                  }))}
                />
              </div>
              {forecasts.data.warnings.length > 0 && (
                <div className="card-pad no-top">
                  <Notice tone="warning">{forecasts.data.warnings.join('；')}</Notice>
                </div>
              )}
              <ForecastEvidence forecast={forecasts.data} />
            </>
          )
        )}
      </Card>
      <div className="inline-between section-heading">
        <div>
          <div className="eyebrow">SHADOW STRATEGIES</div>
          <h2>优化策略工作台</h2>
        </div>
        <Badge tone="blue">
          <Workflow size={13} />
          影子模式
        </Badge>
      </div>
      {strategies.isLoading ? (
        <Loading />
      ) : strategies.error ? (
        <ErrorState error={strategies.error} />
      ) : !strategies.data?.length ? (
        <Card>
          <EmptyState
            title="创建第一条影子策略"
            description="设定目标，评估候选，保留每一次审核与决策的依据"
            icon={<Target size={32} />}
          />
        </Card>
      ) : (
        <div className="strategy-grid">
          {strategies.data.map((s) => (
            <Card key={s.id} className="strategy-card">
              <div className="strategy-card-top">
                <span className="strategy-icon">
                  <Workflow size={22} />
                </span>
                <StatusBadge value={s.status} />
              </div>
              <h3>{s.name}</h3>
              <p>{s.description || '影子模式负载优化策略'}</p>
              <div className="strategy-stats">
                <div>
                  <span>目标削减</span>
                  <strong>
                    {s.target_reduction_pct}
                    <small>%</small>
                  </strong>
                </div>
                <div>
                  <span>候选上限</span>
                  <strong>
                    {s.max_devices}
                    <small>台</small>
                  </strong>
                </div>
              </div>
              <div className="strategy-evidence">
                <Check size={14} />
                {s.latest_evaluation
                  ? `最近评估：${formatDate(s.latest_evaluation.created_at)}`
                  : '等待首次评估'}
              </div>
              <Button onClick={() => setSelected(s)}>
                查看与评估
                <ArrowRight size={15} />
              </Button>
            </Card>
          ))}
        </div>
      )}
      {selected && <StrategyDetail strategy={selected} onClose={close} />}
      {create && <StrategyCreate onClose={closeCreate} />}
    </>
  )
}
