import * as THREE from 'three'

export function detailMeshes(model: THREE.Object3D, assetId: string, buildingId: string) {
  let roots = 0
  const meshes: THREE.Mesh[] = []
  model.traverse((object) => {
    if (object.name === assetId && object.userData.asset_id === assetId) roots++
    if (object instanceof THREE.Mesh) {
      let node: THREE.Object3D | null = object
      let verifiedRoot = false
      while (node) {
        if (node.userData.asset_id !== undefined && node.userData.asset_id !== assetId)
          throw new Error('外观模型的楼栋身份不一致，已保留基础模型')
        if (node.name === assetId && node.userData.asset_id === assetId) {
          verifiedRoot = true
          break
        }
        node = node.parent
      }
      if (!verifiedRoot) throw new Error('外观模型的楼栋身份不一致，已保留基础模型')
      meshes.push(object)
    }
  })
  if (roots !== 1 || !meshes.length) throw new Error('外观模型缺少可核验的楼栋身份')
  for (const mesh of meshes) {
    mesh.userData.buildingId = buildingId
    mesh.castShadow = true
    mesh.receiveShadow = true
  }
  return meshes
}
export function disposeModel(model: THREE.Object3D) {
  const geometry = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const textures = new Set<THREE.Texture>()
  model.traverse((object) => {
    if (!(object instanceof THREE.Mesh || object instanceof THREE.LineSegments)) return
    geometry.add(object.geometry)
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      materials.add(material)
      for (const value of Object.values(material))
        if (value instanceof THREE.Texture) textures.add(value)
    }
  })
  geometry.forEach((item) => item.dispose())
  materials.forEach((item) => item.dispose())
  textures.forEach((item) => item.dispose())
}
