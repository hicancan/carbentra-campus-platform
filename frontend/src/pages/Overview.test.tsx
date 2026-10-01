import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Overview from './Overview'
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: 'viewer' } } }) }))
vi.mock('../lib/scope', () => ({ useScope: () => ({ campusId: '' }) }))
vi.mock('../lib/hooks', () => ({
  useResource: () => ({
    isLoading: false,
    isFetching: false,
    error: null,
    refetch: vi.fn(),
    data: {
      source_mode: 'MIXED',
      generated_at: '2026-09-30T10:00:00Z',
      freshness: {
        status: 'fresh',
        latest_sample_at: '2026-09-30T10:00:00Z',
        stale_after_seconds: 60,
      },
      counts: {
        buildings: 1,
        spaces: 1,
        devices: 2,
        online_devices: 1,
        stale_devices: 0,
        offline_devices: 0,
        unknown_devices: 1,
        active_alarms: 0,
      },
      energy: {
        known_kwh: 10,
        coverage_ratio: 0.9,
        quality: 'partial',
        period_start: '2026-09-29T10:00:00Z',
        period_end: '2026-09-30T10:00:00Z',
        source_mode: 'SIMULATED',
      },
      power: { active_kw: 1, quality: 'good', source_mode: 'REAL' },
      carbon: { kg_co2e: null, quality: 'unknown' },
      cost: { amount: null, currency: null, quality: 'unknown' },
      trend: [],
      buildings: [],
      alarms: [],
    },
  }),
}))
describe('overview evidence boundaries', () => {
  it('keeps historical energy and current power provenance distinct and unknown currency unknown', () => {
    render(
      <MemoryRouter>
        <Overview />
      </MemoryRouter>,
    )
    expect(screen.getByText('统计期已知用电').closest('.metric')).toHaveTextContent('SIMULATED')
    expect(screen.getByText('当前总有功功率').closest('.metric')).toHaveTextContent('REAL')
    expect(screen.getByText('当前总有功功率').closest('.metric')).not.toHaveTextContent('SIMULATED')
    expect(screen.getByText('MIXED')).toBeVisible()
    expect(screen.getByText('估算用能成本').closest('.metric')).not.toHaveTextContent('CNY')
    expect(screen.getByText('未见观测')).toBeVisible()
    expect(screen.getByRole('heading', { name: '常用操作' })).toBeVisible()
  })
})
