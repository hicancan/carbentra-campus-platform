import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ClassroomPolicies from './ClassroomPolicies'
import { policyFixture, roomFixture } from '../test-fixtures/classroom'
import type { EvaluationResponse } from '../lib/classroom-types'
const state = vi.hoisted(() => ({
  role: 'operator',
  post: vi.fn(),
  patch: vi.fn(),
  policies: [] as ReturnType<typeof policyFixture>[],
  history: [] as EvaluationResponse[],
  evaluation: undefined as EvaluationResponse | undefined,
}))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: state.role } } }) }))
vi.mock('../lib/api', async (original) => ({
  ...(await original<typeof import('../lib/api')>()),
  api: { post: state.post, patch: state.patch },
}))
vi.mock('../lib/hooks', () => ({
  useResource: (path: string) => ({
    isLoading: false,
    data: path.includes('/evaluations/') ? state.evaluation : state.policies,
  }),
  useCollection: () => ({
    isLoading: false,
    data: { data: state.history, meta: { total: state.history.length } },
  }),
}))
const evaluation = (): EvaluationResponse => ({
  id: 'eval:test',
  policy_id: 'policy:test',
  space_id: 'space:test:101',
  campus_id: 'campus:test',
  at: '2026-10-01T04:00:00Z',
  policy_revision: 1,
  created_by: 'test',
  content: {
    occupancy: 'unknown',
    vacancy_seconds: 0,
    mode: 'manual',
    targets: [
      {
        channel_id: 'channel:test:plug:relay.1',
        device_id: 'device:test:plug',
        eligible: false,
        blocked_by: ['room_manual_mode', 'vacancy_not_persisted'],
        observed_power_w: null,
      },
    ],
    eligible_count: 0,
    modeled_reduction_w: null,
    savings_claim: false,
    source_mode: 'SIMULATED',
    explanation: 'Unknown occupancy cannot authorize control.',
  },
  command_ids: [],
  commands: [],
  dispatched_at: null,
  verified_count: 0,
  unverified_count: 0,
  failed_count: 0,
  pending_count: 0,
  execution_status: 'shadow',
})
function show(historical = false) {
  render(
    <MemoryRouter>
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
      >
        <ClassroomPolicies room={roomFixture()} historical={historical} />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}
beforeEach(() => {
  state.role = 'operator'
  state.post.mockReset()
  state.patch.mockReset()
  state.policies = [policyFixture()]
  state.history = []
  state.evaluation = evaluation()
  state.post.mockResolvedValue(state.evaluation)
  state.patch.mockResolvedValue({ ...policyFixture(), enabled: false, revision: 2 })
})
describe('room policy evaluation and persisted feedback', () => {
  it('historical views cannot create, evaluate or disable current policies', () => {
    show(true)
    expect(screen.getByRole('button', { name: '新建' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '评估条件' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '停用策略' })).toBeDisabled()
  })
  it('evaluates a shadow policy without dispatch and exposes blockers', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '评估条件' }))
    await waitFor(() =>
      expect(state.post).toHaveBeenCalledWith('/classrooms/policies/policy%3Atest/evaluate'),
    )
    await waitFor(() =>
      expect(screen.getByRole('dialog', { name: '策略评估与执行反馈' })).toBeVisible(),
    )
    expect(screen.getByText(/房间处于人工模式；无人证据未持续达到阈值/)).toBeVisible()
    expect(screen.queryByRole('button', { name: '确认模拟执行' })).toBeNull()
    expect(screen.getByText(/影子策略仅评估，不会下发命令/)).toBeVisible()
    expect(state.post).toHaveBeenCalledTimes(1)
  })
  it('reopens stored evaluations without creating a new evaluation', async () => {
    state.history = [evaluation()]
    show()
    fireEvent.click(screen.getByRole('button', { name: '查看保存的反馈' }))
    expect(screen.getByRole('dialog', { name: '策略评估与执行反馈' })).toBeVisible()
    expect(state.post).not.toHaveBeenCalled()
  })
  it('disables a policy only with an explicit reason and displays revocation implications', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '停用策略' }))
    expect(screen.getByText(/已经执行的动作不会自动恢复/)).toBeVisible()
    fireEvent.change(screen.getByLabelText('策略变更原因'), {
      target: { value: '教学计划变更，暂停策略' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认停用' }))
    await waitFor(() =>
      expect(state.patch).toHaveBeenCalledWith('/classrooms/policies/policy%3Atest', {
        enabled: false,
        reason: '教学计划变更，暂停策略',
      }),
    )
  })
  it('new policy defaults to shadow and has no preselected targets', () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '新建' }))
    expect(screen.getByLabelText('执行方式')).toHaveValue('SHADOW')
    expect(screen.getByRole('button', { name: '保存策略' })).toBeDisabled()
    expect(screen.getByRole('checkbox')).not.toBeChecked()
    expect(state.post).not.toHaveBeenCalled()
  })
})
