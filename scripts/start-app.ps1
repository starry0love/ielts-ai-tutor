$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendScript = Join-Path $PSScriptRoot "start-backend.ps1"
$frontendScript = Join-Path $PSScriptRoot "start-frontend.ps1"
$electronScript = Join-Path $PSScriptRoot "start-electron.ps1"

Write-Host "Starting IELTS AI Tutor..."

Write-Host "Checking backend version..."
Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
  "-ExecutionPolicy", "Bypass",
  "-File", $backendScript
)
Start-Sleep -Seconds 5

try {
  $response = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -TimeoutSec 2 -UseBasicParsing
  if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
    Write-Host "Frontend already running."
  }
} catch {
  Write-Host "Starting frontend in a background window..."
  Start-Process powershell.exe -WindowStyle Hidden -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-NoExit",
    "-File", $frontendScript
  )
  Start-Sleep -Seconds 5
}

Write-Host "Opening desktop app..."
Start-Process powershell.exe -ArgumentList @(
  "-ExecutionPolicy", "Bypass",
  "-NoExit",
  "-File", $electronScript
)

Write-Host "Done. If the desktop window does not appear, open http://127.0.0.1:5173 in your browser."
