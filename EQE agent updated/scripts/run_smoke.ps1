# run_smoke.ps1 — Quick smoke test launcher
# Usage: .\run_smoke.ps1 [-Env qa] [-Headed]
param(
    [string]$Env     = "qa",
    [switch]$Headed  = $false
)

$ErrorActionPreference = "Stop"
$rootDir = $PSScriptRoot
$python  = Join-Path $rootDir ".venv\Scripts\python.exe"
$pytest  = Join-Path $rootDir ".venv\Scripts\pytest.exe"

if (-not (Test-Path $pytest)) {
    Write-Error "pytest not found. Run .\setup_env.ps1 first."
    exit 1
}

Write-Host "=== DocuChat QA — Smoke Tests (env=$Env) ===" -ForegroundColor Cyan

# Pre-run policy check
& $python -m utils.policy_guard
if ($LASTEXITCODE -ne 0) {
    Write-Error "Policy violations detected. Aborting."
    exit $LASTEXITCODE
}

$args = @("-m", "smoke", "--env=$Env", "-v", "--tb=short")
if ($Headed) { $args += "--headless=false" }

& $pytest @args
$exit = $LASTEXITCODE

if ($exit -eq 0) {
    Write-Host "Smoke tests PASSED." -ForegroundColor Green
} else {
    Write-Host "Smoke tests FAILED (exit $exit)." -ForegroundColor Red
}

exit $exit
