param(
    [Parameter(Mandatory=$true)][string]$OutputDirectory,
    [ValidatePattern('^carbentra-[a-z0-9-]+$')][string]$ProjectName='carbentra-production-test',
    [ValidateRange(1024,65535)][int]$HttpPort=18081,
    [ValidateRange(1024,65535)][int]$HttpsPort=18443,
    [ValidateRange(1024,65535)][int]$MqttPort=8884
)
$ErrorActionPreference='Stop'
$Root=Split-Path $PSScriptRoot -Parent
Set-Location $Root
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$Fixture=Join-Path $OutputDirectory 'production-fixture'
$Overlay=Join-Path $OutputDirectory 'compose.fixture.yaml'
if(Test-Path -LiteralPath $Fixture){throw 'Fixture directory already exists; choose a new output directory'}
$Existing=docker ps -aq --filter "label=com.docker.compose.project=$ProjectName"
if($LASTEXITCODE -ne 0){throw 'Docker Desktop with Linux containers is required'}
if($Existing){throw "Project $ProjectName already exists; choose a separate disposable name"}
function Invoke-Check([string]$Name,[string]$Program,[string[]]$Arguments){
    $Log=Join-Path $OutputDirectory "$Name.log"
    & $Program @Arguments *> $Log
    if($LASTEXITCODE -ne 0){Get-Content $Log -Tail 50; throw "$Name failed; see $Log"}
    Write-Host "$Name passed"
}
$Names=@('CARBENTRA_IMAGE_TAG','CARBENTRA_SECRETS_DIR','CARBENTRA_TRANSPORT_DIR','CARBENTRA_ALLOWED_ORIGINS',
    'CARBENTRA_TRUSTED_HOSTS','CARBENTRA_ADMIN_USERNAME','CARBENTRA_ADAPTER_ALLOWED_DEVICE_IDS','PYTHONUTF8','TEMP','TMP')
$Previous=@{}
foreach($Name in $Names){$Previous[$Name]=[Environment]::GetEnvironmentVariable($Name,'Process')}
$Compose=@('compose','-p',$ProjectName,'-f','compose.prod.yaml','-f','compose.bootstrap.yaml','-f','compose.transport.yaml','-f',$Overlay,'--profile','transport')
$Started=$false
try{
    $env:TEMP=$OutputDirectory; $env:TMP=$OutputDirectory; $env:PYTHONUTF8='1'
    if(-not(Test-Path .venv)){Invoke-Check 'venv' 'uv' @('venv','--python','3.12','.venv')}
    Invoke-Check 'dependencies' 'uv' @('sync','--locked','--all-groups')
    Invoke-Check 'fixture' 'uv' @('run','--locked','--all-groups','python','tests/deployment/create_fixture.py',
        '--directory',$Fixture,'--mqtt-port',"$MqttPort",'--disposable-fixture')
    @"
services:
  web:
    ports: !override ["127.0.0.1:${HttpPort}:8080"]
  broker:
    ports: !override ["127.0.0.1:${MqttPort}:8883"]
  platform-tls:
    ports: ["127.0.0.1:${HttpsPort}:8443"]
    networks: [private, transport, broker_ingress]
"@ | Set-Content $Overlay -Encoding utf8NoBOM
    $env:CARBENTRA_IMAGE_TAG='local'
    $env:CARBENTRA_SECRETS_DIR=$Fixture.Replace('\','/')
    $env:CARBENTRA_TRANSPORT_DIR=$env:CARBENTRA_SECRETS_DIR
    $env:CARBENTRA_ALLOWED_ORIGINS='["https://localhost:'+ $HttpsPort +'"]'
    $env:CARBENTRA_TRUSTED_HOSTS='["localhost","127.0.0.1","api"]'
    $env:CARBENTRA_ADMIN_USERNAME='container-test-admin'
    $env:CARBENTRA_ADAPTER_ALLOWED_DEVICE_IDS='["VIRTUAL-QA-01"]'
    $Started=$true
    Invoke-Check 'production-start' 'docker' ($Compose+@('up','-d','--wait','--wait-timeout','180'))
    Invoke-Check 'https-smoke' 'uv' @('run','--locked','--all-groups','python','tests/deployment/production_smoke.py',
        '--base-url',"https://localhost:$HttpsPort",'--cleartext-url',"http://localhost:$HttpPort",'--ca-file',(Join-Path $Fixture 'platform-ca.crt'),
        '--password-file',(Join-Path $Fixture 'admin_password'),'--disposable-fixture')
    Invoke-Check 'mqtt-security' 'uv' @('run','--locked','--all-groups','python','tests/deployment/mqtt_security.py',
        '--fixture-config',(Join-Path $Fixture 'mqtt-fixture.json'),'--disposable-fixture')
    Write-Host 'Disposable production-mode HTTPS and broker checks passed; no physical dispatch was enabled.'
}finally{
    if($Started){docker @Compose down --volumes *> (Join-Path $OutputDirectory 'production-stop.log')}
    # Resolve the exact generated secret directory before recursive deletion.
    if(Test-Path -LiteralPath $Fixture){
        $Resolved=(Resolve-Path -LiteralPath $Fixture).Path
        if($Resolved -ne [IO.Path]::GetFullPath((Join-Path $OutputDirectory 'production-fixture'))){throw 'Unexpected fixture path'}
        Remove-Item -LiteralPath $Resolved -Recurse -Force
    }
    foreach($Name in $Names){[Environment]::SetEnvironmentVariable($Name,$Previous[$Name],'Process')}
}
