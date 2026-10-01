import { describe, expect, it } from 'vitest'
import { IDENTIFIER_PATTERN, USERNAME_PATTERN } from './input-patterns'
describe('HTML UnicodeSets input patterns', () => {
  it.each([IDENTIFIER_PATTERN, USERNAME_PATTERN])(
    'is a valid native v-mode regular expression: %s',
    (pattern) => {
      expect(() => new RegExp(pattern, 'v')).not.toThrow()
    },
  )
  it.each(['QA-UI-1', 'device:edge.1', 'a_b', 'osm_way_223859810'])(
    'retains canonical stable ID %s',
    (id) => {
      expect(new RegExp(`^(?:${IDENTIFIER_PATTERN})$`, 'v').test(id)).toBe(true)
    },
  )
  it.each(['.', '..', 'with space', 'a/b', 'a#b', '汉字'])(
    'rejects non-addressable or unsupported ID %s',
    (id) => {
      expect(new RegExp(`^(?:${IDENTIFIER_PATTERN})$`, 'v').test(id)).toBe(false)
    },
  )
  it('enforces the pattern in a native input rather than silently ignoring invalid syntax', () => {
    const input = document.createElement('input')
    input.pattern = IDENTIFIER_PATTERN
    input.value = 'with space'
    expect(input.validity.patternMismatch).toBe(true)
    input.value = 'QA-UI-1'
    expect(input.validity.patternMismatch).toBe(false)
  })
})
