import type { SpatialContextFeature, SpatialContextGeoJSON } from '../lib/spatial'
const LAYERS = ['boundary', 'surfaces', 'greens', 'waters', 'sports', 'roads', 'context_buildings']
export function contextGeometryPath(
  feature: SpatialContextFeature,
  project: (p: number[]) => string,
): string {
  const geometry = feature.geometry
  if (geometry.type === 'LineString') return `M${geometry.coordinates.map(project).join(' L')}`
  if (geometry.type === 'MultiLineString')
    return geometry.coordinates.map((line) => `M${line.map(project).join(' L')}`).join(' ')
  const rings = geometry.type === 'Polygon' ? geometry.coordinates : geometry.coordinates.flat()
  return rings.map((ring) => `M${ring.map(project).join(' L')}Z`).join(' ')
}
export default function CampusContext2D({
  data,
  project,
  scale,
}: {
  data: SpatialContextGeoJSON
  project: (p: number[]) => string
  scale: number
}) {
  return (
    <g className="map-context" aria-hidden="true" pointerEvents="none">
      {[...data.features]
        .sort(
          (a, b) =>
            LAYERS.indexOf(a.properties.context_layer) - LAYERS.indexOf(b.properties.context_layer),
        )
        .map((feature, index) => {
          const layer = feature.properties.context_layer
          const roadWidth =
            typeof feature.properties.width === 'number' &&
            Number.isFinite(feature.properties.width)
              ? Math.max(0.3, Math.min(30, feature.properties.width)) * scale
              : 3 * scale
          return (
            <path
              key={`${layer}-${feature.properties.asset_id}-${index}`}
              data-context-layer={layer}
              className={`context-${layer}`}
              d={contextGeometryPath(feature, project)}
              fillRule="evenodd"
              strokeWidth={layer === 'roads' ? roadWidth : undefined}
            />
          )
        })}
    </g>
  )
}
