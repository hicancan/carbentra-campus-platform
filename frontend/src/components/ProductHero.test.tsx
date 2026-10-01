import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import ProductHero from './ProductHero'
const state = vi.hoisted(() => ({
  family: 'SWITCH',
  path: '',
  hero: '/api/v1/assets/product/hero?family=SWITCH',
}))
vi.mock('../lib/hooks', () => ({
  useResource: (path: string) => {
    state.path = path
    return {
      data: { family: state.family, hero_url: state.hero, hero_sha256: 'a'.repeat(64) },
      isLoading: false,
    }
  },
}))
beforeEach(() => {
  state.family = 'SWITCH'
  state.hero = '/api/v1/assets/product/hero?family=SWITCH'
})
describe('lightweight family-specific engineering heroes', () => {
  it('uses exact family endpoint and digest without loading a 3D canvas', () => {
    render(<ProductHero family="SWITCH" fallback={<span>Icon fallback</span>} />)
    expect(state.path).toBe('/assets/product/manifest?family=SWITCH')
    const img = screen.getByRole('img', { name: /CARBENTRA Switch 工程参考图/ })
    expect(img.getAttribute('src')).toContain('family=SWITCH')
    expect(img.getAttribute('src')).toContain(`sha256=${'a'.repeat(64)}`)
    expect(document.querySelector('canvas')).toBeNull()
    expect(screen.getByText('工程参考 · 非现场照片')).toBeVisible()
  })
  it('does not substitute a Plug manifest for Sense', () => {
    state.family = 'PLUG'
    state.hero = '/api/v1/assets/product/hero?family=PLUG'
    render(<ProductHero family="PRESENCE" fallback={<span>Sense icon</span>} />)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByText('Sense icon')).toBeVisible()
  })
  it('optional image failure falls back without breaking device controls', () => {
    render(<ProductHero family="SWITCH" fallback={<span>Switch icon</span>} />)
    fireEvent.error(screen.getByRole('img'))
    expect(screen.getByText('Switch icon')).toBeVisible()
    expect(screen.queryByRole('img')).toBeNull()
  })
  it('rejects an external image even when the manifest names the right family', () => {
    state.hero = 'https://external.example/api/v1/assets/product/hero?family=SWITCH'
    render(<ProductHero family="SWITCH" fallback={<span>Switch icon</span>} />)
    expect(screen.queryByRole('img')).toBeNull()
  })
})
