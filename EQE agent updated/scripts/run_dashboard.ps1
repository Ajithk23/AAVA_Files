# run_dashboard.ps1 - Reliable Streamlit dashboard launcher
# Usage: .\scripts\run_dashboard.ps1 [-Port 8501]
param(
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"
$rootDir     = Split-Path $PSScriptRoot -Parent
$python      = Join-Path $rootDir ".venv\Scripts\python.exe"
$dashboardPy = Join-Path $rootDir "dashboard.py"

if (-not (Test-Path $python)) {
    Write-Error "Python venv not found. Run .\setup_env.ps1 first."
    exit 1
}

# Kill any existing Streamlit process on the target port.
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Port $Port already in use - stopping existing process..." -ForegroundColor Yellow
    $pid_ = (Get-NetTCPConnection -LocalPort $Port -State Listen).OwningProcess | Select-Object -First 1
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Write-Host "=== Starting DocuChat Dashboard on http://localhost:$Port ===" -ForegroundColor Cyan

# Start Streamlit using a background job so paths with spaces work correctly.
$job = Start-Job -ScriptBlock {
    param($py, $pyFile, $port, $dir)
    Set-Location $dir
    & $py -m streamlit run $pyFile `
        "--server.port=$port" `
        "--server.headless=true" `
        "--server.runOnSave=false" `
        "--browser.gatherUsageStats=false" `
        "--server.fileWatcherType=none"
} -ArgumentList $python, $dashboardPy, $Port, $rootDir

# Wait until the port is open (max 30 seconds).
$maxWait = 30
$waited  = 0
Write-Host "Waiting for server to start..." -NoNewline
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    $waited++
    Write-Host "." -NoNewline
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Write-Host " Ready!" -ForegroundColor Green
        break
    }
    # Check if the job failed early.
    if ($job.State -eq "Failed" -or $job.State -eq "Completed") {
        Write-Host ""
        Write-Warning "Streamlit job ended unexpectedly. Output:"
        Receive-Job $job
        exit 1
    }
}

if ($waited -ge $maxWait) {
    Write-Host ""
    Write-Warning "Server did not start within $maxWait seconds. Job output:"
    Receive-Job $job -ErrorAction SilentlyContinue
    exit 1
}

# Open browser.
Start-Process "http://localhost:$Port"
Write-Host "Dashboard open at http://localhost:$Port" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the dashboard server."

# Stream job output until the user stops it.
try {
    while ($job.State -eq "Running") {
        $output = Receive-Job $job -ErrorAction SilentlyContinue
        if ($output) { $output | ForEach-Object { Write-Host $_ } }
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}
