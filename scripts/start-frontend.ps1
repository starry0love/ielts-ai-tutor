$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$desktop = Join-Path $root "apps\desktop"
Set-Location $desktop

try {
  $response = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing
  if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
    Write-Host "Frontend is already running at http://127.0.0.1:5173"
    exit 0
  }
} catch {
}

if (-not (Test-Path "node_modules")) {
  npm.cmd install
}

npm.cmd run dev
