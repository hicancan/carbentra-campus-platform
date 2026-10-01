param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidatePattern('^carbentra-[a-z0-9-]+$')][string]$ProjectName = 'carbentra-tests',
    [ValidateRange(1024,65535)][int]$PostgresPort = 15432
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
Set-Location $Root
function Invoke-Check([string]$Name, [string]$Program, [string[]]$Arguments) {
    $Log = Join-Path $OutputDirectory "$Name.log"
    & $Program @Arguments *> $Log
    if ($LASTEXITCODE -ne 0) { Get-Content $Log -Tail 60; throw "$Name failed; see $Log" }
    Write-Host "$Name passed"
}
$Existing = docker ps -aq --filter "label=com.docker.compose.project=$ProjectName"
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop with Linux containers is required' }
if ($Existing) { throw "Project $ProjectName already exists. Choose a separate disposable project name." }
$Names = @('TEMP','TMP','PYTHONUTF8','PYTHONDONTWRITEBYTECODE','CARBENTRA_TEST_PG_PORT',
    'ACCEPTANCE_DATABASE_URL','ACCEPTANCE_DOMAIN_DATABASE_URL','PRICING_TEST_DATABASE_URL',
    'FORECAST_TEST_POSTGRES_URL','SYSTEM_UPGRADE_DATABASE_URL','CARBENTRA_DATABASE_URL','CARBENTRA_PUBLIC_DEMO_TEST_DATABASE_URL')
$Previous = @{}
foreach ($Name in $Names) { $Previous[$Name] = [Environment]::GetEnvironmentVariable($Name, 'Process') }
$Started = $false
try {
    $env:TEMP = $OutputDirectory; $env:TMP = $OutputDirectory
    $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
    if (-not (Test-Path .venv)) { Invoke-Check 'venv' 'uv' @('venv','--python','3.12','.venv') }
    Invoke-Check 'dependencies' 'uv' @('sync','--locked','--all-groups')
    $env:CARBENTRA_TEST_PG_PORT = "$PostgresPort"
    $Started = $true
    Invoke-Check 'postgres-start' 'docker' @('compose','-p',$ProjectName,'-f','compose.test.yaml','up','-d','--wait')
    $Container = "$ProjectName-postgres-tests-1"
    Invoke-Check 'postgres-upgrade-db' 'docker' @('exec',$Container,'createdb','-U','qa','acceptance_upgrade')
    $Url = "postgresql+psycopg://qa@127.0.0.1:$PostgresPort/acceptance"
    $env:ACCEPTANCE_DATABASE_URL=$Url; $env:ACCEPTANCE_DOMAIN_DATABASE_URL=$Url
    $env:PRICING_TEST_DATABASE_URL=$Url; $env:FORECAST_TEST_POSTGRES_URL=$Url
    $env:SYSTEM_UPGRADE_DATABASE_URL="${Url}_upgrade"; $env:CARBENTRA_DATABASE_URL=$env:SYSTEM_UPGRADE_DATABASE_URL
    Push-Location backend
    try {
        Invoke-Check 'migration-old' 'uv' @('run','--locked','alembic','upgrade','ba682468c8c6')
        Invoke-Check 'migration-head' 'uv' @('run','--locked','alembic','upgrade','head')
        Invoke-Check 'migration-repeat' 'uv' @('run','--locked','alembic','upgrade','head')
        Invoke-Check 'migration-check' 'uv' @('run','--locked','alembic','check')
    } finally { Pop-Location }
    Remove-Item Env:CARBENTRA_DATABASE_URL
    $env:CARBENTRA_PUBLIC_DEMO_TEST_DATABASE_URL="postgresql+psycopg://carbentra_public_demo@127.0.0.1:$PostgresPort/carbentra_public_demo"
    Invoke-Check 'public-demo-test-db' 'uv' @('run','--locked','python','tools/public-demo-test-database.py','--confirm-disposable-local-test')
    Invoke-Check 'python-tests' 'uv' @('run','--locked','--all-groups','pytest','--tb=short','backend/tests','tests/acceptance',
        'tests/system_upgrade/test_classrooms_postgres.py','tests/test_infrastructure.py','tests/test_public_demo_deployment.py','tests/system_upgrade/test_packaging.py',
        '--basetemp',(Join-Path $OutputDirectory 'pytest'),'-o',"cache_dir=$OutputDirectory/pytest-cache",'-r','a')
    Invoke-Check 'edge-tests' 'uv' @('run','--locked','--all-groups','pytest','--tb=short','edge/tests',
        '--basetemp',(Join-Path $OutputDirectory 'edge-pytest'),'-o',"cache_dir=$OutputDirectory/pytest-cache",'-r','s')
    Invoke-Check 'spatial-tests' 'uv' @('run','--locked','python','-m','unittest','discover','-s','packages/spatial/tests','-p','test_*.py','-v')
    Push-Location frontend
    try {
        Invoke-Check 'frontend-dependencies' 'npm' @('ci')
        Invoke-Check 'frontend-format' 'npm' @('run','format:check')
        Invoke-Check 'frontend-tests' 'npm' @('test')
        Invoke-Check 'frontend-build' 'npm' @('run','build','--','--outDir',(Join-Path $OutputDirectory 'frontend-dist'))
    } finally { Pop-Location }
    Write-Host 'Local software checks passed. Review skip summaries; physical devices and remote CI are separate gates.'
} finally {
    if ($Started) { docker compose -p $ProjectName -f compose.test.yaml down --volumes *> (Join-Path $OutputDirectory 'postgres-stop.log') }
    foreach ($Name in $Names) { [Environment]::SetEnvironmentVariable($Name, $Previous[$Name], 'Process') }
}
