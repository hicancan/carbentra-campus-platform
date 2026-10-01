import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ClassroomMode from './ClassroomMode'
import { roomFixture } from '../test-fixtures/classroom'
const state = vi.hoisted(() => ({ role: 'operator', patch: vi.fn() }))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: state.role } } }) }))
vi.mock('../lib/api', async (original) => ({
  ...(await original<typeof import('../lib/api')>()),
  api: { patch: state.patch },
}))
function show(historical = false) {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
    >
      <ClassroomMode room={roomFixture()} historical={historical} />
    </QueryClientProvider>,
  )
}
beforeEach(() => {
  state.role = 'operator'
  state.patch.mockReset()
  state.patch.mockResolvedValue({ mode: 'manual' })
})
describe('bounded classroom modes', () => {
  it('is read-only for historical snapshots and viewers', () => {
    show(true)
    expect(screen.getByRole('button', { name: '人工接管' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '检修保护' })).toBeDisabled()
    expect(state.patch).not.toHaveBeenCalled()
  })
  it('sends explicit bounded duration and reason for manual takeover', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '人工接管' }))
    fireEvent.change(screen.getByLabelText('操作原因'), { target: { value: '保留现场教学供电' } })
    fireEvent.click(screen.getByRole('button', { name: '保存模式' }))
    await waitFor(() =>
      expect(state.patch).toHaveBeenCalledWith('/classrooms/space%3Atest%3A101/mode', {
        mode: 'manual',
        duration_seconds: 3600,
        reason: '保留现场教学供电',
      }),
    )
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
  it('requires specific acknowledgement before automatic mode can be saved', async () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '更多模式' }))
    expect(screen.getByRole('button', { name: '保存模式' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('操作原因'), { target: { value: '复核模拟策略范围' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: '保存模式' }))
    await waitFor(() =>
      expect(state.patch).toHaveBeenCalledWith('/classrooms/space%3Atest%3A101/mode', {
        mode: 'automatic',
        duration_seconds: null,
        reason: '复核模拟策略范围',
      }),
    )
  })
  it('cancel preserves server state and does not submit', () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '检修保护' }))
    fireEvent.click(screen.getByRole('button', { name: '取消' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(state.patch).not.toHaveBeenCalled()
  })
})
