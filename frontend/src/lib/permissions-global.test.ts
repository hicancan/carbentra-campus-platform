import { describe, expect, it } from 'vitest'
import { permissions } from './api'
describe('global configuration boundary', () => {
  it('permits only explicitly global administrators', () => {
    expect(permissions.configureGlobal({ role: 'admin', campus_ids: null })).toBe(true)
  })
  it('rejects bounded and zero-campus administrators', () => {
    expect(permissions.configureGlobal({ role: 'admin', campus_ids: ['campus-1'] })).toBe(false)
    expect(permissions.configureGlobal({ role: 'admin', campus_ids: [] })).toBe(false)
  })
  it('rejects other roles and missing session scope', () => {
    expect(permissions.configureGlobal({ role: 'operator', campus_ids: null })).toBe(false)
    expect(permissions.configureGlobal()).toBe(false)
  })
})
