import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider, focusManager } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useLiveEvents, useResource } from './hooks'
class FakeEvents {
  static latest: FakeEvents
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  handlers = new Map<string, (event: MessageEvent) => void>()
  constructor() {
    FakeEvents.latest = this
  }
  addEventListener(name: string, handler: (event: MessageEvent) => void) {
    this.handlers.set(name, handler)
  }
  close() {}
}
afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
  focusManager.setFocused(undefined)
})
describe('live refresh under a slow API', () => {
  it('does not abort and restart an active background read on a telemetry event', async () => {
    vi.stubGlobal('EventSource', FakeEvents)
    const fetch = vi.fn((_url: string, _options: RequestInit) => new Promise<Response>(() => {}))
    vi.stubGlobal('fetch', fetch)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['resource', '/overview'], { version: 'previous' })
    const view = renderHook(
      () => {
        useResource('/overview')
        return useLiveEvents()
      },
      {
        wrapper: ({ children }: { children: ReactNode }) => (
          <QueryClientProvider client={client}>{children}</QueryClientProvider>
        ),
      },
    )
    await waitFor(() => expect(fetch).toHaveBeenCalledOnce())
    const signal = fetch.mock.calls[0][1].signal!
    act(() =>
      FakeEvents.latest.handlers.get('change')!({
        data: JSON.stringify({ type: 'telemetry.updated' }),
      } as MessageEvent),
    )
    expect(fetch).toHaveBeenCalledOnce()
    expect(signal.aborted).toBe(false)
    view.unmount()
    client.clear()
  })
  it('coalesces polling and focus refresh while the same GET is still in flight', async () => {
    vi.useFakeTimers()
    const fetch = vi.fn((_url: string, _options: RequestInit) => new Promise<Response>(() => {}))
    vi.stubGlobal('fetch', fetch)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    client.setQueryData(['resource', '/overview'], { version: 'previous' })
    const view = renderHook(() => useResource('/overview'), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      ),
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
    })
    expect(fetch).toHaveBeenCalledOnce()
    const signal = fetch.mock.calls[0][1].signal!
    await act(async () => {
      await vi.advanceTimersByTimeAsync(61000)
    })
    act(() => {
      focusManager.setFocused(false)
      focusManager.setFocused(true)
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(fetch).toHaveBeenCalledOnce()
    expect(signal.aborted).toBe(false)
    view.unmount()
    client.clear()
  })
})
