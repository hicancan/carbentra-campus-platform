import { describe, expect, it } from 'vitest'
import { spatialUrl } from './spatial'
describe('pinned spatial cache identity', () => {
  it('adds only an encoded manifest version to an accepted same-origin path', () => {
    expect(spatialUrl('map/building.glb', 'revision:a&b')).toBe(
      '/assets/spatial/map/building.glb?v=revision%3Aa%26b',
    )
    expect(spatialUrl('map/building.glb', 'revision-2')).not.toBe(
      spatialUrl('map/building.glb', 'revision-1'),
    )
  })
  it.each([
    'https://outside.example/model',
    '../model.glb',
    'map/%2e%2e/model.glb',
    'map/model.glb?remote=1',
  ])('keeps rejecting untrusted artifact path %s', (path) => {
    expect(() => spatialUrl(path, 'revision-1')).toThrow('不受信任')
  })
})
