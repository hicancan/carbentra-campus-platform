import { describe, expect, it, vi } from 'vitest'
import * as THREE from 'three'
import { detailMeshes, disposeModel } from './building-detail'
function sample() {
  const scene = new THREE.Group(),
    root = new THREE.Group()
  root.name = 'asset-A'
  root.userData.asset_id = 'asset-A'
  root.position.set(20, 3, -50)
  const material = new THREE.MeshStandardMaterial({
    color: '#804030',
    metalness: 0.2,
    roughness: 0.7,
  })
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(), material)
  mesh.userData.asset_id = 'asset-A'
  root.add(mesh)
  scene.add(root)
  return { scene, root, mesh, material }
}
describe('single-building native detail identity', () => {
  it('preserves authored material and campus placement while attaching semantic picking', () => {
    const { scene, root, mesh, material } = sample()
    expect(detailMeshes(scene, 'asset-A', 'building:map:asset-A')).toEqual([mesh])
    expect(mesh.material).toBe(material)
    expect(root.position.toArray()).toEqual([20, 3, -50])
    expect(mesh.userData.buildingId).toBe('building:map:asset-A')
  })
  it('rejects a mismatched mesh identity instead of replacing the base shell', () => {
    const { scene, mesh } = sample()
    mesh.userData.asset_id = 'another-asset'
    expect(() => detailMeshes(scene, 'asset-A', 'building:map:asset-A')).toThrow(/身份不一致/)
  })
  it('releases loaded geometry and materials once', () => {
    const { scene, mesh, material } = sample()
    const geometry = vi.spyOn(mesh.geometry, 'dispose'),
      dispose = vi.spyOn(material, 'dispose')
    disposeModel(scene)
    expect(geometry).toHaveBeenCalledOnce()
    expect(dispose).toHaveBeenCalledOnce()
  })
  it('resolves multi-material primitive children through their authored node Group', () => {
    const { scene, root, mesh, material } = sample()
    root.remove(mesh)
    const authoredNode = new THREE.Group()
    authoredNode.userData.asset_id = 'asset-A'
    delete mesh.userData.asset_id
    const second = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial())
    authoredNode.add(mesh, second)
    root.add(authoredNode)
    expect(detailMeshes(scene, 'asset-A', 'building:map:asset-A')).toEqual([mesh, second])
    expect(mesh.material).toBe(material)
    expect(second.userData.buildingId).toBe('building:map:asset-A')
    authoredNode.userData.asset_id = 'conflicting-asset'
    expect(() => detailMeshes(scene, 'asset-A', 'building:map:asset-A')).toThrow(/身份不一致/)
  })
})
