import type { Forecast } from './types'
export function forecastRefreshInterval(data?: Forecast): number {
  const evaluation = data?.evaluation
  if (!evaluation || evaluation.worker_status === 'failed') return 30_000
  return ['queued', 'running', 'stale'].includes(evaluation.status) ? 5000 : 30_000
}
export function forecastRunLabel(evaluation: NonNullable<Forecast['evaluation']>) {
  if (evaluation.status === 'stale')
    return evaluation.worker_status === 'failed' ? '更新失败，保留上次结果' : '历史结果待更新'
  return { queued: '已排队', running: '正在分析', ready: '分析已完成', failed: '分析未完成' }[
    evaluation.status
  ]
}
