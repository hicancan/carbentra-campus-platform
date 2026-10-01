import type { PhysicalConfirmation } from '../lib/control-eligibility'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, LockKeyhole, ShieldAlert } from 'lucide-react'
import { api, permissions, queryString } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useResource } from '../lib/hooks'
import type { Command, Device } from '../lib/types'
import type { ControlAction, ControlEligibility } from '../lib/control-eligibility'
import { controlActionLabel, controlReason, physicalGateBlocker } from '../lib/control-eligibility'
import { formatDate } from '../lib/format'
import {
  Button,
  DefinitionList,
  ErrorState,
  Field,
  Loading,
  Modal,
  Notice,
  SourceBadge,
  StatusBadge,
} from './ui'
import CommandForm from './CommandForm'
import ChannelCommandForm from './ChannelCommandForm'
import { classroomPath } from '../lib/classroom-display'
import type { ChannelSnapshot } from '../lib/classroom-types'
function PhysicalCommandForm({
  device,
  eligibility,
  receivedAt,
}: {
  device: Device
  eligibility: ControlEligibility
  receivedAt: number
}) {
  const client = useQueryClient()
  const [action, setAction] = useState<ControlAction>(eligibility.allowed_actions[0])
  const [reason, setReason] = useState(''),
    [expiry, setExpiry] = useState(30),
    [review, setReview] = useState(false),
    [ack, setAck] = useState(false),
    [result, setResult] = useState<Command | null>(null),
    [now, setNow] = useState(Date.now)
  const key = useRef(crypto.randomUUID())
  const [reviewed, setReviewed] = useState<{
    deviceId: string
    deviceName: string
    loadId: string
    loadName: string
    releaseId: string
    profileRevision: number
    action: ControlAction
    reason: string
    expiry: number
    consequence: string
  } | null>(null)
  const identity = JSON.stringify([
    device.id,
    device.name,
    eligibility.load.id,
    eligibility.load.name,
    eligibility.release?.id,
    eligibility.profile_revision,
    eligibility.consequence,
  ])
  useEffect(() => {
    setAck(false)
  }, [identity])
  const reviewMatches =
    reviewed !== null &&
    reviewed.deviceId === device.id &&
    reviewed.deviceName === device.name &&
    reviewed.loadId === eligibility.load.id &&
    reviewed.loadName === eligibility.load.name &&
    reviewed.releaseId === eligibility.release?.id &&
    reviewed.profileRevision === eligibility.profile_revision &&
    reviewed.consequence === eligibility.consequence &&
    reviewed.action === action &&
    reviewed.reason === reason &&
    reviewed.expiry === expiry
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const blocker = physicalGateBlocker(eligibility, device.id, receivedAt, now)
  const allowed = !blocker && eligibility.allowed_actions.includes(action)
  const reset = () => {
    key.current = crypto.randomUUID()
    setAck(false)
    setReview(false)
    setReviewed(null)
    setResult(null)
    mutation.reset()
  }
  const mutation = useMutation({
    mutationFn: () => {
      const currentBlocker = physicalGateBlocker(eligibility, device.id, receivedAt, Date.now())
      if (currentBlocker || !allowed || !ack || !reviewMatches || !reviewed)
        throw new Error(currentBlocker || blocker || '请重新核对负载与动作')
      const confirmation: PhysicalConfirmation = {
        device_id: reviewed.deviceId,
        load_id: reviewed.loadId,
        action: reviewed.action,
        release_id: reviewed.releaseId,
        profile_revision: reviewed.profileRevision,
        understands_mains_consequence: true,
      }
      return api.post<Command>(
        '/commands',
        {
          device_id: reviewed.deviceId,
          action: reviewed.action,
          reason: reviewed.reason,
          expires_in_seconds: reviewed.expiry,
          physical_confirmation: confirmation,
        },
        key.current,
      )
    },
    onSuccess: (command) => {
      setReview(false)
      setResult(command)
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  const close = useCallback(() => {
    if (!mutation.isPending) setReview(false)
  }, [mutation.isPending])
  return (
    <>
      <Notice tone="warning" title="现场实际负载操作">
        仅针对下方明确命名的负载。操作可能实际中断或恢复交流市电；命令回执与反馈不证明安全隔离，检修仍需现场程序。
      </Notice>
      <DefinitionList
        items={[
          ['设备', `${device.name} · ${device.id}`],
          ['明确负载', `${eligibility.load.name} · ${eligibility.load.id}`],
          ['独立放行记录', eligibility.release?.id],
          ['设备配置版本', eligibility.profile_revision],
          ['放行有效期', formatDate(eligibility.release?.valid_until)],
          ['服务端最近核验', formatDate(eligibility.checked_at)],
          ['依据', '操作人员声明与独立部署门禁，不替代硬件检定'],
        ]}
      />
      {blocker && <Notice tone="warning">{blocker}</Notice>}
      {result ? (
        <Notice tone="success" title="实际命令已受理，等待执行证据">
          <StatusBadge value={result.status} />
          <Link className="text-link" to={`/commands?command=${encodeURIComponent(result.id)}`}>
            打开命令追踪
            <ArrowRight size={14} />
          </Link>
          受理不代表设备已执行，更不代表已完成现场隔离。
        </Notice>
      ) : (
        <form
          className="form-stack"
          onSubmit={(event) => {
            event.preventDefault()
            if (allowed && eligibility.load.id && eligibility.load.name && eligibility.release) {
              setAck(false)
              setReviewed({
                deviceId: device.id,
                deviceName: device.name,
                loadId: eligibility.load.id,
                loadName: eligibility.load.name,
                releaseId: eligibility.release.id,
                profileRevision: eligibility.profile_revision,
                action,
                reason,
                expiry,
                consequence: eligibility.consequence,
              })
              setReview(true)
            }
          }}
        >
          <div className="form-grid">
            <Field label="实际负载动作">
              <select
                value={action}
                disabled={mutation.isPending}
                onChange={(e) => {
                  setAction(e.target.value as ControlAction)
                  reset()
                }}
              >
                {eligibility.allowed_actions.map((a) => (
                  <option value={a} key={a}>
                    {controlActionLabel(a)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="命令有效期（秒）">
              <input
                type="number"
                min="1"
                max="60"
                value={expiry}
                disabled={mutation.isPending}
                onChange={(e) => {
                  setExpiry(Number(e.target.value))
                  reset()
                }}
                required
              />
            </Field>
          </div>
          <Field label="现场操作原因">
            <textarea
              minLength={3}
              maxLength={1000}
              value={reason}
              disabled={mutation.isPending}
              onChange={(e) => {
                setReason(e.target.value)
                reset()
              }}
              required
            />
          </Field>
          <Button type="submit" variant="danger" disabled={!allowed} loading={mutation.isPending}>
            <ShieldAlert size={16} />
            复核实际负载操作
          </Button>
        </form>
      )}
      {review && reviewed && (
        <Modal title="确认本次实际负载操作" onClose={close}>
          <Notice tone="warning" title="这不是模拟">
            动作可能实际改变市电输出。请确认负载、设备与动作均正确，且已完成必要的现场协调。
          </Notice>
          <DefinitionList
            items={[
              ['设备', `${reviewed.deviceName} · ${reviewed.deviceId}`],
              ['负载', `${reviewed.loadName} · ${reviewed.loadId}`],
              ['本次动作', controlActionLabel(reviewed.action)],
              ['申请原因', reviewed.reason],
              ['命令有效期', `${reviewed.expiry} 秒`],
              ['服务端提示', reviewed.consequence],
              ['本次放行记录', reviewed.releaseId],
              ['已复核配置版本', reviewed.profileRevision],
            ]}
          />
          {!reviewMatches && (
            <Notice tone="warning">
              负载身份或放行依据已变化。请取消后重新复核，不沿用之前的确认。
            </Notice>
          )}
          <label className="checkbox-field section-space">
            <input
              type="checkbox"
              checked={ack}
              disabled={!reviewMatches || mutation.isPending}
              onChange={(e) => setAck(e.target.checked)}
            />
            <span>
              我已核对上述明确负载和本次动作，理解可能实际中断或恢复市电，反馈不能证明安全隔离
            </span>
          </label>
          {blocker && <Notice tone="warning">{blocker}</Notice>}
          {mutation.error && <ErrorState error={mutation.error} />}
          <div className="form-actions">
            <Button onClick={close} disabled={mutation.isPending}>
              取消
            </Button>
            <Button
              variant="danger"
              disabled={!allowed || !ack || !reviewMatches}
              loading={mutation.isPending}
              onClick={() => mutation.mutate()}
            >
              {action === 'shed'
                ? '确认实际中断负载'
                : action === 'restore'
                  ? '确认实际恢复供电'
                  : '确认实际保持状态'}
            </Button>
          </div>
        </Modal>
      )}
    </>
  )
}
export default function DeviceControlPanel({
  device,
  channel,
}: {
  device: Device
  channel?: ChannelSnapshot
}) {
  const auth = useAuth()
  const requiresChannel = !channel && ['switch', 'light'].includes(device.kind)
  const query = useResource<ControlEligibility>(
    `/devices/${encodeURIComponent(device.id)}/control-eligibility${queryString({ channel_id: channel?.channel_id })}`,
    { interval: 5000, enabled: !requiresChannel },
  )
  const e = query.data
  if (!permissions.operate(auth.session?.user.role))
    return <Notice>当前角色只能查看状态，不能申请控制命令</Notice>
  if (requiresChannel)
    return (
      <Notice tone="warning" title="先选择明确通道">
        此设备包含独立继电器通道，不能按整台设备申请开关。
        {device.space_id ? (
          <Link className="text-link" to={classroomPath(device.space_id)}>
            打开教室并选择通道
            <ArrowRight size={13} />
          </Link>
        ) : (
          '请先核验设备的空间与通道登记。'
        )}
      </Notice>
    )
  if (query.isLoading) return <Loading label="正在核验设备控制条件…" />
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch()
        }}
      />
    )
  if (!e || e.device_id !== device.id || e.source_mode !== device.source_mode)
    return <Notice tone="warning">无法确认设备身份与授权检查，控制保持关闭</Notice>
  if (channel)
    return (
      <ChannelCommandForm
        key={`${device.id}:${channel.channel_id}:${channel.binding_id}`}
        device={device}
        channel={channel}
        eligibility={e}
        receivedAt={query.dataUpdatedAt}
      />
    )
  if (device.source_mode === 'SIMULATED')
    return (
      <>
        {!e.eligible && (
          <Notice tone="warning" title="服务端安全检查">
            {[...new Set(Object.values(e.reasons).filter(Boolean).map(controlReason))].join('；')}
          </Notice>
        )}
        {e.eligible ? (
          <CommandForm device={device} />
        ) : (
          <div className="control-blocked">
            <LockKeyhole size={25} />
            <strong>模拟控制闭锁</strong>
            <p>待服务端安全条件恢复后再申请</p>
          </div>
        )}
      </>
    )
  const blocker = physicalGateBlocker(e, device.id, query.dataUpdatedAt)
  if (device.source_mode !== 'REAL' || blocker)
    return (
      <>
        <div className="control-blocked">
          <LockKeyhole size={25} />
          <strong>现场控制保持关闭</strong>
          <p>{device.source_mode === 'REPLAYED' ? '历史回放数据不允许控制现场' : blocker}</p>
          <SourceBadge value={device.source_mode} />
        </div>
        <DefinitionList
          items={[
            ['部署放行', e.physical_deployment_enabled ? '开关已配置，仍需设备检查' : '关闭'],
            ['明确负载', e.load.name || '尚未核验'],
            ['设备放行记录', e.release?.status || '不存在'],
            [
              '安全检查原因',
              [...new Set(Object.values(e.reasons).filter(Boolean).map(controlReason))].join(
                '；',
              ) || '暂无可用检查',
            ],
            ['最近核验', formatDate(e.checked_at)],
          ]}
        />
      </>
    )
  return (
    <PhysicalCommandForm
      key={`${e.device_id}|${e.load.id}|${e.release?.id}|${e.load.profile_id}|${e.profile_revision}`}
      device={device}
      eligibility={e}
      receivedAt={query.dataUpdatedAt}
    />
  )
}
