import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, CircleDot, Clock3, Plus, Search, ShieldCheck, Terminal } from 'lucide-react'
import { permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection, useDebounced, useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Command, Device } from '../lib/types'
import { durationLabel } from '../lib/classroom-display'
import { formatDate, shortId, statusLabel } from '../lib/format'
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
  Notice,
  PageHeader,
  Pagination,
  SourceBadge,
  StatusBadge,
} from '../components/ui'
import CommandForm from '../components/CommandForm'
export const actionLabel = (action: string) =>
  ({ hold: '保持状态', shed: '负载削减', restore: '恢复供电' })[action] || action
function NewCommand({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (command: Command) => void
}) {
  const scope = useScope()
  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const [selected, setSelected] = useState('')
  const devices = useResource<Device[]>(
    `/devices${queryString({ campus_id: scope.campusId, q, source_mode: 'SIMULATED', limit: 100 })}`,
  )
  const query = useResource<Device>(`/devices/${encodeURIComponent(selected)}`, {
    enabled: !!selected,
  })
  return (
    <Drawer title="申请模拟命令" subtitle="可追踪 · 可幂等重试 · 有明确有效期" onClose={onClose}>
      <Field label="查找模拟设备">
        <div className="search-field">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="输入设备名称或 ID"
          />
        </div>
      </Field>
      <Field label="选择设备">
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          <option value="">请选择设备</option>
          {devices.data?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} · {statusLabel(d.status)}
            </option>
          ))}
        </select>
      </Field>
      {devices.error && <ErrorState error={devices.error} />}
      {query.isLoading && selected ? (
        <Loading compact />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : query.data ? (
        <CommandForm key={query.data.id} device={query.data} onCreated={onCreated} />
      ) : (
        <EmptyState
          title="选择设备开始申请"
          description="仅模拟执行器可运行命令。所有现场实际执行保持禁用。"
          icon={<Terminal size={28} />}
        />
      )}
    </Drawer>
  )
}
function CommandDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const query = useResource<Command>(`/commands/${encodeURIComponent(id)}`, { interval: 2000 })
  const d = query.data
  return (
    <Drawer
      title={d ? `${actionLabel(d.action)} · 命令追踪` : '命令追踪'}
      subtitle={id}
      onClose={onClose}
    >
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : (
        d && (
          <>
            <div className="command-status-hero">
              <Terminal size={29} />
              <div>
                <StatusBadge value={d.status} />
                <h3>{actionLabel(d.action)}</h3>
                <p>
                  序列 #{d.sequence} ·{' '}
                  {d.source_mode === 'SIMULATED'
                    ? `${d.simulation_scenario} 模拟场景`
                    : '独立授权执行通道'}
                </p>
              </div>
              <SourceBadge value={d.source_mode} />
            </div>
            <DefinitionList
              items={[
                [
                  '目标设备',
                  <Link
                    className="text-link"
                    to={`/devices?device=${encodeURIComponent(d.device_id)}`}
                  >
                    {d.device_id}
                    <ArrowUpRight size={13} />
                  </Link>,
                ],
                ['目标通道', `${d.channel_key} · ${d.channel_id || '旧版单路默认目标'}`],
                [
                  '通道人工接管',
                  d.manual_hold_seconds
                    ? `${durationLabel(d.manual_hold_seconds)}（后台 / 边缘范围）`
                    : '本次命令无额外接管窗口',
                ],
                ['产品执行类型', d.product_family],
                ['申请原因', d.reason],
                ['发起人员', d.created_by],
                ['申请时间', formatDate(d.issued_at)],
                ['到期时间', formatDate(d.expires_at)],
                ['幂等键', <span className="monospace">{d.idempotency_key}</span>],
              ]}
            />
            <h3 className="section-title">持久化状态轨迹</h3>
            <div className="timeline">
              {d.history.map((step, index) => (
                <div className="timeline-item" key={`${step.status}-${index}`}>
                  <span
                    className={`timeline-dot ${step.status === 'verified' ? 'teal' : ['failed', 'rejected', 'timed_out'].includes(step.status) ? 'red' : 'blue'}`}
                  />
                  <div>
                    <strong>{statusLabel(step.status)}</strong>
                    <time>{formatDate(step.at)}</time>
                    <p>{step.reason}</p>
                    {step.evidence && (
                      <details>
                        <summary>查看阶段证据</summary>
                        <JsonView value={step.evidence} />
                      </details>
                    )}
                  </div>
                </div>
              ))}
            </div>
            {d.status === 'acknowledged_unverified' && (
              <Notice tone="warning" title="执行器已回报，独立物理状态未验证">
                设备回报已接受或执行该通道动作，但该硬件没有独立负载反馈。不能据此认定灯具已经点亮、负载已经通电或已经安全断电。
              </Notice>
            )}
            {d.result && (
              <Notice
                tone="success"
                title={d.result.simulated ? '模拟结果已生成' : '已收到设备结果证据'}
              >
                目标状态：
                {d.result.desired_on == null ? '未知' : d.result.desired_on ? '开启' : '关闭'} ·
                输出反馈：
                {d.result.output_present == null
                  ? '未知'
                  : d.result.output_present
                    ? '存在'
                    : '不存在'}
                。结果反馈不代替现场隔离确认与验电。
              </Notice>
            )}
            <Notice title="状态有明确含义">
              受理、下发、设备确认与结果验证是不同阶段。失败、拒绝和超时不会被显示为成功。
            </Notice>
          </>
        )
      )}
    </Drawer>
  )
}
export default function Commands() {
  const auth = useAuth()
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const selected = params.get('command') || ''
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const [create, setCreate] = useState(false)
  const limit = 25
  const query = useCollection<Command>(
    `/commands${queryString({ campus_id: scope.campusId, status, limit, offset })}`,
    {
      interval: 3000,
    },
  )
  const close = useCallback(() => {
    const next = new URLSearchParams(params)
    next.delete('command')
    setParams(next)
  }, [params, setParams])
  const closeCreate = useCallback(() => setCreate(false), [])
  useEffect(() => setOffset(0), [status, scope.campusId])
  return (
    <>
      <PageHeader
        eyebrow="CONTROL TRACE"
        title="命令追踪"
        description="从意图到证据，逐阶段追踪每一条命令。始终区分请求、确认与验证。"
        actions={
          permissions.operate(auth.session?.user.role) && (
            <Button variant="primary" onClick={() => setCreate(true)}>
              <Plus size={15} />
              申请模拟命令
            </Button>
          )
        }
      />
      <Notice title="现场控制已禁用">
        此页面仅支持申请模拟命令。现场通道需要独立部署与设备放行；任何网页成功提示都不代表已完成物理隔离。
      </Notice>
      <div className="command-pipeline">
        {[
          { icon: CircleDot, title: '已受理', note: '鉴权与持久化' },
          { icon: Terminal, title: '已下发', note: '有序执行与过期检查' },
          { icon: Clock3, title: '设备确认', note: '关联回执' },
          { icon: ShieldCheck, title: '结果验证', note: '反馈证据核对' },
        ].map((step, i) => (
          <div key={step.title}>
            <span>{String(i + 1).padStart(2, '0')}</span>
            <step.icon size={18} />
            <strong>{step.title}</strong>
            <small>{step.note}</small>
          </div>
        ))}
      </div>
      <Card>
        <div className="filter-bar table-filters">
          <select aria-label="命令状态" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">全部状态</option>
            {[
              'requested',
              'dispatched',
              'acknowledged',
              'acknowledged_unverified',
              'verified',
              'rejected',
              'failed',
              'timed_out',
            ].map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
          <span className="filter-hint">每 3 秒刷新 · 以持久化回执为准</span>
          <Badge>{Number(query.data?.meta?.total || 0)} 条命令</Badge>
        </div>
        {query.isLoading ? (
          <Loading />
        ) : query.error ? (
          <ErrorState
            error={query.error}
            retry={() => {
              void query.refetch()
            }}
          />
        ) : (
          <>
            <DataTable
              rows={query.data?.data || []}
              rowKey={(c) => c.id}
              onRowClick={(c) => setParams({ command: c.id })}
              selected={selected}
              columns={[
                {
                  key: 'id',
                  title: '命令',
                  render: (c) => (
                    <strong>
                      {shortId(c.id, 22)}
                      <small>
                        {c.device_id} · {c.channel_key}
                      </small>
                    </strong>
                  ),
                },
                { key: 'action', title: '动作', render: (c) => actionLabel(c.action) },
                { key: 'seq', title: '序列', render: (c) => `#${c.sequence}` },
                { key: 'status', title: '状态', render: (c) => <StatusBadge value={c.status} /> },
                {
                  key: 'source',
                  title: '来源',
                  render: (c) => <SourceBadge value={c.source_mode} />,
                },
                { key: 'at', title: '发起时间', render: (c) => formatDate(c.issued_at) },
                { key: 'scenario', title: '模拟场景', render: (c) => c.simulation_scenario },
              ]}
              empty={
                <EmptyState
                  title="尚无命令记录"
                  description="申请模拟命令后，可在这里查看完整状态轨迹与证据"
                  icon={<Terminal size={30} />}
                />
              }
            />
            <Pagination
              offset={offset}
              limit={limit}
              total={Number(query.data?.meta?.total || 0)}
              setOffset={setOffset}
            />
          </>
        )}
      </Card>
      {selected && <CommandDetail id={selected} onClose={close} />}
      {create && (
        <NewCommand
          onClose={closeCreate}
          onCreated={(command) => {
            setCreate(false)
            setParams({ command: command.id })
          }}
        />
      )}
    </>
  )
}
