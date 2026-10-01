import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import Accounting from './Accounting'
const user = vi.hoisted(() => ({ role: 'admin', campus_ids: [] as string[] | null }))
vi.mock('../lib/auth', () => ({ useAuth: () => ({ session: { user } }) }))
vi.mock('../lib/hooks', () => ({
  useResource: () => ({ data: undefined, isLoading: false, error: null }),
}))
beforeEach(() => {
  user.campus_ids = []
})
describe('accounting write visibility', () => {
  it('keeps factor and tariff registration read-only for a scoped admin', () => {
    user.campus_ids = ['campus-1']
    render(<Accounting />)
    expect(screen.queryByRole('button', { name: '登记版本' })).not.toBeInTheDocument()
  })
  it('offers factor registration to an explicitly global admin', () => {
    user.campus_ids = null
    render(<Accounting />)
    expect(screen.getByRole('button', { name: '登记版本' })).toBeVisible()
  })
})
