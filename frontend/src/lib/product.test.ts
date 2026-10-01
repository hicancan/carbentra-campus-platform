import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  loadVerifiedProduct,
  trustedProductUrl,
  trustedProductHeroUrl,
  deviceProductFamily,
} from './product'
import type { ProductManifest } from './product'
const manifest = {
  bytes: 20,
  display_sha256: '0'.repeat(64),
  model_url: '/api/v1/assets/product/model',
} as ProductManifest
beforeEach(() => {
  vi.stubGlobal('crypto', {
    subtle: { digest: vi.fn().mockResolvedValue(new Uint8Array(32).buffer) },
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
})
describe('explicit, integrity-checked product resources', () => {
  it('permits only the authorized same-origin binary endpoint', () => {
    expect(trustedProductUrl('/api/v1/assets/product/model', 'https://campus.example')).toBe(
      'https://campus.example/api/v1/assets/product/model',
    )
    expect(() =>
      trustedProductUrl('https://other.example/model', 'https://campus.example'),
    ).toThrow()
    expect(() => trustedProductUrl('/assets/anything', 'https://campus.example')).toThrow()
  })
  it('keeps exact product families distinct and does not guess unknown hardware', () => {
    expect(deviceProductFamily({ kind: 'presence' })).toBe('PRESENCE')
    expect(deviceProductFamily({ kind: 'switch' })).toBe('SWITCH')
    expect(deviceProductFamily({ kind: 'smart_plug' })).toBe('PLUG')
    expect(deviceProductFamily({ kind: 'sensor' })).toBeNull()
    expect(() =>
      trustedProductHeroUrl('/api/v1/assets/product/hero?family=PLUG', 'SWITCH'),
    ).toThrow()
  })
  it('rejects a model URL whose family does not match the pinned manifest', async () => {
    await expect(
      loadVerifiedProduct(
        { ...manifest, family: 'SWITCH', model_url: '/api/v1/assets/product/model?family=PLUG' },
        new AbortController().signal,
        vi.fn(),
      ),
    ).rejects.toThrow('类型不一致')
  })
  it('requires a bounded positive size and SHA-256 before downloading', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    await expect(
      loadVerifiedProduct(
        { ...manifest, bytes: 100_000_000 },
        new AbortController().signal,
        vi.fn(),
      ),
    ).rejects.toThrow('清单')
    await expect(
      loadVerifiedProduct(
        { ...manifest, display_sha256: '' },
        new AbortController().signal,
        vi.fn(),
      ),
    ).rejects.toThrow('清单')
    expect(fetch).not.toHaveBeenCalled()
  })
  it('does not parse or display a binary with mismatched bytes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new Uint8Array(21))))
    await expect(
      loadVerifiedProduct(manifest, new AbortController().signal, vi.fn()),
    ).rejects.toThrow('超过清单')
  })
  it('rejects a checksum mismatch', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new Uint8Array(20))))
    vi.stubGlobal('crypto', {
      subtle: { digest: vi.fn().mockResolvedValue(new Uint8Array(32).fill(1).buffer) },
    })
    await expect(
      loadVerifiedProduct(manifest, new AbortController().signal, vi.fn()),
    ).rejects.toThrow('SHA-256 校验失败')
  })
  it('returns only verified bytes with credentialed transport', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(new Uint8Array(20)))
    vi.stubGlobal('fetch', fetch)
    vi.stubGlobal('crypto', {
      subtle: { digest: vi.fn().mockResolvedValue(new Uint8Array(32).buffer) },
    })
    const progress = vi.fn()
    expect(
      (await loadVerifiedProduct(manifest, new AbortController().signal, progress)).byteLength,
    ).toBe(20)
    expect(fetch.mock.calls[0][1].credentials).toBe('include')
    const url = new URL(fetch.mock.calls[0][0])
    expect(url.pathname).toBe('/api/v1/assets/product/model')
    expect(url.searchParams.get('sha256')).toBe(manifest.display_sha256)
    expect(progress).toHaveBeenLastCalledWith(1)
  })
})
