# PowerShell script to run tests with learning file reference
# Usage: .\run_tc.ps1 -TcRange "001-012" -Env qa -Headless

param(
    [Parameter(Mandatory=$true)]
    [string]$TcRange,
    
    [Parameter(Mandatory=$false)]
    [string]$Env = "qa",
    
    [Parameter(Mandatory=$false)]
    [switch]$Headless = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$Headed

    ,
    [Parameter(Mandatory=$false)]
    [int]$Workers = 2
)

# If -Headed is specified, override -Headless
if ($Headed) {
    $Headless = $false
}

# Get workspace root
$WorkspaceRoot = Split-Path -Parent $PSScriptRoot
Set-Location $WorkspaceRoot

# Ensure venv is activated
$VenvPath = Join-Path $WorkspaceRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    & $VenvPath
} else {
    Write-Host "❌ Virtual environment not found at $VenvPath" -ForegroundColor Red
    exit 1
}

# Run the helper script
$HelperScript = Join-Path $WorkspaceRoot "run_tests_with_learning.py"
if (Test-Path $HelperScript) {
    $HeadlessFlag = if ($Headless) { "--headless" } else { "--headed" }
    & python.exe $HelperScript --tc-range $TcRange --env $Env $HeadlessFlag --workers $Workers
} else {
    Write-Host "❌ Helper script not found at $HelperScript" -ForegroundColor Red
    exit 1
}
