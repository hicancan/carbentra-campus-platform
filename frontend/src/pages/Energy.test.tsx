import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Energy from './Energy'
vi.mock('../lib/scope', () => ({ useScope: () => ({ campusId: '' }) }))
vi.mock('../components/Filters', () => ({
  initialRange: () => ({ start: '', end: '' }),
  BuildingFilter: () => null,
  PeriodFilter: () => null,
}))
vi.mock('../lib/hooks', () => ({
  useResource: (path: string) => ({
    data: path.startsWith('/energy/summary')
      ? {
          known_kwh: null,
          export_kwh: null,
          coverage_ratio: null,
          quality: 'unavailable',
          interval_count: 0,
          excluded_intervals: 0,
          device_count: 0,
          warnings: [],
          source_mode: 'UNKNOWN',
          selected_device_ids: [],
        }
      : path.startsWith('/energy/breakdown')
        ? [
            {
              id: null,
              name: '未绑定计量设备',
              known_kwh: null,
              coverage_ratio: 0,
              quality: 'unavailable',
              source_mode: 'UNKNOWN',
              device_count: 1,
            },
          ]
        : path.startsWith('/telemetry')
          ? []
          : undefined,
    error: null,
    isLoading: false,
  }),
}))
describe('nullable accounting evidence', () => {
  it('keeps an unknown coverage value unknown and accepts an unbound breakdown group', () => {
    render(
      <MemoryRouter>
        <Energy />
      </MemoryRouter>,
    )
    const metric = screen.getByText('有效数据覆盖').closest('.metric')
    expect(metric).toHaveTextContent('—')
    expect(metric).not.toHaveTextContent('0.00')
    expect(screen.getByText('未绑定计量设备')).toBeVisible()
  })
})
