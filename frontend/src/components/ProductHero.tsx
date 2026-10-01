import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useResource } from '../lib/hooks'
import { queryString } from '../lib/api'
import type { ProductFamily, ProductManifest } from '../lib/product'
import { manifestMatchesFamily, productFamilyName, trustedProductHeroUrl } from '../lib/product'
/** Small published engineering image only; this component never instantiates a 3D viewer. */
export default function ProductHero({
  family,
  fallback,
}: {
  family: ProductFamily
  fallback: ReactNode
}) {
  const query = useResource<ProductManifest>(`/assets/product/manifest${queryString({ family })}`, {
    interval: false,
  })
  const [failed, setFailed] = useState(false)
  let source = ''
  const manifest = query.data
  if (
    manifest &&
    manifestMatchesFamily(manifest, family) &&
    manifest.hero_url &&
    /^[a-f0-9]{64}$/i.test(manifest.hero_sha256 || '')
  ) {
    try {
      const url = new URL(trustedProductHeroUrl(manifest.hero_url, family))
      url.searchParams.set('sha256', manifest.hero_sha256!)
      source = url.href
    } catch {
      /* A bad optional image never blocks room operations. */
    }
  }
  useEffect(() => setFailed(false), [source])
  return (
    <div className="room-product-hero">
      {source && !failed ? (
        <img
          src={source}
          loading="lazy"
          decoding="async"
          alt={`${productFamilyName(family)} 工程参考图，非现场安装证明`}
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="room-product-fallback">{fallback}</div>
      )}
      <small>{source && !failed ? '工程参考 · 非现场照片' : '工程参考图暂不可用'}</small>
    </div>
  )
}
