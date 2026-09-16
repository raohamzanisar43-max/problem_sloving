# Novu Opportunity Radar — Development Environment Setup Script (Windows PowerShell)
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Novu Opportunity Radar — Dev Setup" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

# 1. Backend Python Dependencies
Write-Host "`n[1/4] Installing Python requirements..." -ForegroundColor Green
Set-Location $BackendDir
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  Created backend/.env from .env.example" -ForegroundColor Yellow
}
python -m pip install -r requirements.txt

# 2. Database Migrations
Write-Host "`n[2/4] Applying database migrations..." -ForegroundColor Green
python manage.py migrate

# 3. Seed Demo Data
Write-Host "`n[3/4] Seeding demonstration dataset & users..." -ForegroundColor Green
python manage.py seed_demo

# 4. Frontend Node Dependencies
Write-Host "`n[4/4] Setting up frontend dependencies..." -ForegroundColor Green
Set-Location $FrontendDir
npm install

Set-Location $ProjectRoot
Write-Host "`n Setup complete! Run .\scripts\demo_run.ps1 to start services." -ForegroundColor Cyan
