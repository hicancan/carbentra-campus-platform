import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, FlaskConical, Play, Plus, ShieldCheck } from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection, useResource } from '../lib/hooks'
import type { EvaluationResponse, PolicyResponse, RoomSnapshot } from '../lib/classroom-types'
import { localDateTime, durationLabel } from '../lib/classroom-display'
import { controlReason } from '../lib/control-eligibility'
import { browserTimezone } from '../lib/timezone'
import { formatDate, formatNumber } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DataTable,
  DefinitionList,
  EmptyState,
  ErrorState,
  Field,
  Loading,
  Modal,
  Pagination,
  Notice,
  SourceBadge,
  StatusBadge,
} from './ui'

function PolicyForm({ room, onClose }: { room: RoomSnapshot; onClose: () => void }) {
  const client = useQueryClient()
  const [name, setName] = useState('')
  const [mode, setMode] = useState<'SHADOW' | 'SIMULATED'>('SHADOW')
  const [start, setStart] = useState(localDateTime(new Date().toISOString()))
  const [end, setEnd] = useState(localDateTime(new Date(Date.now() + 86400000).toISOString()))
  const [channels, setChannels] = useState<string[]>([])
  const [vacancy, setVacancy] = useState(300)
  const [power, setPower] = useState(5)
  const [reason, setReason] = useState('')
  const targets = room.channels.filter((channel) => ['lighting', 'socket'].includes(channel.kind))
  const mutation = useMutation({
    mutationFn: () =>
      api.post<PolicyResponse>(`/classrooms/${encodeURIComponent(room.id)}/policies`, {
        name,
        mode,
        enabled: true,
        starts_at: new Date(start).toISOString(),
        ends_at: new Date(end).toISOString(),
        channel_ids: channels,
        action: 'shed',
        vacant_for_seconds: vacancy,
        minimum_power_w: power,
        max_commands: Math.min(channels.length, 20),
        reason,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Modal
      title={`${room.name} · 新建安全策略`}
      onClose={() => {
        if (!mutation.isPending) onClose()
      }}
    >
      <form
        className="form-stack"
        onSubmit={(event) => {
          event.preventDefault()
          if (channels.length) mutation.mutate()
        }}
      >
        <Field label="策略名称">
          <input
            required
            maxLength={200}
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="例如：教室离人后关闭指定照明"
          />
        </Field>
        <Field label="执行方式">
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value as 'SHADOW' | 'SIMULATED')}
          >
            <option value="SHADOW">影子评估 · 不下发命令</option>
            <option value="SIMULATED">模拟执行 · 仅模拟设备</option>
          </select>
        </Field>
        <div className="form-grid">
          <Field label="生效时间">
            <input
              required
              type="datetime-local"
              value={start}
              max={end}
              onChange={(event) => setStart(event.target.value)}
            />
          </Field>
          <Field label="结束时间（最多 7 天）">
            <input
              required
              type="datetime-local"
              value={end}
              min={start}
              onChange={(event) => setEnd(event.target.value)}
            />
          </Field>
        </div>
        <p className="timezone-hint">计划输入与显示时区：{browserTimezone()}</p>
        <fieldset className="room-target-fieldset">
          <legend>明确目标通道</legend>
          <p>不会自动添加新设备；真实多路硬件没有逐路执行协议时只读</p>
          {targets.length ? (
            <div className="form-stack">
              {targets.map((channel) => (
                <label className="checkbox-field" key={channel.channel_id}>
                  <input
                    type="checkbox"
                    checked={channels.includes(channel.channel_id)}
                    disabled={mode === 'SIMULATED' && channel.source_mode !== 'SIMULATED'}
                    onChange={(event) =>
                      setChannels(
                        event.target.checked
                          ? [...channels, channel.channel_id]
                          : channels.filter((id) => id !== channel.channel_id),
                      )
                    }
                  />
                  <span>
                    {channel.name} <SourceBadge value={channel.source_mode} />
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p className="small text-muted">此空间没有登记输出通道，不能创建控制策略</p>
          )}
        </fieldset>
        <div className="form-grid">
          <Field label="持续无人时间（秒）">
            <input
              type="number"
              min={30}
              max={7200}
              step={1}
              required
              value={vacancy}
              onChange={(event) => setVacancy(Number(event.target.value))}
            />
          </Field>
          <Field label="最小观测功率（W）">
            <input
              type="number"
              min={0}
              max={1000000}
              required
              value={power}
              onChange={(event) => setPower(Number(event.target.value))}
            />
          </Field>
        </div>
        <Field label="策略依据">
          <textarea
            required
            minLength={3}
            maxLength={1000}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </Field>
        <Notice tone="warning">
          策略只允许明确通道的“中断负载”动作。无课表、占用未知、过期观测或部分反馈不能代替无人证据。模型估计不是实测节能量。
        </Notice>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button onClick={onClose}>取消</Button>
          <Button
            type="submit"
            variant="primary"
            loading={mutation.isPending}
            disabled={
              !channels.length ||
              (mode === 'SIMULATED' &&
                channels.some(
                  (id) => targets.find((c) => c.channel_id === id)?.source_mode !== 'SIMULATED',
                ))
            }
          >
            保存策略
          </Button>
        </div>
      </form>
    </Modal>
  )
}
function EvaluationDetail({
  id,
  policy,
  room,
  canOperate,
  onClose,
}: {
  canOperate: boolean
  id: string
  policy: PolicyResponse
  room: RoomSnapshot
  onClose: () => void
}) {
  const client = useQueryClient()
  const [review, setReview] = useState(false)
  const [ack, setAck] = useState(false)
  const query = useResource<EvaluationResponse>(
    `/classrooms/evaluations/${encodeURIComponent(id)}`,
    { interval: (data) => (!data || data.execution_status === 'pending' ? 2000 : false) },
  )
  const dispatch = useMutation({
    mutationFn: () =>
      api.post<EvaluationResponse>(`/classrooms/evaluations/${encodeURIComponent(id)}/dispatch`),
    onSuccess: () => {
      setReview(false)
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  const d = query.data
  return (
    <Modal title="策略评估与执行反馈" onClose={onClose}>
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} />
      ) : (
        d && (
          <>
            <div className="inline-gap section-space">
              <Badge tone="blue">{policy.mode}</Badge>
              <StatusBadge value={d.execution_status} />
              <SourceBadge value={d.content.source_mode} />
            </div>
            <Notice title="可解释评估">{d.content.explanation}</Notice>
            <DefinitionList
              items={[
                ['目标教室', room.name],
                ['策略', `${policy.name} · v${d.policy_revision}`],
                ['评估时间', formatDate(d.at)],
                ['连续无人证据', durationLabel(d.content.vacancy_seconds)],
                ['当前模式', d.content.mode],
                ['合格通道', `${d.content.eligible_count} / ${d.content.targets.length}`],
                [
                  '模型估计可减少功率',
                  `${formatNumber(d.content.modeled_reduction_w)} W（不是实测节能）`,
                ],
                [
                  '已验证 / 未物理验证 / 失败 / 等待',
                  `${d.verified_count} / ${d.unverified_count} / ${d.failed_count} / ${d.pending_count}`,
                ],
              ]}
            />
            <DataTable
              rows={d.content.targets}
              rowKey={(row) => row.channel_id}
              columns={[
                {
                  key: 'channel',
                  title: '目标通道',
                  render: (row) =>
                    room.channels.find((c) => c.channel_id === row.channel_id)?.name ||
                    row.channel_id,
                },
                {
                  key: 'eligible',
                  title: '评估结果',
                  render: (row) => (
                    <Badge tone={row.eligible ? 'teal' : 'amber'}>
                      {row.eligible ? '符合条件' : '已阻止'}
                    </Badge>
                  ),
                },
                {
                  key: 'reason',
                  title: '依据 / 限制',
                  render: (row) =>
                    row.blocked_by.length
                      ? row.blocked_by.map(controlReason).join('；')
                      : '本次评估符合条件，执行时再次核验',
                },
              ]}
            />
            {d.commands.length > 0 && (
              <>
                <h3 className="section-title">执行反馈</h3>
                {d.commands.map((command) => (
                  <div className="room-policy-item" key={command.id}>
                    <div className="inline-gap">
                      <StatusBadge value={command.status} />
                      <Link
                        className="text-link"
                        to={`/commands?command=${encodeURIComponent(command.id)}`}
                      >
                        {command.device_id}
                        <ArrowRight size={12} />
                      </Link>
                    </div>
                    <p>命令 {command.id}</p>
                  </div>
                ))}
              </>
            )}
            {policy.mode === 'SHADOW' && (
              <Notice>影子策略仅评估，不会下发命令。没有执行结果，不展示节能成绩。</Notice>
            )}
            {canOperate && policy.enabled && policy.mode === 'SIMULATED' && !d.dispatched_at && (
              <>
                <Notice tone="warning">
                  只对本次合格的模拟目标申请执行；服务器将重新检查策略版本、无人证据、房间模式和安全条件。评估复核有效期为
                  30 秒，超时需要重新评估。
                </Notice>
                {review ? (
                  <>
                    <label className="checkbox-field">
                      <input
                        type="checkbox"
                        checked={ack}
                        onChange={(event) => setAck(event.target.checked)}
                      />
                      <span>确认以上教室、策略与模拟目标，执行中断负载动作</span>
                    </label>
                    <div className="form-actions">
                      <Button onClick={() => setReview(false)} disabled={dispatch.isPending}>
                        取消
                      </Button>
                      <Button
                        variant="primary"
                        loading={dispatch.isPending}
                        disabled={!ack}
                        onClick={() => dispatch.mutate()}
                      >
                        确认模拟执行
                      </Button>
                    </div>
                  </>
                ) : (
                  <Button
                    variant="primary"
                    disabled={!d.content.eligible_count}
                    onClick={() => {
                      setReview(true)
                      setAck(false)
                    }}
                  >
                    <Play size={15} />
                    复核模拟执行
                  </Button>
                )}
              </>
            )}
            {dispatch.error && <ErrorState error={dispatch.error} />}
          </>
        )
      )}
    </Modal>
  )
}
function PolicyToggle({ policy, onClose }: { policy: PolicyResponse; onClose: () => void }) {
  const client = useQueryClient()
  const [reason, setReason] = useState('')
  const mutation = useMutation({
    mutationFn: () =>
      api.patch<PolicyResponse>(`/classrooms/policies/${encodeURIComponent(policy.id)}`, {
        enabled: !policy.enabled,
        reason,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  return (
    <Modal
      title={`${policy.enabled ? '停用' : '重新启用'} · ${policy.name}`}
      onClose={() => {
        if (!mutation.isPending) onClose()
      }}
    >
      <form
        className="form-stack"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Notice tone="warning">
          {policy.enabled
            ? '停用会撤销后续策略执行与待处理命令的授权；已经执行的动作不会自动恢复。'
            : '重新启用会生成新版本；仍需新的评估和单独执行复核，旧评估不能沿用。'}
        </Notice>
        <Field label="策略变更原因">
          <textarea
            required
            minLength={3}
            maxLength={1000}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled={mutation.isPending}
          />
        </Field>
        {mutation.error && <ErrorState error={mutation.error} compact />}
        <div className="form-actions">
          <Button disabled={mutation.isPending} onClick={onClose}>
            取消
          </Button>
          <Button variant="primary" type="submit" loading={mutation.isPending}>
            {policy.enabled ? '确认停用' : '确认重新启用'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
export default function ClassroomPolicies({
  room,
  historical,
}: {
  room: RoomSnapshot
  historical: boolean
}) {
  const auth = useAuth()
  const client = useQueryClient()
  const [historyOffset, setHistoryOffset] = useState(0)
  const [changingPolicy, setChangingPolicy] = useState<PolicyResponse | null>(null)
  const [create, setCreate] = useState(false)
  const [selected, setSelected] = useState<{ id: string; policy: PolicyResponse } | null>(null)
  const query = useResource<PolicyResponse[]>(`/classrooms/${encodeURIComponent(room.id)}/policies`)
  const history = useCollection<EvaluationResponse>(
    `/classrooms/${encodeURIComponent(room.id)}/evaluations${queryString({ limit: 20, offset: historyOffset })}`,
  )
  const evaluate = useMutation({
    mutationFn: (policy: PolicyResponse) =>
      api
        .post<EvaluationResponse>(`/classrooms/policies/${encodeURIComponent(policy.id)}/evaluate`)
        .then((result) => ({ result, policy })),
    onSuccess: ({ result, policy }) => {
      setSelected({ id: result.id, policy })
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  const canOperate = permissions.operate(auth.session?.user.role) && !historical
  return (
    <Card>
      <CardHeader
        title="教室安全策略"
        subtitle={
          historical
            ? '当前策略配置与处理记录 · 历史快照只读'
            : '先评估，再复核执行，最后看真实回执'
        }
        actions={
          <Button variant="ghost" disabled={!canOperate} onClick={() => setCreate(true)}>
            <Plus size={14} />
            新建
          </Button>
        }
      />
      <div className="room-panel-body">
        <div className="inline-gap">
          <Badge tone="blue">
            <FlaskConical size={12} />
            影子 / 模拟
          </Badge>
          <Badge>
            <ShieldCheck size={12} />
            无真实自动投运
          </Badge>
        </div>
        {query.isLoading ? (
          <Loading compact />
        ) : query.error ? (
          <ErrorState error={query.error} compact />
        ) : !query.data?.length ? (
          <EmptyState title="尚无房间策略" description="从明确通道开始建立策略；默认不自动执行。" />
        ) : (
          query.data.map((policy) => (
            <article className="room-policy-item" key={policy.id}>
              <h3>{policy.name}</h3>
              <div className="inline-gap">
                <Badge tone="blue">{policy.mode}</Badge>
                <Badge>{policy.enabled ? '启用' : '停用'}</Badge>
              </div>
              <p>
                {formatDate(policy.starts_at)} → {formatDate(policy.ends_at)}
                <br />
                持续无人 {durationLabel(policy.config.vacant_for_seconds)} · 最少{' '}
                {formatNumber(policy.config.minimum_power_w)} W · 最多 {policy.config.max_commands}{' '}
                条命令
              </p>
              <p>{policy.config.reason}</p>
              <div className="form-actions">
                <Button
                  disabled={!canOperate || !policy.enabled}
                  loading={evaluate.isPending && evaluate.variables?.id === policy.id}
                  onClick={() => evaluate.mutate(policy)}
                >
                  <FlaskConical size={14} />
                  评估条件
                </Button>
                <Button
                  variant="ghost"
                  disabled={!canOperate}
                  onClick={() => setChangingPolicy(policy)}
                >
                  {policy.enabled ? '停用策略' : '重新启用'}
                </Button>
              </div>
            </article>
          ))
        )}
        {evaluate.error && <ErrorState error={evaluate.error} compact />}
        <h3 className="section-title">已保存的评估与执行</h3>
        {history.isLoading ? (
          <Loading compact />
        ) : history.error ? (
          <ErrorState error={history.error} compact retry={() => void history.refetch()} />
        ) : !history.data?.data.length ? (
          <p className="small text-muted">尚无评估记录。评估与执行后可在此重新查看。</p>
        ) : (
          history.data.data.map((evaluation) => {
            const policy = query.data?.find((item) => item.id === evaluation.policy_id)
            return (
              <article key={evaluation.id} className="room-policy-item">
                <div className="inline-gap">
                  <StatusBadge value={evaluation.execution_status} />
                  <SourceBadge value={evaluation.content.source_mode} />
                </div>
                <p>
                  {policy?.name || evaluation.policy_id} · {formatDate(evaluation.at)}
                  <br />
                  已验证 {evaluation.verified_count} · 未物理验证 {evaluation.unverified_count} ·
                  失败 {evaluation.failed_count} · 等待 {evaluation.pending_count}
                </p>
                <Button
                  variant="ghost"
                  disabled={!policy}
                  onClick={() => policy && setSelected({ id: evaluation.id, policy })}
                >
                  查看保存的反馈
                  <ArrowRight size={13} />
                </Button>
              </article>
            )
          })
        )}
        {Number(history.data?.meta?.total || 0) > 20 && (
          <Pagination
            offset={historyOffset}
            limit={20}
            total={Number(history.data?.meta?.total || 0)}
            setOffset={setHistoryOffset}
          />
        )}
      </div>
      {changingPolicy && (
        <PolicyToggle policy={changingPolicy} onClose={() => setChangingPolicy(null)} />
      )}
      {create && <PolicyForm room={room} onClose={() => setCreate(false)} />}
      {selected && (
        <EvaluationDetail
          id={selected.id}
          policy={selected.policy}
          room={room}
          canOperate={canOperate}
          onClose={() => setSelected(null)}
        />
      )}
    </Card>
  )
}
