import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, LockKeyhole, Send, ShieldCheck } from 'lucide-react'
import { api, permissions } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { Command, Device } from '../lib/types'
import { classroomPath } from '../lib/classroom-display'
import { Button, ErrorState, Field, Notice, SourceBadge, StatusBadge } from './ui'
export function controlBlocker(device: Device): string | null {
  if (['switch', 'light'].includes(device.kind)) return '多路设备必须选择明确通道，不能整机申请开关'
  if (device.source_mode !== 'SIMULATED') return '此表单仅用于仿真设备；其他来源需单独检查控制资格'
  if (device.dispatch_mode === 'DISABLED') return '设备执行通道已停用'
  if (!['IN_PROCESS', 'VIRTUAL'].includes(device.dispatch_mode))
    return '仿真设备没有有效的模拟执行通道'
  if (!device.commissioned) return '设备尚未完成模拟投运'
  if (device.critical) return '关键负载受到保护'
  if (!device.allow_control) return '设备未获得控制授权'
  if (device.status !== 'online') return '设备数据不新鲜，安全闭锁'
  if (!device.latest || device.latest.quality !== 'good') return '缺少有效设备观测，安全闭锁'
  if (device.latest.fault_latched) return '设备本地故障已锁存'
  if (
    device.latest.fault_latched == null ||
    device.latest.output_present == null ||
    device.latest.desired_on == null
  )
    return '设备故障或输出状态未知，安全闭锁'
  if (!device.capabilities.some((c) => ['shed', 'restore', 'hold'].includes(c)))
    return '设备不具备控制能力'
  return null
}
export default function CommandForm({
  device,
  onCreated,
}: {
  device: Device
  onCreated?: (command: Command) => void
}) {
  const auth = useAuth()
  const client = useQueryClient()
  const [action, setAction] = useState(
    device.capabilities.find((c) => ['hold', 'shed', 'restore'].includes(c)) || 'hold',
  )
  const [reason, setReason] = useState('')
  const [scenario, setScenario] = useState('success')
  const [expiry, setExpiry] = useState(30)
  const [ack, setAck] = useState(false)
  const key = useRef(crypto.randomUUID())
  const [result, setResult] = useState<Command | null>(null)
  const mutation = useMutation({
    mutationFn: () =>
      api.post<Command>(
        '/commands',
        {
          device_id: device.id,
          action,
          reason,
          simulation_scenario: scenario,
          expires_in_seconds: expiry,
        },
        key.current,
      ),
    onSuccess: (command) => {
      setResult(command)
      void client.invalidateQueries({ queryKey: ['resource'] })
      onCreated?.(command)
    },
  })
  const reset = () => {
    key.current = crypto.randomUUID()
    mutation.reset()
    setResult(null)
  }
  const blocker = controlBlocker(device)
  if (!permissions.operate(auth.session?.user.role))
    return (
      <Notice title="只读权限">当前角色不能提交控制申请。操作需要运维操作员或管理员权限。</Notice>
    )
  if (blocker)
    return (
      <div className="control-blocked">
        <LockKeyhole size={24} />
        <strong>控制闭锁</strong>
        <p>{blocker}</p>
        <SourceBadge value={device.source_mode} />
        {device.space_id && ['switch', 'light'].includes(device.kind) && (
          <Link className="text-link" to={classroomPath(device.space_id)}>
            打开教室选择通道
            <ArrowRight size={13} />
          </Link>
        )}
      </div>
    )
  return (
    <form
      className="form-stack"
      onSubmit={(event) => {
        event.preventDefault()
        mutation.mutate()
      }}
    >
      <Notice title="仅执行模拟命令">
        命令由模拟执行器驱动完整回执流程。现场继电器不会动作，结果不能证明物理断电。
      </Notice>
      <div className="form-grid">
        <Field label="模拟动作">
          <select
            value={action}
            onChange={(e) => {
              setAction(e.target.value)
              reset()
            }}
          >
            {device.capabilities.includes('hold') && <option value="hold">保持当前状态</option>}
            {device.capabilities.includes('shed') && <option value="shed">模拟负载削减</option>}
            {device.capabilities.includes('restore') && (
              <option value="restore">模拟恢复供电</option>
            )}
          </select>
        </Field>
        <Field label="有效期（秒）">
          <input
            type="number"
            min="1"
            max="60"
            required
            value={expiry}
            onChange={(e) => {
              setExpiry(Number(e.target.value))
              reset()
            }}
          />
        </Field>
      </div>
      <Field label="申请原因">
        <textarea
          minLength={3}
          maxLength={500}
          required
          placeholder="记录操作原因，写入审计与命令追踪…"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value)
            reset()
          }}
        />
      </Field>
      <Field label="模拟故障场景">
        <select
          value={scenario}
          onChange={(e) => {
            setScenario(e.target.value)
            reset()
          }}
        >
          <option value="success">正常执行与验证</option>
          <option value="reject">边缘拒绝</option>
          <option value="fail">执行失败</option>
          <option value="timeout">回执超时</option>
        </select>
      </Field>
      <label className="checkbox-field">
        <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} required />
        <span>已确认这是模拟操作，并理解“回执验证”不代表现场安全隔离</span>
      </label>
      {mutation.error && <ErrorState error={mutation.error} compact />}
      {result ? (
        <Notice tone="success" title="命令已持久化">
          状态：
          <StatusBadge value={result.status} />
          。等待执行器回执，不将受理当作执行成功。
          <Link className="text-link" to={`/commands?command=${encodeURIComponent(result.id)}`}>
            追踪此命令
            <ArrowRight size={14} />
          </Link>
        </Notice>
      ) : (
        <Button type="submit" variant="primary" loading={mutation.isPending} disabled={!ack}>
          <Send size={15} />
          提交模拟命令
        </Button>
      )}
      <p className="small text-muted inline-gap">
        <ShieldCheck size={14} />
        服务端再次校验权限、能力、时效与设备联锁
      </p>
    </form>
  )
}
