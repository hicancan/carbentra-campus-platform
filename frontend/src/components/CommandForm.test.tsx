import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import CommandForm, { controlBlocker } from './CommandForm'
import type { Device } from '../lib/types'
import { api } from '../lib/api'
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: 'operator' } } }) }))
vi.mock('../lib/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../lib/api')>()
  return { ...original, api: { ...original.api, post: vi.fn() } }
})
const device = {
  id: 'plug-1',
  name: '模拟插座',
  source_mode: 'SIMULATED',
  dispatch_mode: 'IN_PROCESS',
  commissioned: true,
  critical: false,
  allow_control: true,
  status: 'online',
  latest: { quality: 'good', fault_latched: false, desired_on: true, output_present: true },
  capabilities: ['hold', 'shed', 'restore'],
} as Device
beforeEach(() => {
  vi.mocked(api.post).mockReset()
})
describe('safe command boundary', () => {
  it('permits only an eligible simulation device', () => {
    expect(controlBlocker(device)).toBeNull()
  })
  it.each([
    { kind: 'switch' },
    { kind: 'light' },
    { source_mode: 'REAL' },
    { source_mode: 'REPLAYED' },
    { commissioned: false },
    { critical: true },
    { allow_control: false },
    { status: 'stale' },
    { status: 'offline' },
    { status: 'unknown' },
    { capabilities: ['metering'] },
    { dispatch_mode: 'DISABLED' },
    { dispatch_mode: 'PHYSICAL' },
    { dispatch_mode: undefined },
    { latest: { quality: 'good', fault_latched: null, desired_on: true, output_present: true } },
    { latest: { quality: 'good', fault_latched: false, desired_on: null, output_present: true } },
    { latest: { quality: 'good', fault_latched: false, desired_on: true, output_present: null } },
    { latest: null },
    { latest: { quality: 'invalid' } },
    { latest: { quality: 'good', fault_latched: true } },
  ])('fails closed for %j', (override) => {
    expect(controlBlocker({ ...device, ...override } as Device)).not.toBeNull()
  })
  it('does not show a submit button for real equipment', () => {
    const client = new QueryClient()
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <CommandForm device={{ ...device, source_mode: 'REAL' }} />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByText('控制闭锁')).toBeVisible()
    expect(screen.queryByText('提交模拟命令')).not.toBeInTheDocument()
  })
  it('requires explicit simulation acknowledgement and preserves server rejection', async () => {
    vi.mocked(api.post).mockRejectedValue(new Error('critical load interlock'))
    const client = new QueryClient({
      defaultOptions: { mutations: { retry: false, throwOnError: false } },
    })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <CommandForm device={device} />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('button', { name: '提交模拟命令' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('申请原因'), { target: { value: '验收模拟流程' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: '提交模拟命令' }))
    await waitFor(() => expect(screen.getByText('critical load interlock')).toBeVisible())
    expect(screen.queryByText('命令已持久化')).not.toBeInTheDocument()
    const key = vi.mocked(api.post).mock.calls[0][2]
    fireEvent.click(screen.getByRole('button', { name: '提交模拟命令' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(client.isMutating()).toBe(0))
    expect(vi.mocked(api.post).mock.calls[1][2]).toBe(key)
  })
})
