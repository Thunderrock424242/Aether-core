$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path (Join-Path $ScriptDir '..')
$SidecarDir = Join-Path $RootDir 'aether_sidecar'
$VenvDir = Join-Path $SidecarDir '.venv'

Set-Location $SidecarDir

if (-not (Test-Path $VenvDir)) {
    python -m venv .venv
}

$ActivateScript = Join-Path $VenvDir 'Scripts\Activate.ps1'
if (-not (Test-Path $ActivateScript)) {
    throw "Could not find virtual environment activation script at $ActivateScript"
}

. $ActivateScript

$SkipInstall = if ($env:AETHER_SKIP_DEV_INSTALL) { $env:AETHER_SKIP_DEV_INSTALL } else { 'false' }
if ($SkipInstall -ne 'true') {
    Write-Host 'Installing sidecar in editable mode (set AETHER_SKIP_DEV_INSTALL=true to skip)...'
    python -m pip install --disable-pip-version-check -e '.[dev]'
}
else {
    Write-Host 'Skipping editable install because AETHER_SKIP_DEV_INSTALL=true.'
}

$HostName = if ($env:AETHER_HOST) { $env:AETHER_HOST } else { '127.0.0.1' }
$Port = if ($env:AETHER_PORT) { $env:AETHER_PORT } else { '8765' }
$Reload = if ($env:AETHER_DEV_RELOAD) { $env:AETHER_DEV_RELOAD } else { 'true' }

if ($Reload -eq 'true') {
    Write-Host "Starting uvicorn with reload on http://${HostName}:${Port} ..."
    python -m uvicorn aether_sidecar.app:app --host $HostName --port $Port --reload
}
else {
    Write-Host "Starting sidecar on http://${HostName}:${Port} without reload ..."
    python run.py
}
