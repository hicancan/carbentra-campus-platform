import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpRight,
  Bell,
  CheckCheck,
  ClipboardCheck,
  MessageSquarePlus,
  ShieldCheck,
} from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection, useResource } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { Alarm } from '../lib/types'
import { formatDate, statusLabel } from '../lib/format'
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
  Loading,
  Notice,
  PageHeader,
  Pagination,
  SourceBadge,
  StatusBadge,
  Tabs,
} from '../components/ui'
import { BuildingFilter } from '../components/Filters'
import ClassroomAnomalies from '../components/ClassroomAnomalies'
function AlarmDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const auth = useAuth()
  const client = useQueryClient()
  const query = useResource<Alarm>(`/alarms/${encodeURIComponent(id)}`)
  const [note, setNote] = useState('')
  const [action, setAction] = useState('notes')
  const [success, setSuccess] = useState('')
  const d = query.data
  const mutation = useMutation({
    mutationFn: () => api.post<Alarm>(`/alarms/${encodeURIComponent(id)}/${action}`, { note }),
    onSuccess: () => {
      setSuccess(
        action === 'acknowledge'
          ? '告警已确认'
          : action === 'resolve'
            ? '告警已解决'
            : '工作记录已添加',
      )
      setNote('')
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  return (
    <Drawer title={d?.title || '告警详情'} subtitle={id} onClose={onClose}>
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : (
        d && (
          <>
            <div className="inline-gap section-space">
              <StatusBadge value={d.severity} />
              <StatusBadge value={d.status} />
              <SourceBadge value={d.source_mode} />
            </div>
            <p className="detail-description">{d.description}</p>
            <DefinitionList
              items={[
                ['告警类型', d.type],
                ['发现时间', formatDate(d.created_at)],
                [
                  '设备',
                  <Link
                    className="text-link"
                    to={`/devices?device=${encodeURIComponent(d.device_id)}`}
                  >
                    {d.device_id}
                    <ArrowUpRight size={13} />
                  </Link>,
                ],
                ['确认时间', formatDate(d.acknowledged_at)],
                ['确认人员', d.acknowledged_by || '—'],
                ['解决时间', formatDate(d.resolved_at)],
              ]}
            />
            <h3 className="section-title">处理时间线</h3>
            <div className="timeline">
              <div className="timeline-item">
                <span className="timeline-dot amber" />
                <div>
                  <strong>告警产生</strong>
                  <time>{formatDate(d.created_at)}</time>
                  <p>{d.title}</p>
                </div>
              </div>
              {d.acknowledged_at && (
                <div className="timeline-item">
                  <span className="timeline-dot blue" />
                  <div>
                    <strong>已确认 · {d.acknowledged_by}</strong>
                    <time>{formatDate(d.acknowledged_at)}</time>
                  </div>
                </div>
              )}
              {d.notes.map((n, i) => (
                <div className="timeline-item" key={`${n.at}-${i}`}>
                  <span className="timeline-dot" />
                  <div>
                    <strong>{n.by}</strong>
                    <time>{formatDate(n.at)}</time>
                    <p>{n.text}</p>
                  </div>
                </div>
              ))}
              {d.resolved_at && (
                <div className="timeline-item">
                  <span className="timeline-dot teal" />
                  <div>
                    <strong>已解决 · {d.resolved_by}</strong>
                    <time>{formatDate(d.resolved_at)}</time>
                  </div>
                </div>
              )}
            </div>
            {permissions.operate(auth.session?.user.role) ? (
              <form
                className="form-stack"
                onSubmit={(event) => {
                  event.preventDefault()
                  mutation.mutate()
                }}
              >
                <h3 className="section-title">更新处理记录</h3>
                <Field label="操作">
                  <select
                    value={action}
                    onChange={(e) => {
                      setAction(e.target.value)
                      setSuccess('')
                      mutation.reset()
                    }}
                  >
                    <option value="notes">添加工作记录</option>
                    {!['acknowledged', 'resolved'].includes(d.status) && (
                      <option value="acknowledge">确认告警</option>
                    )}
                    {d.status !== 'resolved' && <option value="resolve">解决告警</option>}
                  </select>
                </Field>
                <Field label="处理说明" hint="记录诊断与处置证据，不用状态变更代替现场确认">
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    minLength={3}
                    maxLength={1000}
                    required
                    placeholder="请输入处理说明…"
                  />
                </Field>
                {mutation.error && <ErrorState error={mutation.error} compact />}
                {success && <Notice tone="success">{success}</Notice>}
                <Button variant="primary" loading={mutation.isPending} type="submit">
                  {action === 'resolve' ? (
                    <CheckCheck size={16} />
                  ) : action === 'acknowledge' ? (
                    <ClipboardCheck size={16} />
                  ) : (
                    <MessageSquarePlus size={16} />
                  )}
                  {action === 'resolve'
                    ? '提交解决记录'
                    : action === 'acknowledge'
                      ? '确认告警'
                      : '添加工作记录'}
                </Button>
              </form>
            ) : (
              <Notice>当前角色只能查看告警与工作记录</Notice>
            )}
          </>
        )
      )}
    </Drawer>
  )
}
export default function Alarms() {
  const scope = useScope()
  const [params, setParams] = useSearchParams()
  const selected = params.get('alarm') || ''
  const classroomView = params.get('view') === 'classrooms'
  const classroomSpace = params.get('space') || ''
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [building, setBuilding] = useState(params.get('building') || '')
  const [offset, setOffset] = useState(0)
  const limit = 25
  const query = useCollection<Alarm>(
    `/alarms${queryString({ campus_id: scope.campusId, building_id: building, status, severity, limit, offset })}`,
    { enabled: !classroomView },
  )
  const close = useCallback(() => {
    const next = new URLSearchParams(params)
    next.delete('alarm')
    setParams(next)
  }, [params, setParams])
  useEffect(() => setOffset(0), [scope.campusId, building, status, severity])
  return (
    <>
      <PageHeader
        eyebrow="ALARM WORKSPACE"
        title="告警工单"
        description="从发现到确认、记录与解决，形成完整且可复核的运维闭环。"
        actions={
          <Badge tone="amber">
            <Bell size={13} />
            {classroomView
              ? '教室历史异常 · 分层证据'
              : `${Number(query.data?.meta?.total || 0)} 条匹配记录`}
          </Badge>
        }
      />
      <Tabs
        active={classroomView ? 'classrooms' : 'devices'}
        items={[
          { id: 'devices', label: '设备告警工单' },
          { id: 'classrooms', label: '教室历史异常' },
        ]}
        onChange={(value) => {
          const next = new URLSearchParams(params)
          value === 'classrooms' ? next.set('view', value) : next.delete('view')
          next.delete('alarm')
          setParams(next)
        }}
      />
      {classroomView ? (
        <>
          {classroomSpace && (
            <Notice>
              当前限定教室 ·{' '}
              <Link className="text-link" to={`/classrooms/${encodeURIComponent(classroomSpace)}`}>
                返回教室工作台
              </Link>
            </Notice>
          )}
          <div className="filter-bar">
            <BuildingFilter value={building} onChange={setBuilding} />
          </div>
          <ClassroomAnomalies buildingId={building} spaceId={classroomSpace || undefined} />
        </>
      ) : (
        <>
          <div className="workflow-banner">
            <div>
              <Bell size={19} />
              <strong>发现异常</strong>
              <span>来源与设备证据</span>
            </div>
            <i />
            <div>
              <ClipboardCheck size={19} />
              <strong>确认与诊断</strong>
              <span>责任人与处理记录</span>
            </div>
            <i />
            <div>
              <ShieldCheck size={19} />
              <strong>解决与留痕</strong>
              <span>保留完整审计链</span>
            </div>
          </div>
          <Card>
            <Tabs
              active={status}
              onChange={setStatus}
              items={[
                { id: '', label: '全部告警' },
                { id: 'open', label: '待处理' },
                { id: 'acknowledged', label: '已确认' },
                { id: 'resolved', label: '已解决' },
              ]}
            />
            <div className="filter-bar table-filters">
              <BuildingFilter value={building} onChange={setBuilding} />
              <select
                aria-label="告警严重程度"
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              >
                <option value="">全部级别</option>
                <option value="critical">严重</option>
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
              <span className="filter-hint">点击告警查看详情与工作记录</span>
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
                  rowKey={(a) => a.id}
                  onRowClick={(a) => {
                    const next = new URLSearchParams(params)
                    next.set('alarm', a.id)
                    setParams(next)
                  }}
                  selected={selected}
                  columns={[
                    {
                      key: 'title',
                      title: '告警内容',
                      render: (a) => (
                        <div className="table-alarm">
                          <span className={`alarm-icon severity-${a.severity}`}>
                            <Bell size={16} />
                          </span>
                          <strong>
                            {a.title}
                            <small>{a.device_id}</small>
                          </strong>
                        </div>
                      ),
                    },
                    {
                      key: 'severity',
                      title: '级别',
                      render: (a) => <StatusBadge value={a.severity} />,
                    },
                    {
                      key: 'status',
                      title: '工作流状态',
                      render: (a) => <StatusBadge value={a.status} />,
                    },
                    {
                      key: 'source',
                      title: '来源',
                      render: (a) => <SourceBadge value={a.source_mode} />,
                    },
                    { key: 'created', title: '发现时间', render: (a) => formatDate(a.created_at) },
                    {
                      key: 'notes',
                      title: '工作记录',
                      render: (a) => (
                        <span className="inline-gap">
                          <MessageSquarePlus size={14} />
                          {a.notes.length}
                        </span>
                      ),
                    },
                  ]}
                  empty={
                    <EmptyState
                      title={`暂无${status ? statusLabel(status) : '匹配'}告警`}
                      description="告警会保留来源、处理过程与责任人记录"
                      icon={<ShieldCheck size={30} />}
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
          {selected && <AlarmDetail id={selected} onClose={close} />}
        </>
      )}
    </>
  )
}
