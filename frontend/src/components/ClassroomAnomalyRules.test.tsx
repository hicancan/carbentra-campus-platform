import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ClassroomAnomalyRules from './ClassroomAnomalyRules'
import type { AnomalyRuleResponse } from '../lib/classroom-types'
import { ApiError } from '../lib/api'
const state = vi.hoisted(() => ({
  role: 'operator',
  patch: vi.fn(),
  refetch: vi.fn(),
  data: undefined as AnomalyRuleResponse | undefined,
  error: null as unknown,
}))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: state.role } } }) }))
vi.mock('../lib/api', async (original) => ({
  ...(await original<typeof import('../lib/api')>()),
  api: { patch: state.patch },
}))
vi.mock('../lib/hooks', () => ({
  useResource: () => ({
    data: state.data,
    isLoading: false,
    error: state.error,
    refetch: state.refetch,
  }),
}))
function show(readOnly = false) {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
    >
      <ClassroomAnomalyRules spaceId="space:test:101" readOnly={readOnly} />
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: '规则设置' }))
}
beforeEach(() => {
  state.role = 'operator'
  state.patch.mockReset()
  state.refetch.mockReset()
  state.error = null
  state.data = {
    space_id: 'space:test:101',
    revision: 7,
    updated_at: '2026-10-01T05:00:00Z',
    updated_by: 'test-operator',
    reason: '已有现场调整记录',
    defaults_are_engineering_assumptions: true,
    config: {
      enabled: true,
      vacant_power_threshold_w: 75,
      vacant_persistence_seconds: 420,
      data_quality_persistence_seconds: 360,
      high_load_minimum_w: 120,
      baseline_multiplier: 2.1,
      baseline_mad_multiplier: 4,
      high_load_persistence_seconds: 720,
      clear_hysteresis_ratio: 0.15,
    },
  }
  state.patch.mockResolvedValue({ ...state.data, revision: 8 })
})
describe('versioned classroom anomaly rules', () => {
  it('loads authoritative configured values rather than hardcoded engineering defaults', () => {
    show()
    expect(screen.getByLabelText('无人负载阈值（W）')).toHaveValue(75)
    expect(screen.getByLabelText('历史中位数动态系数')).toHaveValue(2.1)
    expect(screen.getByText('规则版本 7')).toBeVisible()
    expect(screen.getByText('工程默认值不是现场校准结论')).toBeVisible()
  })
  it('requires reason and confirmation and sends optimistic revision without a blind overwrite', async () => {
    show()
    expect(screen.getByRole('button', { name: '保存新规则版本' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('无人负载阈值（W）'), { target: { value: '85' } })
    fireEvent.change(screen.getByLabelText('规则修改原因'), {
      target: { value: '依据最近现场误报调整' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /已核对上述阈值/ }))
    fireEvent.click(screen.getByRole('button', { name: '保存新规则版本' }))
    await waitFor(() =>
      expect(state.patch).toHaveBeenCalledWith(
        '/classrooms/space%3Atest%3A101/anomaly-rule',
        expect.objectContaining({
          vacant_power_threshold_w: 85,
          baseline_multiplier: 2.1,
          expected_revision: 7,
          reason: '依据最近现场误报调整',
        }),
      ),
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
  it('keeps conflict visible and requires explicit reload instead of silently retrying', async () => {
    state.patch.mockRejectedValue(
      new ApiError('Rule revision changed', 409, 'rule_revision_conflict'),
    )
    show()
    fireEvent.change(screen.getByLabelText('规则修改原因'), {
      target: { value: '需要调整异常检测' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /已核对上述阈值/ }))
    fireEvent.click(screen.getByRole('button', { name: '保存新规则版本' }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeVisible())
    expect(state.patch).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: '读取最新版本（放弃未保存修改）' }))
    expect(state.refetch).toHaveBeenCalledTimes(1)
  })
  it('keeps an in-progress edit when a background refetch discovers a newer revision', () => {
    const client = new QueryClient()
    const tree = () => (
      <QueryClientProvider client={client}>
        <ClassroomAnomalyRules spaceId="space:test:101" />
      </QueryClientProvider>
    )
    const view = render(tree())
    fireEvent.click(screen.getByRole('button', { name: '规则设置' }))
    fireEvent.change(screen.getByLabelText('无人负载阈值（W）'), { target: { value: '85' } })
    state.data = {
      ...state.data!,
      revision: 8,
      config: { ...state.data!.config, vacant_power_threshold_w: 100 },
    }
    view.rerender(tree())
    expect(screen.getByLabelText('无人负载阈值（W）')).toHaveValue(85)
    expect(screen.getByText('规则版本 7')).toBeVisible()
    expect(screen.getByText(/你正在编辑的内容已保留/)).toBeVisible()
  })
  it('historical views are strictly read-only even for an operator', () => {
    show(true)
    expect(screen.getByLabelText('无人负载阈值（W）')).toBeDisabled()
    expect(screen.queryByRole('button', { name: '保存新规则版本' })).toBeNull()
  })
  it('a failed configuration read never invents a writable client default', () => {
    state.error = new Error('Configuration unavailable')
    state.data = undefined
    show()
    expect(screen.getByRole('alert')).toBeVisible()
    expect(screen.queryByRole('spinbutton')).toBeNull()
    expect(state.patch).not.toHaveBeenCalled()
  })
})
