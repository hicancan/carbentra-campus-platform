import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BuildingFilter } from './Filters'
const result = vi.hoisted(() => ({
  data: [{ id: 'building-new', name: '当前校区楼栋' }] as
    | { id: string; name: string }[]
    | undefined,
  isLoading: false,
  error: null as Error | null,
}))
vi.mock('../lib/hooks', () => ({ useResource: () => result }))
beforeEach(() => {
  result.data = [{ id: 'building-new', name: '当前校区楼栋' }]
  result.isLoading = false
  result.error = null
})
describe('campus scope switch', () => {
  it('clears a building that does not belong to the loaded scope', () => {
    const onChange = vi.fn()
    render(<BuildingFilter value="building-old-campus" onChange={onChange} />)
    expect(onChange).toHaveBeenCalledWith('')
  })
  it('keeps an existing building selection', () => {
    const onChange = vi.fn()
    render(<BuildingFilter value="building-new" onChange={onChange} />)
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByLabelText('筛选楼栋')).toHaveValue('building-new')
  })
  it('does not clear a selection while its directory is still loading', () => {
    result.data = undefined
    result.isLoading = true
    const onChange = vi.fn()
    render(<BuildingFilter value="building-new" onChange={onChange} />)
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByLabelText('筛选楼栋')).toBeDisabled()
  })
})
