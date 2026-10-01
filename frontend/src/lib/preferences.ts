export type Theme = 'light' | 'dark'
export function readTheme(storage?: Pick<Storage, 'getItem'>): Theme {
  try {
    return (storage || window.localStorage).getItem('carbentra-theme') === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}
export function writeTheme(theme: Theme, storage?: Pick<Storage, 'setItem'>): boolean {
  try {
    ;(storage || window.localStorage).setItem('carbentra-theme', theme)
    return true
  } catch {
    return false
  }
}
