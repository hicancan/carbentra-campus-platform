import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowRight, Send } from 'lucide-react'
import { api } from '../lib/api'
import type { Command, Evaluation, Strategy } from '../lib/types'
import { formatDate } from '../lib/format'
import { Button, ErrorState, Field, Notice, StatusBadge } from './ui'
export default function StrategyDispatch({
  strategy,
  evaluation,
}: {
  strategy: Strategy
  evaluation: Evaluation
}) {
  const client = useQueryClient()
  const [reason, setReason] = useState('')
  const [ack, setAck] = useState(false)
  const key = useRef(crypto.randomUUID())
  const [commands, setCommands] = useState<Command[] | null>(null)
  const mutation = useMutation({
    mutationFn: () =>
      api.post<{ commands: Command[]; evaluation_id: string; physical_dispatch: false }>(
        `/strategies/${encodeURIComponent(strategy.id)}/dispatch`,
        { evaluation_id: evaluation.id, reason },
        key.current,
      ),
    onSuccess: (result) => {
      setCommands(result.commands)
      void client.invalidateQueries({ queryKey: ['resource'] })
    },
  })
  if (!evaluation.candidate_device_ids.length) return null
  return (
    <div className="dispatch-section">
      <h3 className="section-title">单独授权模拟调度</h3>
      <Notice tone="warning" title="审批不会自动下发">
        本次将为已批准评估中的 {evaluation.candidate_device_ids.length}{' '}
        台设备逐一生成模拟削减命令。服务端在下发前再次检查时效与联锁。评估有效至{' '}
        {formatDate(new Date(Date.parse(evaluation.created_at) + 5 * 60000).toISOString())}。
      </Notice>
      {commands ? (
        <>
          <Notice tone="success" title="模拟调度已受理">
            已持久化 {commands.length} 条命令，等待关联回执。受理不代表执行或验证完成。
          </Notice>
          <div className="dispatch-results">
            {commands.map((c) => (
              <Link to={`/commands?command=${encodeURIComponent(c.id)}`} key={c.id}>
                <span>{c.device_id}</span>
                <StatusBadge value={c.status} />
                <ArrowRight size={14} />
              </Link>
            ))}
          </div>
        </>
      ) : (
        <form
          className="form-stack"
          onSubmit={(e) => {
            e.preventDefault()
            mutation.mutate()
          }}
        >
          <Field label="调度原因">
            <textarea
              minLength={3}
              maxLength={1000}
              required
              value={reason}
              onChange={(e) => {
                setReason(e.target.value)
                key.current = crypto.randomUUID()
                mutation.reset()
              }}
            />
          </Field>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
              required
            />
            <span>已核对当前评估的全部候选设备，授权本次模拟削减；理解现场不会执行</span>
          </label>
          {mutation.error && <ErrorState error={mutation.error} />}
          <Button variant="primary" type="submit" disabled={!ack} loading={mutation.isPending}>
            <Send size={15} />
            下发 {evaluation.candidate_device_ids.length} 条模拟命令
          </Button>
        </form>
      )}
    </div>
  )
}
