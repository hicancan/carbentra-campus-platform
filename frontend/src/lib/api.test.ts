import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError, permissions, queryString, request, setCsrfToken } from './api'
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  setCsrfToken('')
})
describe('API transport', () => {
  it('includes cookie credentials and anti-CSRF header on mutations', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ data: { id: 'ok' } }), { status: 200 }))
    vi.stubGlobal('fetch', fetch)
    setCsrfToken('csrf-test')
    expect(await api.post('/commands', { action: 'hold' }, 'same-attempt')).toEqual({ id: 'ok' })
    const [url, options] = fetch.mock.calls[0]
    expect(url).toBe('/api/v1/commands')
    expect(options.credentials).toBe('include')
    expect(options.headers.get('X-CSRF-Token')).toBe('csrf-test')
    expect(options.headers.get('Idempotency-Key')).toBe('same-attempt')
    expect(options.body).toBe('{"action":"hold"}')
  })
  it('never turns a rejected mutation into success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: 'physical_control_disabled',
              message: 'Physical control disabled',
              request_id: 'request-7',
            },
          }),
          { status: 409 },
        ),
      ),
    )
    await expect(api.post('/commands', {})).rejects.toMatchObject({
      status: 409,
      code: 'physical_control_disabled',
      requestId: 'request-7',
      message: 'Physical control disabled',
    })
  })
  it('surfaces network and non-JSON proxy errors', async () => {
    const fetch = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('network down'))
      .mockResolvedValueOnce(new Response('Bad gateway', { status: 502 }))
    vi.stubGlobal('fetch', fetch)
    await expect(api.get('/overview')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 })
    await expect(api.get('/overview')).rejects.toMatchObject({ status: 502 })
  })
  it('rejects malformed success envelopes instead of rendering mock values', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"ok":true}', { status: 200 })))
    await expect(request('/overview')).rejects.toBeInstanceOf(ApiError)
    await expect(request('/overview')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })
  it('does not convert an aborted old navigation into a network error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new DOMException('Navigation replaced', 'AbortError')),
    )
    await expect(api.get('/devices')).rejects.toMatchObject({ name: 'AbortError' })
  })
  it('announces expired authenticated sessions', async () => {
    const expired = vi.fn()
    window.addEventListener('carbentra:session-expired', expired)
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"error":{"message":"Session expired"}}', { status: 401 }),
        ),
    )
    await expect(api.get('/devices')).rejects.toMatchObject({ status: 401 })
    expect(expired).toHaveBeenCalledTimes(1)
    window.removeEventListener('carbentra:session-expired', expired)
  })
  it('encodes stable IDs and preserves zero while removing absent filters', () => {
    expect(
      queryString({
        q: '教4 & A',
        offset: 0,
        enabled: false,
        nil: null,
        unset: undefined,
        empty: '',
      }),
    ).toBe('?q=%E6%95%994+%26+A&offset=0&enabled=false')
  })
})
describe('role capabilities', () => {
  it.each(['admin', 'operator'] as const)('allows %s to operate', (role) =>
    expect(permissions.operate(role)).toBe(true),
  )
  it.each(['viewer', 'analyst'] as const)('blocks %s from actuation', (role) =>
    expect(permissions.operate(role)).toBe(false),
  )
  it('separates operator and analyst responsibilities', () => {
    expect(permissions.analyze('analyst')).toBe(true)
    expect(permissions.analyze('operator')).toBe(false)
    expect(permissions.administer('operator')).toBe(false)
    expect(permissions.administer('admin')).toBe(true)
    expect(permissions.operate(undefined)).toBe(false)
  })
})
