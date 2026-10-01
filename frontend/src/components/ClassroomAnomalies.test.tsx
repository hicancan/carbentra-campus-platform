import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ClassroomAnomalyDetail } from './ClassroomAnomalies'
import { anomalyFixture } from '../test-fixtures/classroom'
const state = vi.hoisted(() => ({ role: 'operator', post: vi.fn() }))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: state.role } } }) }))
vi.mock('../lib/api', async (original) => ({
  ...(await original<typeof import('../lib/api')>()),
  api: { post: state.post },
}))
function show() {
  render(
    <MemoryRouter>
      <QueryClientProvider client={new QueryClient()}>
        <ClassroomAnomalyDetail anomaly={anomalyFixture()} onClose={vi.fn()} />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}
beforeEach(() => {
  state.role = 'operator'
  state.post.mockReset()
  state.post.mockResolvedValue({ ...anomalyFixture(), status: 'acknowledged' })
})
describe('historical anomaly evidence and lifecycle', () => {
  it('discloses insufficient baseline and unknown threshold without filling zeros', () => {
    show()
    expect(screen.getByText('历史数据不足，不能认定已学习可靠基线')).toBeVisible()
    expect(screen.getByText('异常阈值').parentElement).toHaveTextContent('— W')
    expect(screen.getByText('历史中位基线').parentElement).toHaveTextContent('— W')
    expect(screen.getByText(/rule-test-v1/)).toBeVisible()
    expect(screen.getByRole('link', { name: '打开教室' })).toHaveAttribute(
      'href',
      '/classrooms/space%3Atest%3A101',
    )
  })
  it('records an acknowledgement with evidence then switches to the resolve action', async () => {
    show()
    fireEvent.change(screen.getByLabelText(/诊断或处置证据/), {
      target: { value: '已核验现场并开始诊断' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认异常' }))
    await waitFor(() =>
      expect(state.post).toHaveBeenCalledWith('/classrooms/anomalies/anomaly%3Atest/acknowledge', {
        note: '已核验现场并开始诊断',
      }),
    )
    await waitFor(() => expect(screen.getByRole('button', { name: '提交解决记录' })).toBeVisible())
  })
  it('viewer sees evidence but no lifecycle mutation form', () => {
    state.role = 'viewer'
    show()
    expect(screen.queryByRole('button', { name: '确认异常' })).toBeNull()
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})
