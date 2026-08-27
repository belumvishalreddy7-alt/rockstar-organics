# Rockstar Organics - Windows start script
# Starts the backend (no-reload, to avoid known Windows uvicorn --reload
# subprocess issues) and the frontend dev server in separate windows.

$root = $PSScriptRoot

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\backend'; & .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 127.0.0.1 --port 8000"

Start-Sleep -Seconds 2

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\frontend'; npm run dev"

Write-Host ""
Write-Host "Two PowerShell windows have been opened for backend and frontend." -ForegroundColor Yellow
Write-Host "If port 8000 is already in use, stop the other process or edit the port in this script."
