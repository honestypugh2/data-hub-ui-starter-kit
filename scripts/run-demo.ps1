<#
.SYNOPSIS
    Starts the starter-kit demo app (backend + frontend).

.DESCRIPTION
    1. Launches the FastAPI mock server on port 8000
    2. Launches the Vite dev server in demo mode on port 3000

    Press Ctrl+C to stop both servers.

.EXAMPLE
    .\scripts\run-demo.ps1
#>

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DemoDir    = Join-Path $Root "app\demo"
$FrontDir   = Join-Path $Root "app\frontend"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starter Kit Demo App - Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Preflight checks ---
if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] Python venv not found at .venv" -ForegroundColor Red
    Write-Host "  Run:  python -m venv .venv && .venv\Scripts\Activate.ps1 && uv add fastapi uvicorn" -ForegroundColor Yellow
    exit 1
}

$npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
if (-not $npmPath) {
    # Refresh PATH in case npm was recently installed
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
}
if (-not $npmPath) {
    Write-Host "[ERROR] npm is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# --- Ensure frontend node_modules ---
if (-not (Test-Path (Join-Path $FrontDir "node_modules"))) {
    Write-Host "[SETUP] Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location $FrontDir
    cmd /c "npm install"
    Pop-Location
}

# --- Start backend (uvicorn) ---
Write-Host "[START] Demo backend  -> http://localhost:8000" -ForegroundColor Yellow
Write-Host "[START] API docs      -> http://localhost:8000/docs" -ForegroundColor Yellow
$backendProc = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000", "--reload" `
    -WorkingDirectory $DemoDir `
    -PassThru `
    -WindowStyle Normal

# --- Start frontend (vite demo mode) ---
Write-Host "[START] Demo frontend -> http://localhost:3000" -ForegroundColor Yellow
$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run start:demo" `
    -WorkingDirectory $FrontDir `
    -PassThru `
    -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Both servers are starting!" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Press ENTER to stop both servers." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# --- Wait for user to press Enter ---
Read-Host "Press Enter to stop"

# --- Cleanup ---
Write-Host "Shutting down..." -ForegroundColor Yellow

if (-not $backendProc.HasExited) {
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
}
if (-not $frontendProc.HasExited) {
    Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    # Also kill any child node processes spawned by npm
    Get-Process -Name "node" -ErrorAction SilentlyContinue |
        Where-Object { $_.StartTime -ge $frontendProc.StartTime } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

Write-Host "Demo stopped." -ForegroundColor Green
