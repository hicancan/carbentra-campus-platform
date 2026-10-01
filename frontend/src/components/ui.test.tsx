import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { Drawer, ErrorState, Metric, StatusBadge } from './ui'
import { formatNumber, statusLabel } from '../lib/format'
import { ApiError } from '../lib/api'
import { spatialUrl } from '../lib/spatial'
describe('readable and accessible state components', () => {
  it('does not format null, NaN or infinity as zero', () => {
    expect(formatNumber(null)).toBe('—')
    expect(formatNumber(undefined)).toBe('—')
    expect(formatNumber(NaN)).toBe('—')
    expect(formatNumber(Infinity)).toBe('—')
    expect(formatNumber(0)).toBe('0')
  })
  it('unknown occupancy stays unknown', () => {
    expect(statusLabel('unknown')).toBe('未知')
    render(<StatusBadge value="unknown" />)
    expect(screen.getByText('未知')).toBeVisible()
    expect(screen.queryByText('无人')).toBeNull()
  })
  it('renders unavailable metric with explicit missing-value marker', () => {
    render(<Metric label="真实功率" value={null} unit="W" icon={<span />} />)
    expect(screen.getByText('—')).toBeVisible()
  })
  it('exposes actionable API failures', () => {
    const retry = vi.fn()
    render(<ErrorState error={new Error('Permission denied')} retry={retry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Permission denied')
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    expect(retry).toHaveBeenCalledOnce()
  })
  it('closes a dialog with Escape and restores body scrolling after unmount', () => {
    const onClose = vi.fn()
    const { unmount } = render(
      <Drawer title="设备详情" onClose={onClose}>
        <button>操作</button>
      </Drawer>,
    )
    expect(screen.getByRole('dialog')).toHaveAccessibleName('设备详情')
    expect(document.body.style.overflow).toBe('hidden')
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
    unmount()
    expect(document.body.style.overflow).not.toBe('hidden')
  })
  it('keeps spatial asset paths on the authenticated local mount', () => {
    expect(spatialUrl('map/campus-lod1.glb')).toBe('/assets/spatial/map/campus-lod1.glb')
    expect(() => spatialUrl('https://untrusted.test/model.glb')).toThrow()
    expect(() => spatialUrl('../secret')).toThrow()
    expect(() => spatialUrl('/other/model')).toThrow()
    expect(() => spatialUrl('/assets/spatial/../secret')).toThrow()
    expect(() => spatialUrl('%2e%2e/secret')).toThrow()
    expect(() => spatialUrl('map\\secret')).toThrow()
  })
})

describe('nested confirmation dialogs', () => {
  it('dismisses only the top dialog on Escape', () => {
    const outer = vi.fn(),
      inner = vi.fn()
    render(
      <Drawer title="设备详情" onClose={outer}>
        <Drawer title="实际负载确认" onClose={inner}>
          <button>确认</button>
        </Drawer>
      </Drawer>,
    )
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(inner).toHaveBeenCalledOnce()
    expect(outer).not.toHaveBeenCalled()
  })
  it('shows sanitized validation fields without reflecting submitted secret values', () => {
    render(
      <ErrorState
        error={
          new ApiError('Request validation failed', 422, 'validation_error', 'test-id', [
            {
              location: ['body', 'password'],
              message: 'At least 16 characters are required',
              input: 'do-not-reflect-this-value',
            },
          ])
        }
      />,
    )
    expect(screen.getByText('body.password: At least 16 characters are required')).toBeVisible()
    expect(screen.queryByText('do-not-reflect-this-value')).toBeNull()
  })
})
