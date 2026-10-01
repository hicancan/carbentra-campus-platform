$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose version
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose is unavailable. Start Docker Desktop with Linux containers.' }
$VersionText = docker version --format '{{.Server.Version}}'
if ($LASTEXITCODE -ne 0 -or -not $VersionText) { throw 'Start Docker Desktop using Linux containers, then retry.' }
$Version = $VersionText.Trim()
if ([int]($Version.Split('.')[0]) -lt 28) { throw 'Docker Engine 28+ is required for localhost-only port isolation.' }
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
docker compose up --build -d --wait --wait-timeout 600
if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Inspect: docker compose logs --tail 100' }
$Config = docker compose config --format json | ConvertFrom-Json
$Port = $Config.services.web.ports[0].published
Write-Host "Open http://localhost:$Port. Development only: admin / development-only"
