import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Hand, ShieldCheck, Wrench } from 'lucide-react'
import { api, permissions } from '../lib/api'
import { useAuth } from '../lib/auth'
import type { ModeResponse, OperationMode, RoomSnapshot } from '../lib/classroom-types'
import { roomStateLabel } from '../lib/classroom-display'
import { formatDate } from '../lib/format'
import { Button, Card, CardHeader, DefinitionList, ErrorState, Field, Modal, Notice } from './ui'
import { ClassroomState } from './ClassroomState'
export default function ClassroomMode({
  room,
  historical,
}: {
  room: RoomSnapshot
  historical: boolean
}) {
  const auth = useAuth()
  const client = useQueryClient()
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<OperationMode>('manual')
  const [duration, setDuration] = useState(3600)
  const [reason, setReason] = useState('')
  const [ack, setAck] = useState(false)
  const mutation = useMutation({
    mutationFn: () =>
      api.patch<ModeResponse>(`/classrooms/${encodeURIComponent(room.id)}/mode`, {
        mode,
        duration_seconds: mode === 'automatic' ? null : duration,
        reason,
      }),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ['resource'] })
      setOpen(false)
      setReason('')
      setAck(false)
    },
  })
  const canOperate = permissions.operate(auth.session?.user.role) && !historical
  const reviewNeeded = mode === 'automatic' || ['maintenance', 'fault'].includes(room.mode)
  return (
    <Card>
      <CardHeader
        title="运行模式与接管"
        subtitle="模式切换有有效期、有原因、可审计"
        actions={<ClassroomState value={room.mode} />}
      />
      <div className="room-panel-body">
        <DefinitionList
          items={[
            ['当前模式', roomStateLabel(room.mode)],
            [
              '有效截止',
              room.mode_expires_at ? formatDate(room.mode_expires_at) : '默认模式 / 未设置临时窗口',
            ],
            [
              '操作原因',
              room.mode_reason === 'No active automatic authorization'
                ? '尚无有效自动策略授权'
                : room.mode_reason || '尚无人工模式记录',
            ],
          ]}
        />
        <Notice tone={['maintenance', 'fault'].includes(room.mode) ? 'warning' : 'info'}>
          {room.mode === 'maintenance'
            ? '检修保护阻止策略与设备控制，但不能替代现场挂牌、隔离与验电。'
            : room.mode === 'fault'
              ? '故障闭锁中。解除软件闭锁不等于现场故障已经排除。'
              : room.mode === 'manual'
                ? '人工模式下不自动执行房间策略；单独控制仍需设备安全检查。'
                : '自动模式仅允许满足策略、占用、质量与设备安全门禁的动作。'}
        </Notice>
        {mutation.isSuccess && <Notice tone="success">模式更新已记录</Notice>}
        <div className="inline-gap">
          <Button
            disabled={!canOperate}
            onClick={() => {
              setMode('manual')
              setAck(false)
              setOpen(true)
            }}
          >
            <Hand size={14} />
            人工接管
          </Button>
          <Button
            disabled={!canOperate}
            onClick={() => {
              setMode('maintenance')
              setAck(false)
              setOpen(true)
            }}
          >
            <Wrench size={14} />
            检修保护
          </Button>
          <Button
            variant="ghost"
            disabled={!canOperate}
            onClick={() => {
              setMode('automatic')
              setAck(false)
              setOpen(true)
            }}
          >
            更多模式
          </Button>
        </div>
        {historical && (
          <p className="small text-muted section-space">历史快照不可更改当前运行模式</p>
        )}
      </div>
      {open && (
        <Modal
          title={`${room.name} · 设置运行模式`}
          onClose={() => {
            if (!mutation.isPending) setOpen(false)
          }}
        >
          <form
            className="form-stack"
            onSubmit={(event) => {
              event.preventDefault()
              if (canOperate && (!reviewNeeded || ack)) mutation.mutate()
            }}
          >
            <Field label="运行模式">
              <select
                value={mode}
                disabled={mutation.isPending}
                onChange={(event) => {
                  setMode(event.target.value as OperationMode)
                  setAck(false)
                  mutation.reset()
                }}
              >
                <option value="manual">人工接管</option>
                <option value="maintenance">检修保护</option>
                <option value="automatic">自动策略</option>
                <option value="fault">故障闭锁</option>
              </select>
            </Field>
            {mode !== 'automatic' && (
              <Field label="保护 / 接管持续时间">
                <select
                  value={duration}
                  onChange={(event) => setDuration(Number(event.target.value))}
                >
                  <option value={900}>15 分钟</option>
                  <option value={3600}>1 小时</option>
                  <option value={7200}>2 小时</option>
                  <option value={28800}>8 小时</option>
                  <option value={86400}>24 小时</option>
                </select>
              </Field>
            )}
            <Field label="操作原因">
              <textarea
                required
                minLength={3}
                maxLength={1000}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="说明接管、检修或恢复的依据…"
              />
            </Field>
            <Notice tone="warning">
              {mode === 'automatic'
                ? '自动策略不会因切换模式立即证明执行成功；它仍受无人持续时间、有效观测与控制授权门禁约束。'
                : '这是平台软件保护，不能证明现场已断电或安全隔离。到期行为以服务端策略为准。'}
            </Notice>
            {reviewNeeded && (
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(event) => setAck(event.target.checked)}
                />
                <span>我已核对教室和当前保护状态，确认本次模式变更依据</span>
              </label>
            )}
            {mutation.error && <ErrorState error={mutation.error} compact />}
            <div className="form-actions">
              <Button onClick={() => setOpen(false)} disabled={mutation.isPending}>
                取消
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={mutation.isPending}
                disabled={reviewNeeded && !ack}
              >
                <ShieldCheck size={15} />
                保存模式
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </Card>
  )
}
