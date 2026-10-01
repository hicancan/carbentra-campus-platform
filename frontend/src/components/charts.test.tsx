import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { chartSegments, chartXCoordinates, LineChart } from './charts'
const point = (value: number | null) => ({ timestamp: '2026-09-30T10:00:00Z', value })
describe('truth-preserving chart geometry', () => {
  it('positions irregular observation intervals on the actual time axis', () => {
    const points = [
      { timestamp: '2026-09-30T10:00:00Z', value: 1 },
      { timestamp: '2026-09-30T10:01:00Z', value: 2 },
      { timestamp: '2026-09-30T10:10:00Z', value: 3 },
    ]
    expect(chartXCoordinates(points, 100)).toEqual([0, 10, 100])
  })
  it('breaks lines at missing readings', () => {
    expect(chartSegments([point(5), point(null), point(8)], 100, 100, 10)).toEqual([
      'M0.00,50.00',
      'M100.00,20.00',
    ])
  })
  it('does not reinterpret unknown as zero', () => {
    expect(chartSegments([point(null), point(null)], 100, 100, 10)).toEqual([])
    render(<LineChart points={[point(null)]} />)
    expect(screen.getByText('暂无可绘制的有效数据')).toBeVisible()
  })
  it('supports signed export measurements and mixed values', () => {
    expect(chartSegments([point(-10), point(0), point(10)], 100, 100, 10, -10)).toEqual([
      'M0.00,100.00 L50.00,50.00 L100.00,0.00',
    ])
  })
  it('renders a single zero sample as a real observation', () => {
    expect(chartSegments([point(0)], 100, 100, 1)).toEqual(['M50.00,100.00'])
    render(<LineChart points={[point(0)]} />)
    expect(screen.getByRole('img')).toHaveAccessibleName(/共 1 个时间点/)
    expect(document.querySelectorAll('circle').length).toBeGreaterThan(0)
  })
  it('skips non-finite observations', () => {
    expect(chartSegments([point(Number.NaN), point(2), point(Infinity)], 100, 100, 10)).toEqual([
      'M50.00,80.00',
    ])
  })
  it('keeps negative-only series within the plot and displays a signed axis', () => {
    render(<LineChart points={[point(-20), point(-5)]} />)
    const paths = [...document.querySelectorAll('path')].map((p) => p.getAttribute('d'))
    expect(paths.every((p) => !p?.includes('NaN'))).toBe(true)
    expect(document.querySelector('svg')?.textContent).toMatch(/-/)
  })
})
