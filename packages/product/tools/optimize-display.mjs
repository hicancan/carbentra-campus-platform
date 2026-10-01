import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { NodeIO } from '@gltf-transform/core'
import { ALL_EXTENSIONS } from '@gltf-transform/extensions'
import { quantize } from '@gltf-transform/functions'

export const OPTIONS = Object.freeze({
  quantizePosition: 16,
  quantizeNormal: 16,
  quantizationVolume: 'mesh',
  cleanup: false,
})
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex')
export function metadata(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  if (bytes.byteLength < 24 || bytes.byteLength > 64 * 1024 * 1024 ||
      view.getUint32(0, true) !== 0x46546c67 || view.getUint32(4, true) !== 2 ||
      view.getUint32(8, true) !== bytes.byteLength || view.getUint32(16, true) !== 0x4e4f534a)
    throw new Error('Expected a bounded GLB 2.0 container')
  const length = view.getUint32(12, true)
  if (length > 2 * 1024 * 1024 || 20 + length > bytes.byteLength) throw new Error('Invalid metadata length')
  const json = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + length)))
  if (json.buffers?.some((item) => item.uri) || json.images?.some((item) => item.uri))
    throw new Error('External resources are prohibited')
  if (json.animations?.length || json.skins?.length) throw new Error('Animated or skinned assets need a separate pipeline')
  const names = (json.nodes || []).map((node) => node.name)
  if (!names.length || names.some((name) => typeof name !== 'string' || !name) || new Set(names).size !== names.length)
    throw new Error('Every source part must retain a unique named node')
  return json
}
export async function optimize({ source, output, report, expectedSha256 }) {
  const paths = [source, output, report].map((path) => resolve(path))
  if (new Set(paths).size !== 3) throw new Error('Source, candidate and report must be separate files')
  const dist = resolve(fileURLToPath(new URL('../dist/', import.meta.url)))
  if (paths.slice(1).some((path) => path === dist || path.startsWith(dist + '/')))
    throw new Error('Candidate tooling must not write the published dist directory')
  if (!/^[a-f0-9]{64}$/.test(expectedSha256 || '')) throw new Error('An exact expected source SHA-256 is required')
  const bytes = await readFile(paths[0])
  if (sha(bytes) !== expectedSha256) throw new Error('Pinned source hash mismatch')
  const original = metadata(bytes)
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).setAllowNetwork(false)
  const document = await io.readBinary(bytes)
  await document.transform(quantize({ ...OPTIONS, pattern: /^(POSITION|NORMAL)$/ }))
  // Quantize(cleanup:false) retains superseded float accessors. Remove only
  // unreferenced storage; never prune nodes, meshes, materials or named parts.
  let removedUnreferencedAccessors = 0
  const root = document.getRoot()
  for (const accessor of root.listAccessors()) {
    if (accessor.listParents().every((parent) => parent === root)) {
      accessor.dispose()
      removedUnreferencedAccessors++
    }
  }
  const candidate = await io.writeBinary(document)
  const result = metadata(candidate)
  const names = (json) => json.nodes.map((node) => node.name).sort()
  if (JSON.stringify(names(original)) !== JSON.stringify(names(result))) throw new Error('Named part identities changed')
  if (result.extensionsRequired?.some((name) => name !== 'KHR_mesh_quantization'))
    throw new Error('Unexpected required decoder or extension')
  const provenance = {
    schema_version: 1,
    status: 'candidate_requires_independent_validation',
    source_sha256: expectedSha256,
    display_sha256: sha(candidate),
    source_bytes: bytes.byteLength,
    display_bytes: candidate.byteLength,
    bytes_saved: bytes.byteLength - candidate.byteLength,
    tool: '@gltf-transform/functions', tool_version: '4.3.0',
    operation: 'quantize', removed_unreferenced_accessors: removedUnreferencedAccessors, options: { ...OPTIONS, pattern: '^(POSITION|NORMAL)$' },
    forbidden_operations: ['join', 'flatten', 'simplify', 'prune', 'dedup'],
    required_extensions: result.extensionsRequired || [],
    source_node_count: original.nodes.length, display_node_count: result.nodes.length,
    physical_geometry_claim: false,
  }
  await writeFile(paths[1], candidate)
  await writeFile(paths[2], JSON.stringify(provenance, null, 2) + '\n')
  return provenance
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, i, all) => {
    if (i % 2 === 0) pairs.push([value.replace(/^--/, ''), all[i + 1]])
    return pairs
  }, []))
  try {
    const result = await optimize({ source: args.source, output: args.output, report: args.report, expectedSha256: args['expected-sha256'] })
    process.stdout.write(JSON.stringify(result) + '\n')
  } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1 }
}
