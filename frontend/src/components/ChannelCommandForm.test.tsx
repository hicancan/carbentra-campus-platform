import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChannelCommandForm from './ChannelCommandForm'
import type { Device } from '../lib/types'
import type { ControlEligibility } from '../lib/control-eligibility'
import { channelFixture } from '../test-fixtures/classroom'
const state = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: 'operator' } } }) }))
vi.mock('../lib/api', async (original) => ({
  ...(await original<typeof import('../lib/api')>()),
  api: { post: state.post },
}))
const channel = () =>
  channelFixture({
    channel_id: 'switch:test:relay.2',
    channel_key: 'relay.2',
    device_id: 'switch:test',
    name: '教室照明第二路',
    kind: 'lighting',
    product_family: 'SWITCH',
    feedback_supported: false,
    verification_kind: 'actuator_reported_only',
    value: { desired_on: true, actuator_reported_on: true, output_present: null },
  })
const device = {
  id: 'switch:test',
  name: '测试三路开关',
  kind: 'switch',
  source_mode: 'SIMULATED',
} as Device
const eligibility = (): ControlEligibility => ({
  device_id: device.id,
  device_name: device.name,
  channel_id: channel().channel_id,
  channel_key: 'relay.2',
  product_family: 'SWITCH',
  verification_kind: 'actuator_reported_only',
  profile_revision: 1,
  source_mode: 'SIMULATED',
  dispatch_mode: 'IN_PROCESS',
  eligible: true,
  allowed_actions: ['hold', 'shed', 'restore'],
  reasons: { hold: null, shed: null, restore: null },
  physical_deployment_enabled: false,
  load: { id: 'load:test', name: '测试第二路', profile_id: 'test' },
  release: null,
  checked_at: new Date().toISOString(),
  server_rechecks_on_submission_and_lease: true,
  consequence: 'Simulated channel command',
})
function show(overrides: Partial<ControlEligibility> = {}, receivedAt = Date.now()) {
  render(
    <MemoryRouter>
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}
      >
        <ChannelCommandForm
          device={device}
          channel={channel()}
          eligibility={{ ...eligibility(), ...overrides }}
          receivedAt={receivedAt}
        />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}
beforeEach(() => {
  state.post.mockReset()
  state.post.mockResolvedValue({
    id: 'command:test',
    status: 'acknowledged_unverified',
    device_id: device.id,
    channel_id: channel().channel_id,
  })
})
describe('exact multi-relay command targeting', () => {
  it('submits only selected relay2 and an explicitly bounded backend hold', async () => {
    show()
    fireEvent.change(screen.getByLabelText('本次通道动作'), { target: { value: 'shed' } })
    fireEvent.change(screen.getByLabelText('通道申请原因'), {
      target: { value: '测试只关闭第二路' },
    })
    fireEvent.change(screen.getByLabelText(/此通道人工接管时限/), { target: { value: '900' } })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: '提交此通道申请' }))
    await waitFor(() =>
      expect(state.post).toHaveBeenCalledWith(
        '/commands',
        expect.objectContaining({
          device_id: 'switch:test',
          channel_id: 'switch:test:relay.2',
          action: 'shed',
          manual_hold_seconds: 900,
        }),
        expect.any(String),
      ),
    )
    expect(screen.getByText('设备已应答 · 未物理验证')).toBeVisible()
    expect(screen.getByText('无反馈能力')).toBeVisible()
  })
  it('one-shot action does not invent a hold or broaden to wholedevice', async () => {
    show()
    fireEvent.change(screen.getByLabelText('通道申请原因'), {
      target: { value: '保持当前第二路状态' },
    })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: '提交此通道申请' }))
    await waitFor(() => expect(state.post).toHaveBeenCalled())
    expect(state.post.mock.calls[0][1]).not.toHaveProperty('manual_hold_seconds')
    expect(state.post.mock.calls[0][1].channel_id).toBe('switch:test:relay.2')
  })
  it.each([
    { channel_id: 'switch:test:relay.1' },
    { channel_key: 'relay.3' },
    { source_mode: 'REAL' as const },
  ])('fails closed if target identity or source differs: %j', (overrides) => {
    show(overrides)
    expect(screen.getByRole('button', { name: '提交此通道申请' })).toBeDisabled()
    expect(state.post).not.toHaveBeenCalled()
  })
  it('expires stale eligibility and resets acknowledgement on action changes', () => {
    show({}, Date.now() - 16000)
    expect(screen.getByRole('button', { name: '提交此通道申请' })).toBeDisabled()
    expect(screen.getByText('通道授权检查已过期，等待重新核验')).toBeVisible()
  })
  it('clears prior confirmation when the reviewed action changes', () => {
    show()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(screen.getByRole('checkbox')).toBeChecked()
    fireEvent.change(screen.getByLabelText('本次通道动作'), { target: { value: 'restore' } })
    expect(screen.getByRole('checkbox')).not.toBeChecked()
    expect(state.post).not.toHaveBeenCalled()
  })
})
