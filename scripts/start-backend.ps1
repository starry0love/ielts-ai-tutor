$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
Set-Location $backend

try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
  if ($health.status -eq "ok") {
    $today = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/plans/today" -TimeoutSec 2
    if ($today.PSObject.Properties.Name -contains "needs_onboarding") {
      Write-Host "Backend is already running at http://127.0.0.1:8000"
      Write-Host "You can refresh Electron with Ctrl + R."
      exit 0
    }
    Write-Host "A stale backend is running on port 8000. Restarting it with the current source..."
    $portOwner = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($portOwner) {
      Stop-Process -Id $portOwner.OwningProcess -Force
      Start-Sleep -Seconds 1
    }
  }
} catch {
}

$portInUse = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portInUse) {
  Write-Host "Port 8000 is already in use, but the IELTS backend health check did not respond."
  Write-Host "Close the process using port 8000, or restart the backend from the existing terminal."
  exit 1
}

$pythonCandidates = @(
  ".\.venv\Scripts\python.exe",
  "python",
  "py",
  "C:\Users\Starry\Documents\Codex\2026-05-06\codex-claude-code-claude-md-codex\codex-python312\tools\python.exe"
)

$python = $null
foreach ($candidate in $pythonCandidates) {
  try {
    & $candidate --version *> $null
    if ($LASTEXITCODE -eq 0) {
      $python = $candidate
      break
    }
  } catch {
  }
}

if (-not $python) {
  throw "No usable Python found. Install Python 3.11+ or add it to PATH."
}

if (-not (Test-Path ".deps")) {
  & $python -m pip install --target .\.deps -r requirements.txt
}

$env:PYTHONPATH = (Resolve-Path ".\.deps").Path
& $python .\run_backend.py
