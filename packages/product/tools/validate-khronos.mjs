import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { basename, resolve } from 'node:path'
import validator from 'gltf-validator'
const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, all) => {
  if (index % 2 === 0) pairs.push([value.replace(/^--/, ''), all[index + 1]])
  return pairs
}, []))
if (!args.candidate || !args.report || resolve(args.candidate) === resolve(args.report))
  throw new Error('Usage: node validate-khronos.mjs --candidate display.glb --report distinct-report.json')
const bytes = await readFile(args.candidate)
const report = await validator.validateBytes(new Uint8Array(bytes), { uri: basename(args.candidate) })
const result = {
  schema_version: 1,
  candidate_sha256: createHash('sha256').update(bytes).digest('hex'),
  candidate_bytes: bytes.byteLength,
  validator_package: 'gltf-validator',
  validator_version: report.validatorVersion,
  status: report.issues.numErrors === 0 && report.issues.numWarnings === 0 ? 'passed' : 'failed',
  report,
}
await writeFile(args.report, JSON.stringify(result, null, 2) + '\n')
process.stdout.write(JSON.stringify({status:result.status,candidate_sha256:result.candidate_sha256,errors:report.issues.numErrors,warnings:report.issues.numWarnings,infos:report.issues.numInfos}) + '\n')
if (result.status !== 'passed') process.exitCode = 1
