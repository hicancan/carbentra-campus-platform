import { useQuery } from '@tanstack/react-query'
export const SPATIAL_BASE = '/assets/spatial/'
export interface SpatialBuilding {
  asset_id: string
  building_id: string
  node_name: string
  name: string
  center_local_m: [number, number, number]
  bounds_local_m: [number, number, number, number, number, number]
  height_m: number
  height_source: string
  levels: number
  geometry_role: string
  mesh_url: string
  detail_mesh_url?: string
  detail_mesh_sha256?: string
  detail_bounds_local_m?: [number, number, number, number, number, number]
  detail_geometry_status?: string
  detail_bytes?: number
  detail_triangles?: number
  detail_report_url?: string
  search_building_id: string | null
  measured_height: boolean
}
export interface SpatialManifest {
  version: string
  source_version: string
  campus_mesh_url: string
  local_geojson_url: string
  context_mesh_url?: string
  context_local_geojson_url?: string
  room_spatial_index_url?: string
  floorplans: Record<string, string>
  buildings: SpatialBuilding[]
  counts: Record<string, number>
  limitations: string[]
  provenance: Record<string, unknown>
  available?: boolean
}
export interface SpatialFeature {
  type: 'Feature'
  properties: {
    building_id: string
    asset_id: string
    name: string
    height_m: number
  }
  geometry: {
    type: 'Polygon' | 'MultiPolygon'
    coordinates: number[][][] | number[][][][]
  }
}
export interface SpatialGeoJSON {
  type: 'FeatureCollection'
  features: SpatialFeature[]
}
export interface Floorplan {
  floor_id: string
  building_id: string
  view_box?: [number, number]
  coordinate_system: string
  geometry_accuracy: string
  registration_status: string
  observed_occupancy: string
  source_version: string
  space_units: {
    id: string
    space_id: string | null
    name: string
    polygon: number[][]
    label_point: [number, number]
    geometry_status: string
  }[]
}
export function spatialUrl(path: string, version?: string) {
  const relative = path.startsWith(SPATIAL_BASE) ? path.slice(SPATIAL_BASE.length) : path
  let decoded: string
  try {
    decoded = decodeURIComponent(relative)
  } catch {
    throw new Error('空间资源路径不受信任')
  }
  if (
    !relative ||
    decoded.startsWith('/') ||
    decoded.includes('://') ||
    decoded.includes('\\') ||
    decoded.includes('?') ||
    decoded.includes('#') ||
    decoded.split('/').includes('..') ||
    decoded.includes('\0')
  )
    throw new Error('空间资源路径不受信任')
  return `${SPATIAL_BASE}${relative}${version ? `?v=${encodeURIComponent(version)}` : ''}`
}
export function useSpatial<T>(path?: string | null, version?: string) {
  return useQuery({
    queryKey: ['spatial', path, version],
    enabled: !!path,
    staleTime: Infinity,
    queryFn: async ({ signal }) => {
      const response = await fetch(spatialUrl(path!, version), {
        signal,
        credentials: 'include',
      })
      if (!response.ok) throw new Error(`空间资源暂时不可用（HTTP ${response.status}）`)
      return response.json() as Promise<T>
    },
  })
}
export function polygonRings(feature: SpatialFeature): number[][][] {
  return feature.geometry.type === 'Polygon'
    ? (feature.geometry.coordinates as number[][][])
    : (feature.geometry.coordinates as number[][][][]).flatMap((p) => p)
}

export interface SpatialContextFeature {
  type: 'Feature'
  properties: {
    asset_id: string
    name?: string
    context_layer:
      | 'boundary'
      | 'greens'
      | 'waters'
      | 'sports'
      | 'surfaces'
      | 'roads'
      | 'context_buildings'
    width?: number
    [key: string]: unknown
  }
  geometry:
    | { type: 'Polygon'; coordinates: number[][][] }
    | { type: 'MultiPolygon'; coordinates: number[][][][] }
    | { type: 'LineString'; coordinates: number[][] }
    | { type: 'MultiLineString'; coordinates: number[][][] }
}
export interface SpatialContextGeoJSON {
  type: 'FeatureCollection'
  features: SpatialContextFeature[]
}
