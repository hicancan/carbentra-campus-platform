import { describe, expect, it } from 'vitest'
import { displayBuildingName, sortBuildings } from './registry-display'
describe('source-preserving building directory presentation', () => {
  it('sorts numeric names naturally without mutating names or canonical IDs', () => {
    const original = [
      { id: 'building:b10', name: '10' },
      { id: 'building:b2', name: '2' },
      { id: 'building:b1', name: '1' },
    ]
    const sorted = sortBuildings(original)
    expect(sorted.map((item) => item.name)).toEqual(['1', '2', '10'])
    expect(sorted.map((item) => item.id)).toEqual(['building:b1', 'building:b2', 'building:b10'])
    expect(original[0].name).toBe('10')
  })
  it('also sorts embedded numbers naturally and labels bare numeric source marks honestly', () => {
    expect(
      sortBuildings([
        { id: 'a', name: '教10' },
        { id: 'b', name: '教2' },
      ]).map((item) => item.name),
    ).toEqual(['教2', '教10'])
    expect(displayBuildingName('1')).toBe('建筑 1')
    expect(displayBuildingName('图书馆')).toBe('图书馆')
  })
})
