# DocuChat Framework Setup Script
# Run this once in PowerShell from the DocuChat folder:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\setup_env.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "=== DocuChat Framework Setup ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host ""
# ── Step 1: Check Python (3.12 preferred) ────────────────────────────────────
Write-Host "[1/6] Checking Python (3.12 preferred)..." -ForegroundColor Yellow

$preferredVersion = [version]"3.12"
$minimumSupportedVersion = [version]"3.10"

$pyExe = $null
$detectedVersion = $null

$pythonCandidates = @(
    @{ cmd = "py"; args = @("-3.12") },
    @{ cmd = "python3.12"; args = @() },
    @{ cmd = "python312"; args = @() },
    @{ cmd = "py"; args = @() },
    @{ cmd = "python"; args = @() },
    @{ cmd = "python3"; args = @() }
)

$bestFallbackExe = $null
$bestFallbackVersion = $null

foreach ($candidate in $pythonCandidates) {
    try {
        $output = & $candidate.cmd @($candidate.args + @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{sys.executable}')")) 2>$null
        if (-not $output) { continue }

        $line = ($output | Select-Object -Last 1).Trim()
        if (-not $line.Contains("|")) { continue }

        $parts = $line.Split("|", 2)
        $versionText = $parts[0].Trim()
        $exePath = $parts[1].Trim()
        $version = [version]$versionText

        if ($version -eq $preferredVersion) {
            $pyExe = $exePath
            $detectedVersion = $version
            break
        }

        if ($version -ge $minimumSupportedVersion) {
            if (-not $bestFallbackVersion -or $version -gt $bestFallbackVersion) {
                $bestFallbackVersion = $version
                $bestFallbackExe = $exePath
            }
        }
    } catch {}
}

if (-not $pyExe -and $bestFallbackExe) {
    $pyExe = $bestFallbackExe
    $detectedVersion = $bestFallbackVersion
    Write-Host "Python 3.12 not found. Using compatible Python $detectedVersion." -ForegroundColor Yellow
}

if (-not $pyExe) {
    Write-Host ""
    throw "No compatible Python found (requires 3.10+). Install Python and rerun setup_env.ps1."
}

Write-Host "Using Python $detectedVersion: $pyExe" -ForegroundColor Green
Write-Host ""
$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvPath) {
    Write-Host "Removing old .venv..."
    Remove-Item $venvPath -Recurse -Force
}

& $pyExe -m venv $venvPath
$venvPy = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"
Write-Host "Virtual environment created at $venvPath" -ForegroundColor Green
Write-Host ""

# ── Step 3: Install dependencies ──────────────────────────────────────────────
Write-Host "[3/6] Installing dependencies from requirements.txt..." -ForegroundColor Yellow

& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host "Dependencies installed." -ForegroundColor Green
Write-Host ""

# ── Step 4: Install Playwright Chromium ───────────────────────────────────────
Write-Host "[4/6] Installing Playwright Chromium browser..." -ForegroundColor Yellow

$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"
& $venvPy -m playwright install chromium

Write-Host "Playwright Chromium installed." -ForegroundColor Green
Write-Host ""

# ── Step 5: Update user PATH with new venv Scripts ───────────────────────────
Write-Host "[5/6] Updating user PATH..." -ForegroundColor Yellow

$venvScripts = Join-Path $venvPath "Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$venvScripts*") {
    [Environment]::SetEnvironmentVariable("Path", "$venvScripts;$userPath", "User")
    $env:Path = "$venvScripts;$env:Path"
    Write-Host "PATH updated. 'pytest' now works in new terminals." -ForegroundColor Green
} else {
    Write-Host "PATH already contains venv Scripts." -ForegroundColor Green
}
Write-Host ""

# ── Step 6: Run sample test ───────────────────────────────────────────────────
Write-Host "[6/6] Running sample test to verify setup..." -ForegroundColor Yellow
Write-Host ""

Set-Location $ProjectRoot
& $venvPy -m pytest tests/web/chat/test_chat_send_message.py::test_chat_send_message `
    --env=qa -v -n 0

Write-Host ""
Write-Host "=== Setup complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run tests:" -ForegroundColor White
Write-Host "  pytest tests/web/chat --env=qa -v -n 0" -ForegroundColor Gray
Write-Host "  pytest -m smoke --env=qa -n 0" -ForegroundColor Gray
Write-Host "  python run_tests.py --env qa --feature chat" -ForegroundColor Gray
Write-Host ""
