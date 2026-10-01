import { describe, expect, it, vi } from 'vitest'
import { readTheme, writeTheme } from './preferences'
describe('privacy-friendly theme preferences', () => {
  it('keeps the application available with blocked browser storage', () => {
    expect(
      readTheme({
        getItem: () => {
          throw new Error('Storage disabled')
        },
      }),
    ).toBe('light')
    expect(
      writeTheme('dark', {
        setItem: () => {
          throw new Error('Storage disabled')
        },
      }),
    ).toBe(false)
  })
  it('accepts only known themes', () => {
    expect(readTheme({ getItem: () => 'dark' })).toBe('dark')
    expect(readTheme({ getItem: () => 'not-a-theme' })).toBe('light')
  })
  it('writes only the non-sensitive display preference', () => {
    const setItem = vi.fn()
    expect(writeTheme('dark', { setItem })).toBe(true)
    expect(setItem).toHaveBeenCalledWith('carbentra-theme', 'dark')
  })
})
