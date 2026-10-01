import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, CircleCheck, ClipboardCheck, ScanLine, ShieldAlert } from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useCollection } from '../lib/hooks'
import { useScope } from '../lib/scope'
import type { AnomalyResponse } from '../lib/classroom-types'
import ClassroomAnomalyRules from './ClassroomAnomalyRules'
import { classroomPath, durationLabel } from '../lib/classroom-display'
import { formatDate, formatNumber } from '../lib/format'
import {
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionList,
  Drawer,
  EmptyState,
  ErrorState,
  Field,
  Loading,
  Notice,
  SourceBadge,
  StatusBadge,
} from './ui'

export const anomalyLabel = (value: string) =>
  (
    ({
      vacant_with_load: '无人时负载持续开启',
      vacant_load: '无人时负载持续开启',
      data_quality: '观测质量持续不足',
      conditional_high_load: '功率偏离条件历史基线',
      vacancy_load: '无人时负载持续开启',
      power_baseline: '功率偏离历史基线',
      power_outlier: '功率偏离历史基线',
      feedback_mismatch: '输出反馈与请求不一致',
      sensor_conflict: '存在证据冲突',
      stale_observation: '观测持续过期',
    }) as Record<string, string>
  )[value] || value
export function ClassroomAnomalyDetail({
  anomaly,
  onClose,
  readOnly = false,
}: {
  readOnly?: boolean
  anomaly: AnomalyResponse
  onClose: () => void
}) {
  const auth = useAuth()
  const client = useQueryClient()
  const [note, setNote] = useState('')
  const [action, setAction] = useState<'acknowledge' | 'resolve'>(
    anomaly.status === 'open' ? 'acknowledge' : 'resolve',
  )
  const mutation = useMutation({
    mutationFn: () =>
      api.post<AnomalyResponse>(
        `/classrooms/anomalies/${encodeURIComponent(anomaly.id)}/${action}`,
        { note },
      ),
    onSuccess: (updated) => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      if (updated.status === 'acknowledged') setAction('resolve')
      setNote('')
    },
  })
  const data = mutation.data || anomaly
  const evidence = data.evidence
  return (
    <Drawer title={anomalyLabel(data.type)} subtitle={data.id} onClose={onClose}>
      <div className="inline-gap section-space">
        <StatusBadge value={data.status} />
        <StatusBadge value={data.severity} />
        <SourceBadge value={data.source_mode} />
      </div>
      <Notice tone="warning" title="异常是待核实的线索">
        {evidence.explanation}
      </Notice>
      <div className="room-evidence-metrics">
        <div>
          <span>观测功率</span>
          <strong>
            {formatNumber(evidence.observed_power_w)} <small>W</small>
          </strong>
        </div>
        <div>
          <span>异常阈值</span>
          <strong>
            {formatNumber(evidence.threshold_w)} <small>W</small>
          </strong>
        </div>
        <div>
          <span>历史中位基线</span>
          <strong>
            {formatNumber(evidence.baseline_median_w)} <small>W</small>
          </strong>
        </div>
      </div>
      <DefinitionList
        items={[
          [
            '发生空间',
            <Link className="text-link" to={classroomPath(data.space_id)}>
              打开教室
              <ArrowUpRight size={13} />
            </Link>,
          ],
          ['事件起点', formatDate(data.episode_start)],
          ['最近观测', formatDate(data.last_observed_at)],
          ['评估时间', formatDate(evidence.evaluated_at)],
          ['规则版本', `${evidence.rule_version} · 配置修订 ${evidence.rule_revision}`],
          [
            '解除回差阈值',
            evidence.clear_threshold_w == null
              ? '不适用 / 未知'
              : `${formatNumber(evidence.clear_threshold_w)} W`,
          ],
          [
            '实际 / 要求持续时间',
            `${durationLabel(evidence.persistence_seconds)} / ${durationLabel(evidence.required_persistence_seconds)}`,
          ],
          [
            '基线状态',
            evidence.baseline_status === 'sufficient'
              ? '历史样本满足规则要求'
              : evidence.baseline_status === 'insufficient'
                ? '历史数据不足，不能认定已学习可靠基线'
                : '此规则不使用历史基线',
          ],
          ['历史样本数', evidence.baseline_sample_count],
          [
            'MAD 稳健离差',
            evidence.baseline_mad_w == null
              ? '不适用 / 未知'
              : `${formatNumber(evidence.baseline_mad_w)} W`,
          ],
          ['基线条件', evidence.baseline_condition],
          ['质量标记', evidence.quality_flags.join(' · ') || '无附加标记'],
          [
            '观测证据 ID',
            evidence.observation_ids.length
              ? evidence.observation_ids.join(' · ')
              : '无有效观测 ID',
          ],
        ]}
      />
      <h3 className="section-title">处理过程</h3>
      <div className="timeline">
        <div className="timeline-item">
          <span className="timeline-dot amber" />
          <div>
            <strong>发现异常</strong>
            <time>{formatDate(data.episode_start)}</time>
          </div>
        </div>
        {data.notes.map((entry, index) => (
          <div className="timeline-item" key={`${entry.at}-${index}`}>
            <span className="timeline-dot" />
            <div>
              <strong>
                {entry.by} · {entry.action}
              </strong>
              <time>{formatDate(entry.at)}</time>
              <p>{entry.text}</p>
            </div>
          </div>
        ))}
        {data.resolved_at && (
          <div className="timeline-item">
            <span className="timeline-dot teal" />
            <div>
              <strong>已解决</strong>
              <time>{formatDate(data.resolved_at)}</time>
            </div>
          </div>
        )}
      </div>
      {!readOnly && permissions.operate(auth.session?.user.role) && data.status !== 'resolved' && (
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate()
          }}
        >
          <Field label="处置动作">
            <select
              value={action}
              onChange={(event) => setAction(event.target.value as 'acknowledge' | 'resolve')}
            >
              {data.status === 'open' && <option value="acknowledge">确认并开始诊断</option>}
              <option value="resolve">记录解决证据</option>
            </select>
          </Field>
          <Field label="诊断或处置证据" hint="状态变更不代替现场确认；请记录实际观察和采取的措施">
            <textarea
              required
              minLength={3}
              maxLength={1000}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </Field>
          {mutation.error && <ErrorState error={mutation.error} compact />}
          {mutation.isSuccess && <Notice tone="success">处理记录已保存</Notice>}
          <Button type="submit" variant="primary" loading={mutation.isPending}>
            {action === 'resolve' ? <CircleCheck size={15} /> : <ClipboardCheck size={15} />}
            {action === 'resolve' ? '提交解决记录' : '确认异常'}
          </Button>
        </form>
      )}
    </Drawer>
  )
}
export default function ClassroomAnomalies({
  spaceId,
  buildingId,
  compact = false,
  readOnly = false,
}: {
  spaceId?: string
  buildingId?: string
  compact?: boolean
  readOnly?: boolean
}) {
  const scope = useScope()
  const auth = useAuth()
  const client = useQueryClient()
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<AnomalyResponse | null>(null)
  const query = useCollection<AnomalyResponse>(
    `/classrooms/anomalies${queryString({ campus_id: scope.campusId, building_id: buildingId, space_id: spaceId, status, limit: compact ? 30 : 2000 })}`,
  )
  const evaluate = useMutation({
    mutationFn: () =>
      api.post('/classrooms/anomalies/evaluate', {
        ...(scope.campusId ? { campus_id: scope.campusId } : {}),
        ...(buildingId ? { building_id: buildingId } : {}),
        ...(spaceId ? { space_id: spaceId } : {}),
      }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['resource'] }),
  })
  return (
    <Card>
      <CardHeader
        title="教室异常与证据"
        subtitle="持续性、历史基线与输出反馈共同形成可解释线索"
        actions={
          <>
            {spaceId && <ClassroomAnomalyRules spaceId={spaceId} readOnly={readOnly} />}
            {permissions.operate(auth.session?.user.role) && (
              <Button
                variant="ghost"
                disabled={readOnly}
                loading={evaluate.isPending}
                onClick={() => evaluate.mutate()}
              >
                <ScanLine size={14} />
                重新评估
              </Button>
            )}
          </>
        }
      />
      <div className="room-panel-body">
        <div className="inline-gap">
          <select
            aria-label="教室异常状态"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">全部历史事件</option>
            <option value="open">待处理</option>
            <option value="acknowledged">已确认</option>
            <option value="resolved">已解决</option>
          </select>
          <Badge>{Number(query.data?.meta?.total ?? query.data?.data.length ?? 0)} 条</Badge>
        </div>
        {evaluate.error && <ErrorState error={evaluate.error} compact />}
        {evaluate.isSuccess && (
          <p className="small text-muted section-space" role="status">
            评估已完成，结果以服务端证据为准
          </p>
        )}
        {query.isLoading ? (
          <Loading compact />
        ) : query.error ? (
          <ErrorState error={query.error} compact retry={() => void query.refetch()} />
        ) : !query.data?.data.length ? (
          <EmptyState
            title="当前筛选没有异常事件"
            description="不代表已验证安全；没有有效观测时不会编造异常基线。"
            icon={<ShieldAlert size={26} />}
          />
        ) : (
          query.data.data.map((anomaly) => (
            <article className="room-anomaly-card" key={anomaly.id}>
              <div className="inline-gap">
                <StatusBadge value={anomaly.status} />
                <SourceBadge value={anomaly.source_mode} />
              </div>
              <h3>{anomalyLabel(anomaly.type)}</h3>
              <p>
                {formatDate(anomaly.episode_start)} 起 · 持续{' '}
                {durationLabel(anomaly.evidence.persistence_seconds)}
              </p>
              <p>{anomaly.evidence.explanation}</p>
              <Button variant="ghost" onClick={() => setSelected(anomaly)}>
                查看基线与证据
                <ArrowUpRight size={13} />
              </Button>
            </article>
          ))
        )}
        {Number(query.data?.meta?.total || 0) > (query.data?.data.length || 0) && (
          <Link
            className="text-link"
            to={`/alarms${queryString({ view: 'classrooms', space: spaceId, building: buildingId })}`}
          >
            查看完整异常历史
            <ArrowUpRight size={13} />
          </Link>
        )}
      </div>
      {selected && (
        <ClassroomAnomalyDetail
          readOnly={readOnly}
          anomaly={query.data?.data.find((a) => a.id === selected.id) || selected}
          onClose={() => setSelected(null)}
        />
      )}
    </Card>
  )
}
