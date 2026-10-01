export type ProductFamily = 'PLUG' | 'SWITCH' | 'PRESENCE'
export function isProductFamily(value: string | null | undefined): value is ProductFamily {
  return value === 'PLUG' || value === 'SWITCH' || value === 'PRESENCE'
}
export function deviceProductFamily(device: { kind: string }): ProductFamily | null {
  return device.kind === 'smart_plug'
    ? 'PLUG'
    : ['switch', 'light'].includes(device.kind)
      ? 'SWITCH'
      : device.kind === 'presence'
        ? 'PRESENCE'
        : null
}
export function productFamilyName(family: ProductFamily) {
  return { PLUG: 'CARBENTRA Plug', SWITCH: 'CARBENTRA Switch', PRESENCE: 'CARBENTRA Sense' }[family]
}
export interface ProductPart {
  id: string
  name: string
  source_part?: string
  node_index?: number
  provenance?: { source?: string; development_status?: string; [key: string]: unknown }
  source?: string
  development_status?: string
  [key: string]: unknown
}
export interface ProductManifest {
  family?: ProductFamily
  product_name?: string
  hero_url?: string
  hero_sha256?: string
  version: string | number
  source_commit: string
  source_sha256: string
  display_sha256: string
  model_url: string
  bytes: number
  units: string
  node_count: number
  triangle_count: number
  parts: ProductPart[]
  optimized: boolean
  provenance?: Record<string, unknown> | string
  license?: string
  limitations?: string[]
}
export function trustedProductUrl(path: string, origin = window.location.origin) {
  const url = new URL(path, origin)
  if (
    url.origin !== origin ||
    url.pathname !== '/api/v1/assets/product/model' ||
    url.hash ||
    url.username ||
    url.password ||
    url.searchParams.getAll('family').length > 1
  )
    throw new Error('产品模型必须来自已授权的同源产物接口')
  return url.href
}
export function trustedProductHeroUrl(
  path: string,
  family: ProductFamily,
  origin = window.location.origin,
) {
  const url = new URL(path, origin)
  if (
    url.origin !== origin ||
    url.pathname !== '/api/v1/assets/product/hero' ||
    url.hash ||
    url.username ||
    url.password ||
    url.searchParams.get('family') !== family ||
    url.searchParams.getAll('family').length !== 1
  )
    throw new Error('产品参考图必须来自匹配产品类型的已授权同源接口')
  return url.href
}
export function manifestMatchesFamily(manifest: ProductManifest, family: ProductFamily) {
  return manifest.family === family || (!manifest.family && family === 'PLUG')
}
export async function loadVerifiedProduct(
  manifest: ProductManifest,
  signal: AbortSignal,
  progress: (ratio: number) => void,
): Promise<ArrayBuffer> {
  if (
    !Number.isSafeInteger(manifest.bytes) ||
    manifest.bytes < 20 ||
    manifest.bytes > 64 * 1024 * 1024 ||
    !/^[a-f0-9]{64}$/i.test(manifest.display_sha256)
  )
    throw new Error('产品清单缺少有效的大小或完整性校验信息')
  if (!globalThis.crypto?.subtle) throw new Error('完整性校验需要 HTTPS 或本机安全环境，模型未加载')
  const modelUrl = new URL(trustedProductUrl(manifest.model_url))
  const requestedFamily = modelUrl.searchParams.get('family')
  if (requestedFamily && !isProductFamily(requestedFamily)) throw new Error('产品模型类型不受信任')
  if (manifest.family && (requestedFamily || 'PLUG') !== manifest.family)
    throw new Error('产品模型与清单类型不一致')
  modelUrl.searchParams.set('sha256', manifest.display_sha256.toLowerCase())
  const response = await fetch(modelUrl.href, {
    signal,
    credentials: 'include',
  })
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('carbentra:session-expired'))
    throw new Error(`产品模型读取失败（HTTP ${response.status}）`)
  }
  let buffer: ArrayBuffer
  if (response.body) {
    const reader = response.body.getReader()
    const chunks: Uint8Array[] = []
    let length = 0
    let lastPercent = -1
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      length += value.byteLength
      if (length > manifest.bytes) {
        await reader.cancel()
        throw new Error('产品模型超过清单声明大小')
      }
      chunks.push(value)
      const percent = Math.floor((length / manifest.bytes) * 100)
      if (percent !== lastPercent) {
        lastPercent = percent
        progress(Math.min(1, length / manifest.bytes))
      }
    }
    if (length !== manifest.bytes) throw new Error('产品模型长度与固定清单不一致')
    const bytes = new Uint8Array(length)
    let offset = 0
    for (const chunk of chunks) {
      bytes.set(chunk, offset)
      offset += chunk.byteLength
    }
    buffer = bytes.buffer
  } else buffer = await response.arrayBuffer()
  if (signal.aborted) throw new DOMException('Aborted', 'AbortError')
  if (buffer.byteLength !== manifest.bytes) throw new Error('产品模型长度与固定清单不一致')
  const digest = await crypto.subtle.digest('SHA-256', buffer)
  const hash = [...new Uint8Array(digest)].map((n) => n.toString(16).padStart(2, '0')).join('')
  if (hash !== manifest.display_sha256.toLowerCase())
    throw new Error('产品模型 SHA-256 校验失败，已停止展示')
  progress(1)
  return buffer
}
