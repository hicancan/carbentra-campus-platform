param([Parameter(Mandatory=$true)][string]$Backup)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path $Backup -PathType Leaf)) { throw 'Backup file does not exist' }
$Name = 'carbentra_restore_check_' + [guid]::NewGuid().ToString('N')
$Temp = '/tmp/' + $Name + '.dump'
$Container = (docker compose ps -q db).Trim()
if (-not $Container) { throw 'Database container not found' }
$Created = $false
try {
    docker cp $Backup "${Container}:$Temp"
    if ($LASTEXITCODE -ne 0) { throw 'Copying backup failed' }
    docker compose exec -T --interactive=false db chmod 0600 $Temp
    if ($LASTEXITCODE -ne 0) { throw 'Could not restrict the temporary container dump' }
    docker compose exec -T --interactive=false db sh -c 'createdb -U "$POSTGRES_USER" --template=template0 "$1"' sh $Name
    if ($LASTEXITCODE -ne 0) { throw 'Creating isolated restore database failed' }
    $Created = $true
    docker compose exec -T --interactive=false db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error "$2"' sh $Name $Temp
    if ($LASTEXITCODE -ne 0) { throw 'Restore validation failed' }
    docker compose exec -T --interactive=false db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -c "SELECT version_num FROM alembic_version;"' sh $Name
    if ($LASTEXITCODE -ne 0) { throw 'Restored migration revision could not be read' }
    docker compose exec -T --interactive=false db sh -c 'psql -U carbentra -d "$1" -v ON_ERROR_STOP=1 -c "SELECT current_user, count(*) AS restored_devices FROM devices;" -c "SELECT count(*) AS restored_reports FROM reports;"' sh $Name
    if ($LASTEXITCODE -ne 0) { throw 'Application role cannot read restored data' }
    Write-Host 'Restore completed in an isolated temporary database'
} finally {
    if ($Created) { docker compose exec -T --interactive=false db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists "$1"' sh $Name }
    docker compose exec -T --interactive=false db rm -f $Temp
}
