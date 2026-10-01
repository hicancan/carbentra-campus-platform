import { Clock3, RefreshCw } from 'lucide-react'
import type { Forecast } from '../lib/types'
import { forecastRunLabel } from '../lib/forecast-state'
import { formatDate, formatNumber } from '../lib/format'
import { Badge, Button, ErrorState } from './ui'
export default function ForecastRunStatus({
  forecast,
  retrying,
  retryError,
  onRetry,
}: {
  forecast: Forecast
  retrying: boolean
  retryError: unknown
  onRetry: () => void
}) {
  const e = forecast.evaluation
  if (!e) return null
  const failed = e.status === 'failed' || e.worker_status === 'failed'
  const waiting = e.status !== 'ready' && !failed
  return (
    <div className={`forecast-run-status ${failed ? 'run-failed' : ''}`}>
      <div className="inline-between">
        <Badge tone={failed ? 'red' : e.status === 'ready' ? 'teal' : 'amber'}>
          <Clock3 size={12} />
          {forecastRunLabel(e)}
        </Badge>
        {failed && (
          <Button className="button-small" loading={retrying} onClick={onRetry}>
            <RefreshCw size={13} />
            重新排队分析
          </Button>
        )}
      </div>
      {waiting && (
        <p role="status">
          {e.cached
            ? '正在读取新的输入批次；图表保留上次结果及其原始时间。'
            : '首次结果正在由分析服务准备，尚无结果的时点保持未知。'}{' '}
          每 5 秒检查一次进度。
        </p>
      )}
      {failed && (
        <p>
          分析服务未能完成此批次，可手动重试。
          {e.error_code && (
            <>
              错误标识：<code>{e.error_code}</code>
            </>
          )}
        </p>
      )}
      <div className="forecast-run-times">
        <span>请求 {formatDate(e.requested_at)}</span>
        <span>本次完成 {formatDate(e.completed_at)}</span>
        <span>
          {e.cached ? '保留结果生成' : '结果生成'}{' '}
          {forecast.points.some((p) => p.predicted_kw !== null)
            ? formatDate(forecast.generated_at)
            : '尚未生成'}
        </span>
        {e.projection_pending_hours > 0 && (
          <span>待投影 {formatNumber(e.projection_pending_hours, 0)} 个设备小时</span>
        )}
      </div>
      {!!retryError && <ErrorState error={retryError} compact />}
    </div>
  )
}
