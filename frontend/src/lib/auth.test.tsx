import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './auth'
import { setCsrfToken } from './api'
const session = {
  user: { id: 'u-1', username: 'analyst', display_name: 'Analyst User', role: 'analyst' },
  csrf_token: 'csrf-session',
  expires_at: '2026-10-01T10:00:00Z',
}
function Probe() {
  const auth = useAuth()
  return (
    <div>
      {auth.loading ? 'loading' : auth.session?.user.username || 'signed out'}
      <button
        onClick={() => {
          void auth.login('analyst', 'not-a-real-password')
        }}
      >
        Login
      </button>
      <button onClick={auth.refresh}>Refresh</button>
      <button
        onClick={() => {
          void auth.logout()
        }}
      >
        Logout
      </button>
    </div>
  )
}
afterEach(() => {
  vi.unstubAllGlobals()
  setCsrfToken('')
})
describe('session lifecycle without stale identity', () => {
  it('updates the active observer on login and clears private caches on logout', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/auth/login'))
          return new Response(JSON.stringify({ data: session }), { status: 200 })
        if (url.endsWith('/auth/logout'))
          return new Response('{"data":{"logged_out":true}}', { status: 200 })
        return new Response('{"error":{"code":"unauthorized","message":"Login required"}}', {
          status: 401,
        })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </QueryClientProvider>,
    )
    await screen.findByText('signed out')
    client.setQueryData(['resource', '/devices'], [{ id: 'old-private-record' }])
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    await screen.findByText('analyst')
    expect(client.getQueryData(['resource', '/devices'])).toBeUndefined()
    client.setQueryData(['resource', '/overview'], { private: true })
    fireEvent.click(screen.getByRole('button', { name: 'Logout' }))
    await screen.findByText('signed out')
    expect(client.getQueryData(['resource', '/overview'])).toBeUndefined()
    expect(client.getQueryData(['session'])).toBeNull()
  })
  it('immediately drops session data after authenticated expiry notification', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{"error":{"message":"Expired"}}', { status: 401 })),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['session'], session)
    client.setQueryData(['resource', '/devices'], [{ id: 'private-record' }])
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </QueryClientProvider>,
    )
    expect(screen.getByText('analyst')).toBeVisible()
    fireEvent(window, new Event('carbentra:session-expired'))
    await waitFor(() => expect(screen.getByText('signed out')).toBeVisible())
    expect(client.getQueryData(['resource', '/devices'])).toBeUndefined()
  })
  it('also clears cached private state when the periodic auth check is unauthorized', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{"error":{"message":"Expired"}}', { status: 401 })),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['session'], session)
    client.setQueryData(['resource', '/overview'], { private: true })
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </QueryClientProvider>,
    )
    expect(screen.getByText('analyst')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    await screen.findByText('signed out')
    await waitFor(() => expect(client.getQueryData(['resource', '/overview'])).toBeUndefined())
    expect(client.getQueryData(['session'])).toBeNull()
  })
  it('does not let a late anonymous refresh erase a newer successful login', async () => {
    let settleRefresh: ((response: Response) => void) | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.endsWith('/auth/login'))
          return Promise.resolve(new Response(JSON.stringify({ data: session }), { status: 200 }))
        return new Promise<Response>((resolve) => {
          settleRefresh = resolve
        })
      }),
    )
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['session'], null)
    render(
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </QueryClientProvider>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(settleRefresh).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
    await screen.findByText('analyst')
    await act(async () => {
      settleRefresh!(
        new Response('{"error":{"message":"Old anonymous response"}}', { status: 401 }),
      )
      await new Promise((resolve) => setTimeout(resolve, 20))
    })
    expect(screen.getByText('analyst')).toBeVisible()
    expect(client.getQueryData(['session'])).toEqual(session)
    client.clear()
  })
})
