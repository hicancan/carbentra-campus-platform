import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import openapiTS, { astToString } from 'openapi-typescript'
import { format, resolveConfig } from 'prettier'

const source = new URL('../../packages/contracts/openapi.json', import.meta.url)
const destination = new URL('../src/lib/generated-api.ts', import.meta.url)
const input = await readFile(source, 'utf8')
const sha256 = createHash('sha256').update(input).digest('hex')
const schema = JSON.parse(input)
const ast = await openapiTS(schema)
const header = `// Generated from packages/contracts/openapi.json. Do not edit.\n// Source SHA-256: ${sha256}\n// Regenerate with npm run api:generate; validate with npm run api:check.\n\n`
const config = await resolveConfig(fileURLToPath(destination))
const output = await format(header + astToString(ast), { ...config, parser: 'typescript' })
if (process.argv.includes('--check')) {
  const current = await readFile(destination, 'utf8').catch(() => '')
  if (current !== output) {
    process.stderr.write(
      'Generated API types differ from the pinned OpenAPI. Run npm run api:generate.\n',
    )
    process.exitCode = 1
  } else process.stdout.write(`API contracts match ${sha256}\n`)
} else {
  await writeFile(destination, output)
  process.stdout.write(`Generated src/lib/generated-api.ts from ${sha256}\n`)
}
