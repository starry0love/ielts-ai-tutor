$ErrorActionPreference = "Continue"

Write-Host "IELTS AI Tutor environment check"
Write-Host ""

Write-Host "Node.js:"
where.exe node
node --version
Write-Host ""

Write-Host "npm.cmd:"
where.exe npm.cmd
npm.cmd --version
Write-Host ""

Write-Host "Python:"
where.exe python
if ($LASTEXITCODE -eq 0) {
  python --version
} else {
  Write-Host "python not found. Install Python 3.11+ or add it to PATH."
}
Write-Host ""

Write-Host "Python launcher:"
where.exe py
if ($LASTEXITCODE -eq 0) {
  py --version
} else {
  Write-Host "py launcher not found."
}

