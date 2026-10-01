import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ClassroomDeviceCard from './ClassroomDeviceCard'
import { channelFixture } from '../test-fixtures/classroom'
vi.mock('../lib/hooks', () => ({ useResource: () => ({ isLoading: false, data: undefined }) }))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user: { role: 'operator' } } }) }))
function show(channels = [channelFixture()], historical = false) {
  render(
    <MemoryRouter>
      <ClassroomDeviceCard channels={channels} historical={historical} />
    </MemoryRouter>,
  )
}
describe('capability-driven classroom cards', () => {
  it('separates requested and feedback state and displays source', () => {
    show()
    expect(screen.getByText('请求状态')).toBeVisible()
    expect(screen.getByText('物理反馈')).toBeVisible()
    expect(screen.getByText('开启')).toBeVisible()
    expect(screen.getByText('关闭')).toBeVisible()
    expect(screen.getByText('SIMULATED')).toBeVisible()
    expect(screen.getByText('CARBENTRA Plug')).toBeVisible()
  })
  it('disables operation for historical snapshots', () => {
    show([channelFixture()], true)
    expect(screen.getByRole('button', { name: /操作 .*relay/ })).toBeDisabled()
  })
  it('explicitly labels missing feedback hardware rather than verifying requested state', () => {
    show([
      channelFixture({
        feedback_supported: false,
        value: { desired_on: true, output_present: null },
      }),
    ])
    expect(screen.getByText('无反馈能力')).toBeVisible()
    expect(screen.queryByText('已验证')).toBeNull()
  })
  it('never manufactures HVAC setpoints or dimmers on a presence sensor', () => {
    show([
      channelFixture({
        product_family: 'PRESENCE',
        kind: 'presence',
        controllable: false,
        allowed_actions: [],
        value: { occupancy: 'unknown' },
        capabilities: ['presence.radar'],
      }),
    ])
    expect(screen.getByText('CARBENTRA Sense')).toBeVisible()
    expect(screen.queryByRole('button', { name: /操作 .*relay/ })).toBeNull()
    expect(screen.queryByRole('slider')).toBeNull()
    expect(screen.queryByRole('spinbutton')).toBeNull()
  })
  it('offers independent relay1/2/3 targets instead of one device-wide operation', () => {
    const channels = [1, 2, 3].map((n) =>
      channelFixture({
        channel_id: `switch:test:relay.${n}`,
        channel_key: `relay.${n}`,
        device_id: 'switch:test',
        product_family: 'SWITCH',
        name: `照明第${n}路`,
        kind: 'lighting',
        feedback_supported: false,
        verification_kind: 'actuator_reported_only',
        value: { desired_on: true, actuator_reported_on: true, output_present: null },
      }),
    )
    show(channels)
    expect(screen.getAllByRole('button', { name: /操作 照明第/ })).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: '操作 照明第2路 relay.2' }))
    expect(
      screen.getByRole('dialog', { name: 'CARBENTRA Switch · relay.2 通道操作' }),
    ).toBeVisible()
    expect(screen.queryByRole('button', { name: /^操作$/ })).toBeNull()
  })
  it('opens actual observation provenance', () => {
    show()
    fireEvent.click(screen.getByRole('button', { name: '证据' }))
    expect(screen.getByText('test-v1')).toBeVisible()
    expect(screen.getByText('relay.commanded · relay.feedback')).toBeVisible()
  })
})
