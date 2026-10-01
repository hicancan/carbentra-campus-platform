import * as THREE from 'three'
export function boundsCorners(bounds: THREE.Box3) {
  return [bounds.min.x, bounds.max.x].flatMap((x) =>
    [bounds.min.y, bounds.max.y].flatMap((y) =>
      [bounds.min.z, bounds.max.z].map((z) => new THREE.Vector3(x, y, z)),
    ),
  )
}
export function campusViewDirection(aspect: number) {
  return aspect < 1 ? new THREE.Vector3(0, 1.8, 0.8) : new THREE.Vector3(0.72, 1.07, 0.94)
}
/** Fits every bound corner to the current horizontal and vertical frustum. */
export function fitPerspectiveBounds(
  camera: THREE.PerspectiveCamera,
  bounds: THREE.Box3,
  direction = new THREE.Vector3(0.72, 1.07, 0.94),
  padding = 1.14,
) {
  const corners = boundsCorners(bounds)
  if (
    bounds.isEmpty() ||
    !corners.every((point) => point.toArray().every(Number.isFinite)) ||
    !Number.isFinite(camera.aspect) ||
    camera.aspect <= 0 ||
    !Number.isFinite(camera.fov) ||
    !Number.isFinite(camera.zoom) ||
    camera.zoom <= 0 ||
    camera.fov <= 0 ||
    camera.fov >= 179 ||
    !Number.isFinite(padding) ||
    padding < 1
  )
    throw new Error('无法拟合无效的显示边界')
  const backward = direction.clone().normalize()
  if (backward.lengthSq() < 0.9) backward.set(0.72, 1.07, 0.94).normalize()
  const right = new THREE.Vector3().crossVectors(camera.up, backward).normalize()
  if (right.lengthSq() < 0.9) right.set(1, 0, 0)
  const up = new THREE.Vector3().crossVectors(backward, right).normalize()
  const tanY = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) / camera.zoom
  const tanX = tanY * camera.aspect
  const target = bounds.getCenter(new THREE.Vector3())
  const place = () => {
    let distance = Math.max(camera.near * 2, 1)
    for (const corner of corners) {
      const offset = corner.clone().sub(target),
        depth = offset.dot(backward)
      distance = Math.max(
        distance,
        depth + (Math.abs(offset.dot(right)) * padding) / tanX,
        depth + (Math.abs(offset.dot(up)) * padding) / tanY,
        depth + camera.near * 2,
      )
    }
    camera.position.copy(target).addScaledVector(backward, distance)
    camera.lookAt(target)
    camera.updateProjectionMatrix()
    camera.updateMatrixWorld(true)
    return distance
  }
  // A perspective-projected box can be off-center even when its world center is centered.
  for (let iteration = 0; iteration < 6; iteration++) {
    const distance = place()
    const projected = corners.map((point) => point.clone().project(camera))
    const midX =
      (Math.min(...projected.map((p) => p.x)) + Math.max(...projected.map((p) => p.x))) / 2
    const midY =
      (Math.min(...projected.map((p) => p.y)) + Math.max(...projected.map((p) => p.y))) / 2
    if (Math.abs(midX) + Math.abs(midY) < 0.002) break
    target
      .addScaledVector(right, midX * distance * tanX)
      .addScaledVector(up, midY * distance * tanY)
  }
  place()
  return target
}
