// CPU-only check with the shipped GLTFLoader; does not claim WebGL/browser rendering.
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { createHash } from 'node:crypto'
import assert from 'node:assert/strict'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
const root = resolve(process.argv[2] || '../packages/product/dist')
const catalog = JSON.parse(await readFile(resolve(root, 'catalog.json'), 'utf8'))
const results = []
for (const family of ['PLUG', 'SWITCH', 'PRESENCE']) {
  assert.equal(catalog.format, 'carbentra-product-catalog')
  assert.equal(catalog.schema_version, 1)
  const item = catalog.products[family]
  const manifest = JSON.parse(await readFile(resolve(root, item.manifest), 'utf8'))
  const bytes = await readFile(resolve(root, item.model))
  assert.equal(manifest.family, family)
  assert.equal(createHash('sha256').update(bytes).digest('hex'), manifest.display_sha256)
  const manager = new THREE.LoadingManager()
  manager.setURLModifier((url) => {
    if (url.startsWith('data:') || url.startsWith('blob:')) return url
    throw new Error('Product model is not self-contained')
  })
  const gltf = await new GLTFLoader(manager).parseAsync(
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    '',
  )
  const declared = new Set(manifest.parts.map((part) => part.id)),
    found = new Set()
  let meshes = 0
  gltf.scene.traverse((object) => {
    const index = gltf.parser.associations.get(object)?.nodes
    const name = index === undefined ? undefined : gltf.parser.json.nodes[index]?.name
    if (name && declared.has(name)) found.add(name)
    if (object instanceof THREE.Mesh) meshes++
  })
  assert.equal(declared.size, manifest.parts.length, 'Duplicate declared part IDs')
  assert.equal(found.size, declared.size, `Viewer cannot resolve every ${family} part`)
  assert(meshes > 0)
  const bounds = new THREE.Box3().setFromObject(gltf.scene),
    size = bounds.getSize(new THREE.Vector3())
  assert(size.toArray().every(Number.isFinite) && size.length() > 0)
  results.push({
    family,
    bytes: bytes.length,
    manifest_parts: declared.size,
    resolved_parts: found.size,
    meshes,
    bounds: [...bounds.min.toArray(), ...bounds.max.toArray()],
  })
  gltf.scene.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return
    object.geometry.dispose()
    for (const material of Array.isArray(object.material) ? object.material : [object.material])
      material.dispose()
  })
  gltf.scene.clear()
}
const result = {
  status: 'passed',
  renderer_created: false,
  browser_verified: false,
  families: results,
}
const output = JSON.stringify(result, null, 2) + '\n'
if (process.argv[3]) await writeFile(process.argv[3], output)
process.stdout.write(output)
