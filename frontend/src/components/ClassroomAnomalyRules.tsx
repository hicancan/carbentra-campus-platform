import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings2, ShieldCheck } from 'lucide-react'
import { api, ApiError, permissions } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import type { AnomalyRuleResponse } from '../lib/classroom-types'
import { formatDate } from '../lib/format'
import { Badge, Button, DefinitionList, ErrorState, Field, Loading, Modal, Notice } from './ui'

type Config = AnomalyRuleResponse['config']
function completeConfig(config: Config) {
  return (
    typeof config.enabled === 'boolean' &&
    [
      'vacant_power_threshold_w',
      'vacant_persistence_seconds',
      'data_quality_persistence_seconds',
      'high_load_minimum_w',
      'baseline_multiplier',
      'baseline_mad_multiplier',
      'high_load_persistence_seconds',
      'clear_hysteresis_ratio',
    ].every(
      (key) =>
        typeof config[key as keyof Config] === 'number' &&
        Number.isFinite(config[key as keyof Config]),
    )
  )
}
function RuleEditor({
  data,
  readOnly,
  onClose,
  onSaving,
  onReload,
}: {
  onSaving: (saving: boolean) => void
  onReload: () => void
  data: AnomalyRuleResponse
  readOnly: boolean
  onClose: () => void
}) {
  const auth = useAuth()
  const client = useQueryClient()
  const [config, setConfig] = useState<Config>(data.config)
  const [reason, setReason] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const canEdit = !readOnly && permissions.operate(auth.session?.user.role)
  const mutation = useMutation({
    mutationFn: () => {
      if (!canEdit || !reviewed) throw new Error('请核对规则变更内容与原因')
      return api.patch<AnomalyRuleResponse>(
        `/classrooms/${encodeURIComponent(data.space_id)}/anomaly-rule`,
        { ...config, expected_revision: data.revision, reason },
      )
    },
    onMutate: () => onSaving(true),
    onSettled: () => onSaving(false),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      onClose()
    },
  })
  const change = <K extends keyof Config>(key: K, value: Config[K]) => {
    setConfig((previous) => ({ ...previous, [key]: value }))
    setReviewed(false)
    mutation.reset()
  }
  const numeric = (
    key: keyof Config,
    label: string,
    min: number,
    max: number,
    step: number | 'any' = 1,
    hint?: string,
  ) => (
    <Field label={label} hint={hint}>
      <input
        type="number"
        required
        min={min}
        max={max}
        step={step}
        disabled={!canEdit || mutation.isPending}
        value={Number(config[key])}
        onChange={(event) => change(key, Number(event.target.value) as Config[typeof key])}
      />
    </Field>
  )
  return (
    <form
      className="form-stack"
      onSubmit={(event) => {
        event.preventDefault()
        if (canEdit && reviewed) mutation.mutate()
      }}
    >
      <div className="inline-gap">
        <Badge tone="blue">规则版本 {data.revision}</Badge>
        <Badge>仅此教室</Badge>
      </div>
      <Notice tone="warning" title="工程默认值不是现场校准结论">
        阈值、动态系数和持续时间必须结合安装位置、设备能力与历史覆盖逐步核验。修改规则不能使缺失的观测或不足的基线变得可靠。
      </Notice>
      <DefinitionList
        items={[
          ['空间身份', data.space_id],
          ['最近更新', formatDate(data.updated_at)],
          ['修改人员', data.updated_by || '平台工程默认配置'],
          ['上次原因', data.reason || '尚未修改默认规则'],
        ]}
      />
      <label className="checkbox-field">
        <input
          type="checkbox"
          checked={config.enabled}
          disabled={!canEdit || mutation.isPending}
          onChange={(event) => change('enabled', event.target.checked)}
        />
        <span>启用此教室异常检测</span>
      </label>
      <h3 className="section-title">无人负载与数据质量</h3>
      <div className="form-grid">
        {numeric('vacant_power_threshold_w', '无人负载阈值（W）', 0, 10000000, 'any')}
        {numeric('vacant_persistence_seconds', '无人负载持续时间（秒）', 30, 7200)}
        {numeric('data_quality_persistence_seconds', '数据质量异常持续时间（秒）', 30, 86400)}
      </div>
      <h3 className="section-title">条件历史基线</h3>
      <div className="form-grid">
        {numeric('high_load_minimum_w', '高负载最小阈值（W）', 0, 10000000, 'any')}
        {numeric('baseline_multiplier', '历史中位数动态系数', 1, 10, 'any')}
        {numeric('baseline_mad_multiplier', 'MAD 动态系数', 0, 20, 'any')}
        {numeric('high_load_persistence_seconds', '高负载持续时间（秒）', 30, 7200)}
        {numeric(
          'clear_hysteresis_ratio',
          '解除回差比例',
          0,
          0.9,
          'any',
          '0.10 表示 10%；用于减少阈值附近的反复开闭事件',
        )}
      </div>
      <Notice>
        新版本对后续评估生效。旧异常保留当时的规则版本、阈值和观测证据；规则变更不会改写历史检测依据，也不替代设备控制联锁。
      </Notice>
      {canEdit && (
        <>
          <Field label="规则修改原因">
            <textarea
              required
              minLength={3}
              maxLength={1000}
              disabled={mutation.isPending}
              value={reason}
              onChange={(event) => {
                setReason(event.target.value)
                setReviewed(false)
              }}
              placeholder="记录调整依据，例如最近的误报证据或安装环境变化…"
            />
          </Field>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={reviewed}
              disabled={mutation.isPending}
              onChange={(event) => setReviewed(event.target.checked)}
            />
            <span>已核对上述阈值与此教室，理解这些参数仍需要工程验证</span>
          </label>
        </>
      )}
      {mutation.error && <ErrorState error={mutation.error} compact />}
      {mutation.error instanceof ApiError && mutation.error.status === 409 && (
        <Button variant="ghost" onClick={onReload}>
          读取最新版本（放弃未保存修改）
        </Button>
      )}
      <div className="form-actions">
        <Button disabled={mutation.isPending} onClick={onClose}>
          {canEdit ? '取消' : '关闭'}
        </Button>
        {canEdit && (
          <Button type="submit" variant="primary" disabled={!reviewed} loading={mutation.isPending}>
            <ShieldCheck size={15} />
            保存新规则版本
          </Button>
        )}
      </div>
    </form>
  )
}
export default function ClassroomAnomalyRules({
  spaceId,
  readOnly = false,
}: {
  spaceId: string
  readOnly?: boolean
}) {
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editingData, setEditingData] = useState<AnomalyRuleResponse | null>(null)
  const query = useResource<AnomalyRuleResponse>(
    `/classrooms/${encodeURIComponent(spaceId)}/anomaly-rule`,
    { enabled: open, interval: false },
  )
  useEffect(() => {
    if (open && !editingData && query.data && completeConfig(query.data.config))
      setEditingData(query.data)
  }, [open, editingData, query.data])
  const reload = async () => {
    const result = await query.refetch()
    if (result?.data && completeConfig(result.data.config)) setEditingData(result.data)
  }
  const editor = editingData || query.data
  return (
    <>
      <Button
        variant="ghost"
        onClick={() => {
          setEditingData(null)
          setOpen(true)
        }}
      >
        <Settings2 size={14} />
        规则设置
      </Button>
      {open && (
        <Modal
          title="教室异常规则"
          onClose={() => {
            if (!saving) setOpen(false)
          }}
        >
          {query.data && editingData && query.data.revision !== editingData.revision && (
            <Notice tone="warning">
              服务端已有更新版本。你正在编辑的内容已保留；保存时会执行版本冲突检查。
            </Notice>
          )}
          {query.isLoading && !editor ? (
            <Loading label="正在读取已保存的规则参数…" />
          ) : query.error && !editor ? (
            <ErrorState error={query.error} retry={() => void query.refetch()} />
          ) : editor && completeConfig(editor.config) ? (
            <RuleEditor
              key={`${spaceId}:${editor.revision}`}
              data={editor}
              onSaving={setSaving}
              onReload={() => void reload()}
              readOnly={readOnly}
              onClose={() => setOpen(false)}
            />
          ) : (
            <Notice tone="warning">规则配置暂不可用，不能使用客户端默认值覆盖</Notice>
          )}
        </Modal>
      )}
    </>
  )
}
