import { lazy, Suspense, useState } from 'react'
import { Box, Layers3, RefreshCw, Search, ShieldCheck } from 'lucide-react'
import { useResource } from '../lib/hooks'
import type { ProductManifest, ProductFamily } from '../lib/product'
import { manifestMatchesFamily, productFamilyName } from '../lib/product'
import { queryString } from '../lib/api'
import { formatNumber, shortId } from '../lib/format'
import { Badge, Button, DefinitionList, EmptyState, ErrorState, Loading, Notice } from './ui'
const ProductCanvas = lazy(() => import('./ProductCanvas'))
function KnownProductReference({ family }: { family: ProductFamily }) {
  const query = useResource<ProductManifest>(`/assets/product/manifest${queryString({ family })}`, {
    interval: false,
    enabled: !!family,
  })
  const [loaded, setLoaded] = useState(false),
    [selected, setSelected] = useState(''),
    [search, setSearch] = useState(''),
    [isolate, setIsolate] = useState(false),
    [rotate, setRotate] = useState(false)

  const d = query.data
  const part = d?.parts.find((p) => p.id === selected)
  if (query.isLoading) return <Loading label="正在读取产品参考清单…" />
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch()
        }}
      />
    )
  if (!d)
    return <EmptyState title="未发布产品参考模型" description="设备遥测与控制功能不依赖产品模型" />
  if (!manifestMatchesFamily(d, family))
    return <Notice tone="warning">产品参考清单与所选类型不一致，模型未加载</Notice>
  return (
    <div className="product-reference">
      <Notice title="产品参考，独立于现场设备安装">
        {d.product_name || productFamilyName(family)}{' '}
        工程展示资产，不能证明所选点位的型号、安装、标定或电气安全状态。CAD/ECAD
        仍是工程源；这里保留显示产物的版本与零件身份。
      </Notice>
      {loaded ? (
        <>
          <Suspense fallback={<Loading label="正在加载产品视图引擎…" />}>
            <ProductCanvas
              manifest={d}
              selected={selected}
              isolate={isolate}
              rotate={rotate}
              onSelect={setSelected}
            />
          </Suspense>
          <div className="product-options">
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={isolate}
                onChange={(e) => setIsolate(e.target.checked)}
                disabled={!selected}
              />
              单独显示选中零件
            </label>
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={rotate}
                onChange={(e) => setRotate(e.target.checked)}
              />
              自动旋转
            </label>
            <Button
              variant="ghost"
              onClick={() => {
                setLoaded(false)
                setSelected('')
                setIsolate(false)
                setRotate(false)
              }}
            >
              卸载模型
            </Button>
          </div>
          <div className="product-parts">
            <label className="search-field">
              <Search size={15} />
              <input
                aria-label="搜索产品零件"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索稳定零件 ID…"
              />
            </label>
            <div className="product-part-list">
              {d.parts
                .filter((p) => `${p.id} ${p.name}`.toLowerCase().includes(search.toLowerCase()))
                .map((p) => (
                  <button
                    key={p.id}
                    className={selected === p.id ? 'selected' : ''}
                    onClick={() => setSelected(p.id)}
                  >
                    <Layers3 size={13} />
                    <span>{p.name || p.id}</span>
                  </button>
                ))}
            </div>
          </div>
          {part && (
            <DefinitionList
              items={[
                ['稳定零件 ID', part.id],
                [
                  '参考来源',
                  part.source_part ||
                    part.source ||
                    part.provenance?.source ||
                    '硬件发布产物中的原始节点',
                ],
                [
                  '验证边界',
                  part.development_status ||
                    part.provenance?.development_status ||
                    '工程参考，现场验证未在此模型中体现',
                ],
              ]}
            />
          )}
        </>
      ) : (
        <div className="product-consent">
          <span>
            <Box size={36} />
          </span>
          <h3>打开产品工程模型</h3>
          <p>
            {formatNumber(d.bytes / 1024 / 1024, 1)} MiB · {formatNumber(d.node_count, 0)} 个源节点
            · {formatNumber(d.triangle_count, 0)} 个三角面
          </p>
          <Button variant="primary" onClick={() => setLoaded(true)}>
            <Box size={16} />
            加载三维参考模型
          </Button>
          <small>仅在此处按需下载；不会为每台校园设备重复实例化</small>
        </div>
      )}
      <div className="inline-gap section-space">
        <Badge tone="teal">
          <ShieldCheck size={12} />
          固定 SHA-256 产物
        </Badge>
        <Badge>{d.optimized ? '优化显示衍生件' : '原始发布显示件'}</Badge>
        <Badge>单位 {d.units}</Badge>
        <Button
          variant="ghost"
          loading={query.isFetching}
          onClick={() => {
            setLoaded(false)
            setSelected('')
            setIsolate(false)
            setRotate(false)
            void query.refetch()
          }}
        >
          <RefreshCw size={13} />
          {loaded ? '刷新资料并卸载' : '刷新发布资料'}
        </Button>
      </div>
      <DefinitionList
        items={[
          ['产物版本', shortId(String(d.version), 24)],
          ['显示文件 SHA-256', <span className="monospace">{d.display_sha256}</span>],
          ['源文件 SHA-256', <span className="monospace">{d.source_sha256}</span>],
          ['硬件源提交', <span className="monospace">{d.source_commit}</span>],
        ]}
      />
    </div>
  )
}

export default function ProductReference({ family }: { family?: ProductFamily | null }) {
  if (!family)
    return (
      <EmptyState
        title="此设备没有已核验的产品参考类型"
        description="不会把未知型号套用 Plug 模型；设备数据与管理不依赖模型"
      />
    )
  return <KnownProductReference key={family} family={family} />
}
