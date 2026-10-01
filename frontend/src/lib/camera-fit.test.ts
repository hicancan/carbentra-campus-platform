import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import { boundsCorners, campusViewDirection, fitPerspectiveBounds } from './camera-fit'
describe('aspect-aware campus and detail framing', () => {
  it.each([1.72, 1, 0.58, 2.8])('fits and centers all eight corners at aspect %s', (aspect) => {
    const camera = new THREE.PerspectiveCamera(38, aspect, 1, 15000)
    const box = new THREE.Box3(new THREE.Vector3(-430, 0, -950), new THREE.Vector3(480, 62, 1050))
    const target = fitPerspectiveBounds(camera, box)
    expect(target.toArray().every(Number.isFinite)).toBe(true)
    const points = boundsCorners(box).map((point) => point.project(camera))
    for (const point of points) {
      expect(Math.abs(point.x)).toBeLessThanOrEqual(1 / 1.14 + 1e-6)
      expect(Math.abs(point.y)).toBeLessThanOrEqual(1 / 1.14 + 1e-6)
      expect(point.z).toBeGreaterThan(-1)
      expect(point.z).toBeLessThan(1)
    }
    const xs = points.map((p) => p.x),
      ys = points.map((p) => p.y)
    expect(Math.abs(Math.min(...xs) + Math.max(...xs))).toBeLessThan(0.02)
    expect(Math.abs(Math.min(...ys) + Math.max(...ys))).toBeLessThan(0.02)
    expect(
      Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)),
    ).toBeGreaterThan(1.5)
  })
  it('fits an offset native building without moving its campus coordinates', () => {
    const box = new THREE.Box3(
      new THREE.Vector3(127.9, 0, 50.1),
      new THREE.Vector3(216.4, 27.85, 160.95),
    )
    const before = box.clone(),
      camera = new THREE.PerspectiveCamera(38, 1.6, 1, 15000)
    fitPerspectiveBounds(camera, box)
    expect(box.equals(before)).toBe(true)
    expect(boundsCorners(box).every((p) => Math.abs(p.project(camera).x) < 1)).toBe(true)
  })
  it('rejects invalid bounds instead of moving the camera to NaN', () => {
    expect(() => fitPerspectiveBounds(new THREE.PerspectiveCamera(), new THREE.Box3())).toThrow(
      '显示边界',
    )
  })
  it('uses a north-aligned higher view to fill a narrow mobile canvas', () => {
    const camera = new THREE.PerspectiveCamera(38, 0.58, 1, 15000)
    const box = new THREE.Box3(new THREE.Vector3(-507, 0, -796), new THREE.Vector3(512, 23.5, 801))
    fitPerspectiveBounds(camera, box, campusViewDirection(camera.aspect))
    const points = boundsCorners(box).map((point) => point.project(camera))
    expect(points.every((point) => Math.abs(point.x) < 1 && Math.abs(point.y) < 1)).toBe(true)
    expect(
      (Math.max(...points.map((p) => p.y)) - Math.min(...points.map((p) => p.y))) / 2,
    ).toBeGreaterThan(0.6)
  })
})
