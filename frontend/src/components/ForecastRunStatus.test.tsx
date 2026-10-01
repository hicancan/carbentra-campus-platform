import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import ForecastRunStatus from './ForecastRunStatus'
import { forecastRefreshInterval } from '../lib/forecast-state'
import type { Forecast } from '../lib/types'
const fixture = (
  status: 'queued' | 'stale' | 'ready' | 'failed',
  worker: 'queued' | 'ready' | 'failed' = 'queued',
) =>
  ({
    generated_at: '2026-09-30T12:00:00Z',
    points: [
      { timestamp: '2026-09-30T13:00:00Z', predicted_kw: null, lower_kw: null, upper_kw: null },
    ],
    evaluation: {
      id: 'run-1',
      status,
      worker_status: worker,
      requested_at: '2026-09-30T12:10:00Z',
      started_at: null,
      completed_at: null,
      input_revision: 'new',
      result_input_revision: null,
      projection_pending_hours: 12,
      retry_after_seconds: 5,
      error_code: worker === 'failed' ? 'projection_failed' : null,
      cached: status === 'stale',
    },
  }) as Forecast
describe('persisted forecast progress', () => {
  it('polls active work every five seconds and backs off a completed or failed worker', () => {
    expect(forecastRefreshInterval(fixture('queued'))).toBe(5000)
    expect(forecastRefreshInterval(fixture('stale'))).toBe(5000)
    expect(forecastRefreshInterval(fixture('ready', 'ready'))).toBe(30000)
    expect(forecastRefreshInterval(fixture('stale', 'failed'))).toBe(30000)
  })
  it('shows queued null predictions as not generated', () => {
    render(
      <ForecastRunStatus
        forecast={fixture('queued')}
        retrying={false}
        retryError={null}
        onRetry={vi.fn()}
      />,
    )
    expect(screen.getByText('已排队')).toBeVisible()
    expect(screen.getByText(/尚无结果的时点保持未知/)).toBeVisible()
    expect(screen.getByText(/尚未生成/)).toBeVisible()
    expect(screen.queryByRole('button')).toBeNull()
  })
  it('keeps a stale result distinct and offers an explicit failed-job retry', () => {
    const retry = vi.fn()
    render(
      <ForecastRunStatus
        forecast={fixture('stale', 'failed')}
        retrying={false}
        retryError={null}
        onRetry={retry}
      />,
    )
    expect(screen.getByText('更新失败，保留上次结果')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: '重新排队分析' }))
    expect(retry).toHaveBeenCalledOnce()
  })
})
