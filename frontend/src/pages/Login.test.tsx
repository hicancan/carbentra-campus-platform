import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider, focusManager } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '../lib/auth'
import { setCsrfToken } from '../lib/api'
import Login from './Login'
function Shell() {
  const auth = useAuth()
  return auth.loading ? (
    <p>Checking session</p>
  ) : auth.session ? (
    <p>Authenticated as {auth.session.user.username}</p>
  ) : (
    <Login />
  )
}
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  focusManager.setFocused(undefined)
  setCsrfToken('')
})
describe('login persistence and recovery', () => {
  it('preserves the error and entered account through delayed auth refresh and stops anonymous polling', async () => {
    vi.useFakeTimers()
    let meCalls = 0
    const fetch = vi.fn(async (url: string) => {
      if (url.endsWith('/auth/me') && ++meCalls > 1)
        await new Promise((resolve) => setTimeout(resolve, 1000))
      return new Response(
        JSON.stringify({
          error: {
            code: url.endsWith('/auth/login') ? 'invalid_credentials' : 'unauthenticated',
            message: url.endsWith('/auth/login')
              ? 'Invalid username or password'
              : 'Login required',
          },
        }),
        { status: 401, headers: { 'content-type': 'application/json' } },
      )
    })
    vi.stubGlobal('fetch', fetch)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Shell />
        </AuthProvider>
      </QueryClientProvider>,
    )
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30)
    })
    fireEvent.change(screen.getByLabelText('账户'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong-fixture-password' } })
    fireEvent.click(screen.getByRole('button', { name: '进入平台' }))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30)
    })
    expect(screen.getByRole('alert')).toHaveTextContent('账户或密码不正确')
    await act(async () => {
      await vi.advanceTimersByTimeAsync(61_000)
    })
    expect(meCalls).toBe(1)
    expect(screen.getByLabelText('账户')).toHaveValue('admin')
    await act(async () => {
      focusManager.setFocused(false)
      focusManager.setFocused(true)
      await vi.advanceTimersByTimeAsync(30)
    })
    expect(meCalls).toBe(1)
    act(() => {
      void client.invalidateQueries({ queryKey: ['session'] })
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30)
    })
    expect(screen.getByLabelText('账户')).toHaveValue('admin')
    expect(screen.queryByText('Checking session')).toBeNull()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1100)
    })
    expect(screen.getByRole('alert')).toHaveTextContent('账户或密码不正确')
    expect(screen.getByLabelText('账户')).toHaveValue('admin')
    client.clear()
  })
  it('recovers from a wrong password to a successful login', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, options?: RequestInit) => {
        const body = options?.body ? JSON.parse(String(options.body)) : null
        if (url.endsWith('/auth/login') && body?.password === 'valid-inert-fixture')
          return new Response(
            JSON.stringify({
              data: {
                user: {
                  id: 'test-user',
                  username: 'admin',
                  display_name: 'Test Admin',
                  role: 'admin',
                  campus_ids: null,
                },
                csrf_token: 'inert-csrf',
                expires_at: new Date(Date.now() + 3600000).toISOString(),
              },
            }),
            { status: 200 },
          )
        return new Response(
          JSON.stringify({
            error: { code: 'unauthorized', message: 'Invalid username or password' },
          }),
          { status: 401 },
        )
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Shell />
        </AuthProvider>
      </QueryClientProvider>,
    )
    await screen.findByLabelText('账户')
    fireEvent.change(screen.getByLabelText('账户'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong-inert-fixture' } })
    fireEvent.click(screen.getByRole('button', { name: '进入平台' }))
    await screen.findByRole('alert')
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'valid-inert-fixture' } })
    fireEvent.click(screen.getByRole('button', { name: '进入平台' }))
    await waitFor(() => expect(screen.getByText('Authenticated as admin')).toBeVisible())
    expect(screen.queryByRole('alert')).toBeNull()
    client.clear()
  })
})
