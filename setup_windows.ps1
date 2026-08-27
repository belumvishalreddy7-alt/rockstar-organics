# Rockstar Organics - Windows setup script
# Run from the repository root in PowerShell: .\setup_windows.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== Rockstar Organics setup ==" -ForegroundColor Green

Set-Location "$root\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv .venv
} else {
    Write-Host "Virtual environment already exists, reusing it."
}

Write-Host "Activating virtual environment..."
& "$root\backend\.venv\Scripts\Activate.ps1"

Write-Host "Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created backend\.env from .env.example - review and edit it." -ForegroundColor Yellow
}

Write-Host "Running environment doctor..."
python -m scripts.doctor

Write-Host "Applying database migrations..."
python -m scripts.upgrade_database

Write-Host "Seeding required (non-business) data..."
python -m scripts.seed_required_data

Write-Host ""
Write-Host "Backend setup complete." -ForegroundColor Green
Write-Host "Next: python -m scripts.create_superadmin --email you@example.com --name `"Your Name`""

Set-Location "$root\frontend"
Write-Host "Installing frontend dependencies..."
npm install

Write-Host ""
Write-Host "Setup complete. Use start_windows.ps1 to run both servers." -ForegroundColor Green
Set-Location $root
