import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { Document, NodeIO } from '@gltf-transform/core'
import { metadata, optimize } from './optimize-display.mjs'

async function fixture() {
  const dir = await mkdtemp(join(tmpdir(), 'carbentra-product-test-'))
  const document = new Document()
  const buffer = document.createBuffer()
  const positions = document.createAccessor().setType('VEC3').setArray(new Float32Array([0,0,0, 0.1,0,0, 0,0.1,0])).setBuffer(buffer)
  const normals = document.createAccessor().setType('VEC3').setArray(new Float32Array([0,0,1, 0,0,1, 0,0,1])).setBuffer(buffer)
  const indices = document.createAccessor().setType('SCALAR').setArray(new Uint16Array([0,1,2])).setBuffer(buffer)
  const material = document.createMaterial('Pinned PBR').setRoughnessFactor(0.3).setMetallicFactor(0.2)
  const mesh = document.createMesh('Test mesh').addPrimitive(document.createPrimitive().setAttribute('POSITION',positions).setAttribute('NORMAL',normals).setIndices(indices).setMaterial(material))
  const node = document.createNode('Exact-Part-ID').setMesh(mesh).setExtras({source:'Inert fixture'})
  document.createScene().addChild(node)
  const bytes = await new NodeIO().writeBinary(document)
  const source = join(dir,'source.glb')
  await writeFile(source,bytes)
  return {source, output:join(dir,'candidate.glb'), report:join(dir,'candidate.json'), expectedSha256:createHash('sha256').update(bytes).digest('hex')}
}
test('keeps named node/provenance and emits only built-in quantization', async () => {
  const options = await fixture()
  const result = await optimize(options)
  const out = metadata(await readFile(options.output))
  assert.equal(result.status,'candidate_requires_independent_validation')
  assert.equal(out.nodes[0].name,'Exact-Part-ID')
  assert.deepEqual(out.nodes[0].extras,{source:'Inert fixture'})
  assert.deepEqual(out.extensionsRequired,['KHR_mesh_quantization'])
  const repeated = await optimize(options)
  assert.equal(repeated.display_sha256,result.display_sha256)
})
test('refuses source mutation and an unexpected source fingerprint', async () => {
  const options = await fixture()
  await assert.rejects(optimize({...options,output:options.source}),/separate files/)
  await assert.rejects(optimize({...options,expectedSha256:'0'.repeat(64)}),/hash mismatch/)
})
test('rejects a malformed asset before reading it as a scene', () => {
  assert.throws(() => metadata(Buffer.alloc(24)),/GLB/)
})
