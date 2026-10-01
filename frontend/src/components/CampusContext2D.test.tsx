import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import CampusContext2D, { contextGeometryPath } from './CampusContext2D'
import type { SpatialContextFeature } from '../lib/spatial'
const project = (point: number[]) => `${point[0]},${-point[1]}`
const polygon: SpatialContextFeature = {
  type: 'Feature',
  properties: { asset_id: 'source-green', context_layer: 'greens' },
  geometry: {
    type: 'Polygon',
    coordinates: [
      [
        [0, 0],
        [10, 0],
        [10, 10],
        [0, 0],
      ],
      [
        [2, 2],
        [3, 2],
        [3, 3],
        [2, 2],
      ],
    ],
  },
}
describe('source-derived context geometry', () => {
  it('preserves polygon holes and flips north only for SVG projection', () => {
    expect(contextGeometryPath(polygon, project)).toBe(
      'M0,0 L10,0 L10,-10 L0,0Z M2,-2 L3,-2 L3,-3 L2,-2Z',
    )
  })
  it('renders roads as open alignments rather than polygons', () => {
    const road: SpatialContextFeature = {
      ...polygon,
      properties: { asset_id: 'road-1', context_layer: 'roads', width: 5.5 },
      geometry: {
        type: 'LineString',
        coordinates: [
          [0, 0],
          [5, 4],
          [8, 9],
        ],
      },
    }
    expect(contextGeometryPath(road, project)).toBe('M0,0 L5,-4 L8,-9')
  })
  it('never exposes context features as selectable registry buildings', () => {
    render(
      <svg>
        <CampusContext2D
          data={{ type: 'FeatureCollection', features: [polygon] }}
          project={project}
          scale={1}
        />
      </svg>,
    )
    expect(screen.queryAllByRole('button')).toHaveLength(0)
    expect(document.querySelector('[data-context-layer="greens"]')).toHaveAttribute(
      'fill-rule',
      'evenodd',
    )
    expect(document.querySelector('.map-context')).toHaveAttribute('pointer-events', 'none')
  })
})
