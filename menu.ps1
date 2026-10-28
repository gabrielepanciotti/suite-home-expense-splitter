# menu.ps1 — launcher HomeExpenseSplitter (dev)
# Backend FastAPI :10009  ·  Frontend Vite :3343  ·  CLI
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
$env:PYTHONPATH = (Join-Path $root "backend")

function Start-Backend {
    Write-Host "Backend FastAPI -> http://localhost:10009 (Ctrl+C per fermare)" -ForegroundColor Cyan
    $env:PYTHONUTF8 = "1"
    & $py -m uvicorn home_expense_splitter_backend.app:app --port 10009 --reload
}

function Start-Frontend {
    Write-Host "Frontend Vite -> http://localhost:3343 (Ctrl+C per fermare)" -ForegroundColor Cyan
    Push-Location (Join-Path $root "frontend")
    if (-not (Test-Path "node_modules")) { npm install }
    npm run dev
    Pop-Location
}

function Start-Bot {
    Write-Host "Bot Telegram HomeExpenseSplitter (Ctrl+C per fermare)" -ForegroundColor Cyan
    $env:PYTHONUTF8 = "1"
    & $py -m home_expense_splitter_bot.bot
}

function Start-Both {
    # Backend in una nuova finestra, frontend in questa.
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$PSCommandPath' backend"
    Start-Frontend
}

switch ($args[0]) {
    "backend"  { Start-Backend; return }
    "frontend" { Start-Frontend; return }
    "both"     { Start-Both; return }
    "bot"      { Start-Bot; return }
    "split"    { $env:PYTHONUTF8 = "1"; & $py -m home_expense_splitter.cli split; return }
    "excel"    { $env:PYTHONUTF8 = "1"; & $py -m home_expense_splitter.cli export-excel; return }
}

Write-Host ""
Write-Host "  HomeExpenseSplitter — dev menu" -ForegroundColor Green
Write-Host "  ---------------------"
Write-Host "  1) Backend  (FastAPI :10009)"
Write-Host "  2) Frontend (Vite :3343)"
Write-Host "  3) Entrambi (backend in nuova finestra + frontend qui)"
Write-Host "  4) CLI split   (saldo divisione)"
Write-Host "  5) CLI export-excel"
Write-Host "  6) Bot Telegram"
Write-Host ""
$c = Read-Host "Scelta"
switch ($c) {
    "1" { Start-Backend }
    "2" { Start-Frontend }
    "3" { Start-Both }
    "4" { $env:PYTHONUTF8 = "1"; & $py -m home_expense_splitter.cli split }
    "5" { $env:PYTHONUTF8 = "1"; & $py -m home_expense_splitter.cli export-excel }
    "6" { Start-Bot }
    default { Write-Host "Scelta non valida." -ForegroundColor Yellow }
}
