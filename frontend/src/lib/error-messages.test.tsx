import { describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ApiError } from './api'
import { apiErrorMessage } from './error-messages'
import { ErrorState } from '../components/ui'
describe('clear operational errors with retained technical evidence', () => {
  it('localizes common codes without changing the transport error', () => {
    const error = new ApiError(
      'Invalid username or password',
      401,
      'invalid_credentials',
      'request-42',
    )
    render(<ErrorState error={error} />)
    expect(screen.getByRole('alert')).toHaveTextContent('账户或密码不正确')
    expect(screen.getByText('请求编号：request-42')).toBeVisible()
    expect(error.message).toBe('Invalid username or password')
    expect(screen.getByText('Invalid username or password')).not.toBeVisible()
    fireEvent.click(screen.getByText('技术详情'))
    expect(screen.getByText('Invalid username or password')).toBeVisible()
    expect(screen.getByText('invalid_credentials')).toBeVisible()
  })
  it('keeps an unmapped technical error and explains proxy timeouts', () => {
    expect(apiErrorMessage('domain_specific', 409, 'Specific retained reason')).toBe(
      'Specific retained reason',
    )
    expect(apiErrorMessage('REQUEST_FAILED', 504, 'HTTP504')).toBe('服务响应超时，请稍后重试')
    expect(apiErrorMessage('constructor', 409, 'Unmapped server reason')).toBe(
      'Unmapped server reason',
    )
    expect(apiErrorMessage('physical_review_stale', 409, 'Old review')).toContain('重新读取资格')
  })
})
