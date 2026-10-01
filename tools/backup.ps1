param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (Test-Path $Destination) { throw "Refusing to overwrite $Destination" }
$Parent = Split-Path $Destination -Parent
if ($Parent) { New-Item -ItemType Directory -Path $Parent -Force | Out-Null }
$Destination = [System.IO.Path]::GetFullPath($Destination)
$Partial = $Destination + '.partial.' + [guid]::NewGuid().ToString('N')
$Temp = '/tmp/carbentra-backup-' + [guid]::NewGuid().ToString('N') + '.dump'
try {
    docker compose exec -T --interactive=false db sh -c 'umask 077; exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom -f "$1"' sh $Temp
    if ($LASTEXITCODE -ne 0) { throw 'pg_dump failed' }
    $Container = (docker compose ps -q db).Trim()
    if (-not $Container) { throw 'Database container not found' }
    docker cp "${Container}:$Temp" $Partial
    if ($LASTEXITCODE -ne 0) { throw 'Copying database backup failed' }
    if ((Get-Item $Partial).Length -eq 0) { throw 'Backup is empty' }
    # File.Move refuses an existing destination, including a file created during the dump.
    [System.IO.File]::Move($Partial, $Destination)
    (Get-FileHash -Algorithm SHA256 $Destination).Hash | Set-Content "$Destination.sha256"
    Write-Host "Saved binary database snapshot to $Destination"
} finally {
    if (Test-Path $Partial) { Remove-Item -LiteralPath $Partial }
    docker compose exec -T --interactive=false db rm -f $Temp
}
