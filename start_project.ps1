$root = Get-Location
Write-Host "Starting MarketPulse from $root"

# Start Backend (Port 8000)
# Navigates to backend, activates venv, runs python main.py
$backendVenv = Join-Path $root "backend\venv\Scripts\Activate.ps1"
$rootVenv = Join-Path $root "venv\Scripts\Activate.ps1"
$venvActivate = $null
if (Test-Path $backendVenv) {
    $venvActivate = $backendVenv
} elseif (Test-Path $rootVenv) {
    $venvActivate = $rootVenv
}

$activateCmd = if ($venvActivate) { ". '$venvActivate';" } else { "Write-Host 'WARNING: venv not found; using system Python.';" }
$backendCommand = "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process; cd '$root\backend'; $activateCmd python server.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $backendCommand }" -WindowStyle Normal

# Start Frontend (Port 3001)
# Navigates to frontend, runs npm run dev
$frontendCommand = "cd '$root\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& { $frontendCommand }" -WindowStyle Normal

Write-Host "Services are launching..."
