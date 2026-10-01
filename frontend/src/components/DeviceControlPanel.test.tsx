import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import DeviceControlPanel from './DeviceControlPanel'
import type { Device } from '../lib/types'
import type { ControlEligibility } from '../lib/control-eligibility'
import { api } from '../lib/api'
const query = vi.hoisted(() => ({
  data: null as ControlEligibility | null,
  isLoading: false,
  error: null,
  dataUpdatedAt: 0,
  refetch: vi.fn(),
}))
vi.mock('../lib/hooks', () => ({ useResource: () => query }))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: 'operator' } } }) }))
vi.mock('../lib/api', async (original) => {
  const actual = await original<typeof import('../lib/api')>()
  return { ...actual, api: { ...actual.api, post: vi.fn() } }
})
const device = {
  id: 'inert-ui-device',
  name: 'INERT UI TEST DEVICE',
  source_mode: 'REAL',
  kind: 'smart_plug',
} as Device
beforeEach(() => {
  vi.mocked(api.post).mockReset()
  const now = Date.now()
  query.dataUpdatedAt = now
  query.data = {
    channel_id: null,
    channel_key: 'relay.1',
    product_family: 'PLUG',
    verification_kind: 'independent_feedback',
    device_id: device.id,
    device_name: device.name,
    source_mode: 'REAL',
    dispatch_mode: 'PHYSICAL',
    profile_revision: 7,
    eligible: true,
    allowed_actions: ['shed'],
    reasons: { hold: null, shed: null, restore: null },
    physical_deployment_enabled: true,
    load: { id: 'inert-load', name: 'INERT TEST LOAD NO ACTUATOR', profile_id: 'test' },
    release: {
      id: 'inert-release',
      status: 'released',
      valid_until: new Date(now + 60000).toISOString(),
      basis: 'operator_attestation',
    },
    checked_at: new Date(now).toISOString(),
    server_rechecks_on_submission_and_lease: true,
    consequence: 'Inert fixture only',
  }
})
function show() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const tree = () => (
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DeviceControlPanel device={device} />
      </MemoryRouter>
    </QueryClientProvider>
  )
  const view = render(tree())
  return () => view.rerender(tree())
}
describe('named-load confirmation UI with a mocked transport', () => {
  it('shows no physical-submit path when the delivered deployment gate is OFF', () => {
    query.data!.physical_deployment_enabled = false
    show()
    expect(screen.getByText('现场控制保持关闭')).toBeVisible()
    expect(screen.queryByRole('button', { name: '复核实际负载操作' })).toBeNull()
    expect(api.post).not.toHaveBeenCalled()
  })
  it('requires review and per-action consequence acknowledgement before a mocked submission', async () => {
    vi.mocked(api.post).mockResolvedValue({
      id: 'inert-command',
      status: 'requested',
      source_mode: 'REAL',
    })
    show()
    fireEvent.change(screen.getByLabelText('现场操作原因'), {
      target: { value: 'Inert UI fixture; never actuate' },
    })
    fireEvent.click(screen.getByRole('button', { name: '复核实际负载操作' }))
    expect(screen.getByRole('dialog', { name: '确认本次实际负载操作' })).toHaveTextContent(
      'INERT TEST LOAD NO ACTUATOR',
    )
    const confirm = screen.getByRole('button', { name: '确认实际中断负载' })
    expect(confirm).toBeDisabled()
    expect(api.post).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(confirm)
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce())
    expect(vi.mocked(api.post).mock.calls[0][1]).toMatchObject({
      device_id: 'inert-ui-device',
      action: 'shed',
      physical_confirmation: {
        device_id: 'inert-ui-device',
        load_id: 'inert-load',
        action: 'shed',
        release_id: 'inert-release',
        profile_revision: 7,
        understands_mains_consequence: true,
      },
    })
    await screen.findByText('实际命令已受理，等待执行证据')
  })
  it('lets a user cancel review without submitting anything', () => {
    show()
    fireEvent.change(screen.getByLabelText('现场操作原因'), {
      target: { value: 'Inert cancellation test' },
    })
    fireEvent.click(screen.getByRole('button', { name: '复核实际负载操作' }))
    fireEvent.click(screen.getByRole('button', { name: '取消' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(api.post).not.toHaveBeenCalled()
  })
  it('freezes the reviewed load name and clears acknowledgement after a same-ID rename', async () => {
    const rerender = show()
    fireEvent.change(screen.getByLabelText('现场操作原因'), {
      target: { value: 'Inert identity-change regression' },
    })
    fireEvent.click(screen.getByRole('button', { name: '复核实际负载操作' }))
    fireEvent.click(screen.getByRole('checkbox'))
    expect(screen.getByRole('button', { name: '确认实际中断负载' })).toBeEnabled()
    query.data = {
      ...query.data!,
      load: { ...query.data!.load, name: 'NEW INERT LOAD' },
    }
    rerender()
    expect(screen.getByRole('dialog', { name: '确认本次实际负载操作' })).toHaveTextContent(
      'INERT TEST LOAD NO ACTUATOR',
    )
    expect(screen.getByRole('dialog', { name: '确认本次实际负载操作' })).not.toHaveTextContent(
      'NEW INERT LOAD',
    )
    expect(screen.getByText(/负载身份或放行依据已变化/)).toBeVisible()
    expect(screen.getByRole('checkbox')).not.toBeChecked()
    expect(screen.getByRole('checkbox')).toBeDisabled()
    expect(screen.getByRole('button', { name: '确认实际中断负载' })).toBeDisabled()
    expect(api.post).not.toHaveBeenCalled()
  })
  it('dismisses the whole review when a different load ID is returned', () => {
    const rerender = show()
    fireEvent.change(screen.getByLabelText('现场操作原因'), {
      target: { value: 'Inert load replacement regression' },
    })
    fireEvent.click(screen.getByRole('button', { name: '复核实际负载操作' }))
    fireEvent.click(screen.getByRole('checkbox'))
    query.data = { ...query.data!, load: { ...query.data!.load, id: 'another-inert-load' } }
    rerender()
    expect(screen.queryByRole('dialog', { name: '确认本次实际负载操作' })).toBeNull()
    expect(screen.getByLabelText('现场操作原因')).toHaveValue('')
    expect(api.post).not.toHaveBeenCalled()
  })
  it.each(['release', 'revision'])('discards the review when its %s changes', (field) => {
    const rerender = show()
    fireEvent.change(screen.getByLabelText('现场操作原因'), {
      target: { value: 'Inert review-version regression' },
    })
    fireEvent.click(screen.getByRole('button', { name: '复核实际负载操作' }))
    fireEvent.click(screen.getByRole('checkbox'))
    query.data =
      field === 'release'
        ? { ...query.data!, release: { ...query.data!.release!, id: 'different-inert-release' } }
        : { ...query.data!, profile_revision: 8 }
    rerender()
    expect(screen.queryByRole('dialog', { name: '确认本次实际负载操作' })).toBeNull()
    expect(screen.getByLabelText('现场操作原因')).toHaveValue('')
    expect(api.post).not.toHaveBeenCalled()
  })
})
