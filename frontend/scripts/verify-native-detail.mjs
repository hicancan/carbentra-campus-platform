// CPU-only integration check with the exact shipped Three.js GLTFLoader. No renderer/browser.
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { detailMeshes, disposeModel } from '../src/lib/building-detail.ts'
const [path, assetId] = process.argv.slice(2)
if (!path || !assetId)
  throw new Error('Usage: node scripts/verify-native-detail.mjs source.glb exact_asset_id')
const bytes = await readFile(path)
const gltf = await new GLTFLoader().parseAsync(
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
  '',
)
const before = new THREE.Box3().setFromObject(gltf.scene)
const originals = new Map()
gltf.scene.traverse((object) => {
  if (object instanceof THREE.Mesh) originals.set(object, object.material)
})
const meshes = detailMeshes(gltf.scene, assetId, `building:map:${assetId}`)
assert.equal(meshes.length, originals.size)
for (const mesh of meshes) {
  assert.equal(mesh.material, originals.get(mesh), 'Original PBR reference changed')
  assert.equal(mesh.userData.buildingId, `building:map:${assetId}`)
}
const after = new THREE.Box3().setFromObject(gltf.scene)
assert(before.equals(after), 'Campus placement changed')
const primitiveChildrenWithoutOwnId = meshes.filter((mesh) => !mesh.userData.asset_id).length
const previous = meshes[0].userData.asset_id
meshes[0].userData.asset_id = 'inert-conflicting-asset'
assert.throws(() => detailMeshes(gltf.scene, assetId, `building:map:${assetId}`), /身份不一致/)
if (previous === undefined) delete meshes[0].userData.asset_id
else meshes[0].userData.asset_id = previous
console.log(
  JSON.stringify(
    {
      status: 'passed',
      source_sha256: createHash('sha256').update(bytes).digest('hex'),
      bytes: bytes.byteLength,
      asset_id: assetId,
      primitive_mesh_count: meshes.length,
      primitive_children_resolved_through_ancestor: primitiveChildrenWithoutOwnId,
      pbr_material_references_preserved: true,
      world_bounds_unchanged: true,
      conflicting_child_id_rejected: true,
      bounds_gltf: [...before.min.toArray(), ...before.max.toArray()],
      renderer_created: false,
    },
    null,
    2,
  ),
)
disposeModel(gltf.scene)
