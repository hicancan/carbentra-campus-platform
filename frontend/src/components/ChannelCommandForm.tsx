import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, LockKeyhole, Send } from 'lucide-react'
import { api, permissions } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { Device, Command } from '../lib/types'
import type { ChannelSnapshot } from '../lib/classroom-types'
import type { ControlEligibility, ControlAction } from '../lib/control-eligibility'
import { controlReason } from '../lib/control-eligibility'
import { formatDate } from '../lib/format'
import { BooleanState } from './ClassroomState'
import { Button, DefinitionList, ErrorState, Field, Notice, SourceBadge, StatusBadge } from './ui'

/** Channel-scoped simulated control. A device ID alone never identifies a multi-relay target. */
export default function ChannelCommandForm({
  device,
  channel,
  eligibility,
  receivedAt,
}: {
  device: Device
  channel: ChannelSnapshot
  eligibility: ControlEligibility
  receivedAt: number
}) {
  const auth = useAuth()
  const client = useQueryClient()
  const [action, setAction] = useState<ControlAction>('hold')
  const [reason, setReason] = useState('')
  const [expiry, setExpiry] = useState(30)
  const [scenario, setScenario] = useState('success')
  const [holdSeconds, setHoldSeconds] = useState(0)
  const [ack, setAck] = useState(false)
  const [now, setNow] = useState(Date.now)
  const key = useRef(crypto.randomUUID())
  const [result, setResult] = useState<Command | null>(null)
  const identity = `${device.id}|${channel.channel_id}|${channel.channel_key}|${channel.binding_id}|${channel.source_mode}`
  const reviewIdentity = JSON.stringify([
    identity,
    channel.value?.desired_on,
    channel.value?.actuator_reported_on,
    channel.value?.output_present,
    channel.manual_hold_until,
    eligibility.profile_revision,
    eligibility.eligible,
    eligibility.allowed_actions,
  ])
  useEffect(() => setAck(false), [reviewIdentity])
  useEffect(() => {
    setAck(false)
    setResult(null)
    key.current = crypto.randomUUID()
  }, [identity])
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])
  const check = (time: number) => {
    if (!permissions.operate(auth.session?.user.role)) return '当前角色不可申请控制'
    if (
      device.id !== channel.device_id ||
      eligibility.device_id !== device.id ||
      eligibility.channel_id !== channel.channel_id ||
      eligibility.channel_key !== channel.channel_key
    )
      return '通道身份与设备授权检查不一致'
    if (
      eligibility.product_family !== channel.product_family ||
      eligibility.verification_kind !== channel.verification_kind
    )
      return '通道验证能力与授权检查不一致'
    if (
      device.source_mode !== 'SIMULATED' ||
      channel.source_mode !== 'SIMULATED' ||
      eligibility.source_mode !== 'SIMULATED'
    )
      return '教室逐通道操作仅开放模拟执行；真实硬件保持闭锁'
    if (
      !Number.isFinite(receivedAt) ||
      receivedAt <= 0 ||
      time - receivedAt > 15000 ||
      time < receivedAt - 1000
    )
      return '通道授权检查已过期，等待重新核验'
    if (!eligibility.eligible || !eligibility.allowed_actions.includes(action))
      return controlReason(
        eligibility.reasons[action] || channel.block_reason || 'control_not_authorized',
      )
    return null
  }
  const blocker = check(now)
  const mutation = useMutation({
    mutationFn: () => {
      const currentBlocker = check(Date.now())
      if (currentBlocker || !ack) throw new Error(currentBlocker || '请核对本次明确通道与动作')
      return api
        .post<Command>(
          '/commands',
          {
            device_id: device.id,
            channel_id: channel.channel_id,
            action,
            reason,
            expires_in_seconds: expiry,
            simulation_scenario: scenario,
            ...(holdSeconds ? { manual_hold_seconds: holdSeconds } : {}),
          },
          key.current,
        )
        .then((command) => {
          if (command.device_id !== device.id || command.channel_id !== channel.channel_id)
            throw new Error('返回命令的设备或通道与申请不一致，请立即核查命令追踪；不要重复提交')
          return command
        })
    },
    onSuccess: (command) => {
      setResult(command)
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  const reset = () => {
    setAck(false)
    setResult(null)
    key.current = crypto.randomUUID()
    mutation.reset()
  }
  const actions: { id: ControlAction; label: string }[] = [
    { id: 'restore', label: '开启此通道' },
    { id: 'shed', label: '关闭此通道' },
    { id: 'hold', label: '保持此通道' },
  ]
  return (
    <form
      className="form-stack"
      onSubmit={(event) => {
        event.preventDefault()
        if (!blocker && ack) mutation.mutate()
      }}
    >
      <Notice title="明确到通道的模拟申请">
        只申请下面这一路，不把选择扩展成整个设备。设备执行回报不证明灯具已亮、负载通电或现场安全隔离。
      </Notice>
      <DefinitionList
        items={[
          ['设备', `${device.name} · ${device.id}`],
          ['目标通道', `${channel.name} · ${channel.channel_key}`],
          ['稳定通道身份', channel.channel_id],
          ['安装绑定', channel.binding_id ?? '未知'],
          ['来源', <SourceBadge value={channel.source_mode} />],
          ['设备执行回报', <BooleanState value={channel.value?.actuator_reported_on} />],
          [
            '验证依据',
            eligibility.verification_kind === 'actuator_reported_only'
              ? '仅执行器回报，不证明物理负载状态'
              : '独立输出反馈',
          ],
          ['现有后台接管截止', formatDate(channel.manual_hold_until)],
          [
            '输出物理反馈',
            <BooleanState
              value={channel.value?.output_present}
              unavailable={!channel.feedback_supported}
            />,
          ],
          ['服务端最近核验', formatDate(eligibility.checked_at)],
        ]}
      />
      <Field label="本次通道动作">
        <select
          value={action}
          disabled={mutation.isPending}
          onChange={(event) => {
            setAction(event.target.value as ControlAction)
            reset()
          }}
        >
          {actions.map((item) => (
            <option
              value={item.id}
              key={item.id}
              disabled={!eligibility.allowed_actions.includes(item.id)}
            >
              {item.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="通道申请原因">
        <textarea
          required
          minLength={3}
          maxLength={500}
          value={reason}
          disabled={mutation.isPending}
          onChange={(event) => {
            setReason(event.target.value)
            reset()
          }}
          placeholder="明确这一路的操作依据…"
        />
      </Field>
      <div className="form-grid">
        <Field label="命令有效期（秒）">
          <input
            required
            type="number"
            min={1}
            max={60}
            value={expiry}
            disabled={mutation.isPending}
            onChange={(event) => {
              setExpiry(Number(event.target.value))
              reset()
            }}
          />
        </Field>
        <Field label="模拟执行场景">
          <select
            value={scenario}
            disabled={mutation.isPending}
            onChange={(event) => {
              setScenario(event.target.value)
              reset()
            }}
          >
            <option value="success">正常设备应答</option>
            <option value="reject">边缘拒绝</option>
            <option value="fail">执行失败</option>
            <option value="timeout">回执超时</option>
          </select>
        </Field>
      </div>
      <Field
        label="此通道人工接管时限"
        hint="仅覆盖后台 / 边缘对所选通道的自动策略，不改变设备本地按键保护；不扩展到其他通道"
      >
        <select
          value={holdSeconds}
          disabled={mutation.isPending}
          onChange={(event) => {
            setHoldSeconds(Number(event.target.value))
            reset()
          }}
        >
          <option value={0}>不接管 · 仅本次命令</option>
          <option value={900}>人工接管此通道 15 分钟</option>
          <option value={3600}>人工接管此通道 1 小时</option>
          <option value={7200}>人工接管此通道 2 小时</option>
          <option value={28800}>人工接管此通道 8 小时</option>
        </select>
      </Field>
      <label className="checkbox-field">
        <input
          type="checkbox"
          checked={ack}
          disabled={!!blocker || mutation.isPending}
          onChange={(event) => setAck(event.target.checked)}
        />
        <span>已核对 {channel.channel_key} 这一路与本次动作；理解设备执行回报不是独立物理反馈</span>
      </label>
      {blocker && (
        <Notice tone="warning">
          <LockKeyhole size={14} />
          {blocker}
        </Notice>
      )}
      {mutation.error && <ErrorState error={mutation.error} compact />}
      {result ? (
        <Notice title="通道命令已保存，执行结果仍需追踪">
          <StatusBadge value={result.status} />
          <Link className="text-link" to={`/commands?command=${encodeURIComponent(result.id)}`}>
            追踪此通道命令
            <ArrowRight size={14} />
          </Link>
        </Notice>
      ) : (
        <Button
          type="submit"
          variant="primary"
          disabled={!!blocker || !ack}
          loading={mutation.isPending}
        >
          <Send size={15} />
          提交此通道申请
        </Button>
      )}
      <p className="small text-muted">
        不接管不会撤销既有保护。“保持此通道”保留其已知执行状态；选择接管时限后，这一路的自动策略暂时让位。整个教室的接管在房间运行模式面板单独设置。
      </p>
    </form>
  )
}
