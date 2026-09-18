# run_regression.ps1 — Full regression suite launcher
# Usage: .\run_regression.ps1 [-Env qa] [-Feature chat|file_handling|prompt_library] [-Headed]
param(
    [string]$Env     = "qa",
    [string]$Feature = "",
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

Write-Host "=== DocuChat QA — Regression Tests (env=$Env) ===" -ForegroundColor Cyan

& $python -m utils.policy_guard
if ($LASTEXITCODE -ne 0) {
    Write-Error "Policy violations detected. Aborting."
    exit $LASTEXITCODE
}

$pytestArgs = @("-m", "regression", "--env=$Env", "-v", "--tb=long")
if ($Headed) { $pytestArgs += "--headless=false" }

if ($Feature -ne "") {
    $featurePath = Join-Path $rootDir "tests\web\$Feature"
    if (-not (Test-Path $featurePath)) {
        Write-Error "Feature folder not found: $featurePath"
        exit 1
    }
    $pytestArgs += $featurePath
}

& $pytest @pytestArgs
$exit = $LASTEXITCODE

if ($exit -eq 0) {
    Write-Host "Regression tests PASSED." -ForegroundColor Green
} else {
    Write-Host "Regression tests FAILED (exit $exit)." -ForegroundColor Red
}

exit $exit
