import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import CampusMap2D from './CampusMap2D'
import type { SpatialGeoJSON } from '../lib/spatial'
const map: SpatialGeoJSON = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: {
        building_id: 'building:source:a',
        asset_id: 'a',
        name: '源建筑 A',
        height_m: 10,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 0],
          ],
        ],
      },
    },
  ],
}
describe('source building map integrity', () => {
  it('picks the exact semantic ID with the keyboard and keeps attribution visible', () => {
    const select = vi.fn()
    render(<CampusMap2D data={map} allowedIds={new Set(['building:source:a'])} onSelect={select} />)
    fireEvent.keyDown(screen.getByRole('button', { name: '选择楼栋 源建筑 A' }), { key: 'Enter' })
    expect(select).toHaveBeenCalledWith('building:source:a')
    expect(screen.getByRole('link', { name: 'OpenStreetMap contributors' })).toBeVisible()
  })
  it('does not draw non-finite or empty geometry', () => {
    const invalid: SpatialGeoJSON = {
      ...map,
      features: map.features.map((f) => ({
        ...f,
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [NaN, 2],
              [0, 0],
              [1, 1],
            ],
          ],
        },
      })),
    }
    render(
      <CampusMap2D data={invalid} allowedIds={new Set(['building:source:a'])} onSelect={vi.fn()} />,
    )
    expect(screen.getByText('该范围尚无已发布的室外几何')).toBeVisible()
    expect(document.querySelector('.map-svg')).toBeNull()
  })
})
