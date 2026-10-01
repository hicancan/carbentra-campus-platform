// CPU-only numerical framing proof with the real published campus bounds.
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { boundsCorners, campusViewDirection, fitPerspectiveBounds } from '../src/lib/camera-fit.ts'
const root = new URL('../../packages/spatial/dist/', import.meta.url)
const manifest = JSON.parse(await readFile(new URL('manifest.json', root), 'utf8'))
const bytes = await readFile(new URL(manifest.campus_mesh_url, root))
const gltf = await new GLTFLoader().parseAsync(
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
  '',
)
const bounds = new THREE.Box3().setFromObject(gltf.scene)
function projection(camera) {
  camera.updateProjectionMatrix()
  camera.updateMatrixWorld(true)
  const points = boundsCorners(bounds).map((point) => point.project(camera))
  const xs = points.map((p) => p.x),
    ys = points.map((p) => p.y)
  return {
    width_fraction: (Math.max(...xs) - Math.min(...xs)) / 2,
    height_fraction: (Math.max(...ys) - Math.min(...ys)) / 2,
    center_ndc: [(Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...ys) + Math.min(...ys)) / 2],
    all_corners_visible: points.every(
      (p) => Math.abs(p.x) <= 1 && Math.abs(p.y) <= 1 && Math.abs(p.z) <= 1,
    ),
  }
}
const old = new THREE.PerspectiveCamera(38, 886 / 516, 1, 15000),
  center = bounds.getCenter(new THREE.Vector3()),
  size = bounds.getSize(new THREE.Vector3()),
  span = Math.max(size.x, size.z)
old.position.set(center.x + span * 0.72, span * 1.07, center.z + span * 0.94)
old.lookAt(center)
const desktop = new THREE.PerspectiveCamera(38, 886 / 516, 1, 15000),
  mobile = new THREE.PerspectiveCamera(38, 0.58, 1, 15000)
fitPerspectiveBounds(desktop, bounds, campusViewDirection(desktop.aspect))
fitPerspectiveBounds(mobile, bounds, campusViewDirection(mobile.aspect))
console.log(
  JSON.stringify(
    {
      manifest_version: manifest.version,
      source_sha256: createHash('sha256').update(bytes).digest('hex'),
      bounds_gltf: [...bounds.min.toArray(), ...bounds.max.toArray()],
      previous_desktop: projection(old),
      fitted_desktop: projection(desktop),
      fitted_mobile: projection(mobile),
      renderer_created: false,
    },
    null,
    2,
  ),
)
