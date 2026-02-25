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
pip install -e '.[dev]'

$HostName = if ($env:AETHER_HOST) { $env:AETHER_HOST } else { '127.0.0.1' }
$Port = if ($env:AETHER_PORT) { $env:AETHER_PORT } else { '8765' }
$Reload = if ($env:AETHER_DEV_RELOAD) { $env:AETHER_DEV_RELOAD } else { 'true' }

if ($Reload -eq 'true') {
    python -m uvicorn aether_sidecar.app:app --host $HostName --port $Port --reload
}
else {
    python run.py
}
