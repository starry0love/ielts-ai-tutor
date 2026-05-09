$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
Set-Location $backend

$pythonCandidates = @(
  ".\.packaging-venv\Scripts\python.exe",
  ".\.venv\Scripts\python.exe",
  "python",
  "py"
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

if (-not (Test-Path ".\.packaging-venv")) {
  & $python -m venv .\.packaging-venv
}

$venvPython = ".\.packaging-venv\Scripts\python.exe"
$pyInstaller = ".\.packaging-venv\Scripts\pyinstaller.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt pyinstaller

$distExe = Join-Path $backend "dist\ielts-backend.exe"
$buildDir = Join-Path $backend "build\ielts-backend"
$specFile = Join-Path $backend "ielts-backend.spec"

if (Test-Path $distExe) {
  Remove-Item -LiteralPath $distExe -Force
}

if (Test-Path $buildDir) {
  Remove-Item -LiteralPath $buildDir -Recurse -Force
}

if (Test-Path $specFile) {
  Remove-Item -LiteralPath $specFile -Force
}

$pyInstallerArgs = @(
  "--clean",
  "--noconfirm",
  "--onefile",
  "--name",
  "ielts-backend",
  "--paths",
  ".",
  "--paths",
  ".\.deps",
  "--hidden-import",
  "app.main",
  "--collect-submodules",
  "app"
)

if (Test-Path ".\app\prompts") {
  $pyInstallerArgs += @("--add-data", "app\prompts;app\prompts")
}

if (Test-Path ".\app\knowledge") {
  $pyInstallerArgs += @("--add-data", "app\knowledge;app\knowledge")
}

$pyInstallerArgs += "run_backend.py"

& $pyInstaller @pyInstallerArgs

Write-Host "Backend exe built at backend\dist\ielts-backend.exe"
