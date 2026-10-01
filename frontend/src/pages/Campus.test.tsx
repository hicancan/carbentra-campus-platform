import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { FloorMap } from './Campus'
const query = vi.hoisted(() => ({
  data: {
    space_units: [
      {
        id: 'unit1',
        space_id: 'space1',
        name: '教4-601',
        geometry_status: 'schematic',
        polygon: [
          [0.1, 0.1],
          [0.2, 0.1],
          [0.2, 0.3],
          [0.1, 0.1],
        ],
        label_point: [0.15, 0.2],
      },
    ],
    view_box: [1000, 600],
  },
  isLoading: false,
  error: null,
}))
vi.mock('../lib/spatial', async (original) => ({
  ...(await original<typeof import('../lib/spatial')>()),
  useSpatial: () => query,
}))
beforeEach(() => {
  query.data.space_units = [
    {
      id: 'unit1',
      space_id: 'space1',
      name: '教4-601',
      geometry_status: 'schematic',
      polygon: [
        [0.1, 0.1],
        [0.2, 0.1],
        [0.2, 0.3],
        [0.1, 0.1],
      ],
      label_point: [0.15, 0.2],
    },
  ]
})
describe('independent indoor diagram navigation', () => {
  it('zooms the schematic and preserves exact semantic selection', () => {
    const select = vi.fn()
    render(<FloorMap path="floor-a.json" selected={null} onSelect={select} />)
    fireEvent.click(screen.getByRole('button', { name: '放大楼层图' }))
    expect(document.querySelector('.floor-map-content')?.getAttribute('transform')).toContain(
      'scale(1.35)',
    )
    fireEvent.keyDown(screen.getByRole('button', { name: '教4-601，占用未知' }), { key: 'Enter' })
    expect(select).toHaveBeenCalledWith('space1')
    fireEvent.click(screen.getByRole('button', { name: '重置楼层视角' }))
    expect(document.querySelector('.floor-map-content')?.getAttribute('transform')).toContain(
      'scale(1)',
    )
  })
  it('does not manufacture geometry or availability for an empty plan', () => {
    query.data.space_units = []
    render(<FloorMap path="empty.json" selected={null} onSelect={vi.fn()} />)
    expect(screen.getByText('该图面没有有效几何')).toBeVisible()
    expect(document.querySelector('svg[aria-label="楼层房间示意图"]')).toBeNull()
  })
})
