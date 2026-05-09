$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$desktop = Join-Path $root "apps\desktop"
$backendExe = Join-Path $root "backend\dist\ielts-backend.exe"

Write-Host "Building backend executable..."
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build-backend-exe.ps1")

if (-not (Test-Path $backendExe)) {
  throw "Backend exe was not created at $backendExe"
}

Set-Location $desktop

if (-not (Test-Path "node_modules")) {
  npm.cmd install
}

if (-not (Test-Path "node_modules\electron-builder")) {
  npm.cmd install
}

if (Test-Path "dist") {
  Remove-Item -LiteralPath "dist" -Recurse -Force
}

if (Test-Path "dist-electron") {
  Remove-Item -LiteralPath "dist-electron" -Recurse -Force
}

Write-Host "Building frontend..."
npm.cmd run build

Write-Host "Packaging Windows portable app..."
$env:CSC_IDENTITY_AUTO_DISCOVERY = "false"
npm.cmd run pack:portable

Write-Host "Portable app output is under apps\desktop\dist-electron"
