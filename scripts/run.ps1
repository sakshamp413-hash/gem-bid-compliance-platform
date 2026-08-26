# ---- GeM Bid Compliance Platform: dev shortcuts (Windows) ----
# Usage:  scripts\run.ps1 seed | server | web | test | all

param([string]$Action = "all")

$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"

function Seed {
  & $Py "$Root\data\generate.py"
  Push-Location "$Root\backend"
  & "..\.venv\Scripts\python.exe" -m app.seed
  Pop-Location
}

function Server {
  Push-Location "$Root\backend"
  & "..\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
  Pop-Location
}

function Web {
  Push-Location "$Root\frontend"
  npm run dev
  Pop-Location
}

function Tests {
  Push-Location "$Root\backend"
  & "..\.venv\Scripts\python.exe" -m pytest tests -q
  Pop-Location
  Push-Location "$Root\frontend"
  npm test
  Pop-Location
}

switch ($Action) {
  "seed" { Seed }
  "server" { Server }
  "web" { Web }
  "test" { Tests }
  "all" { Seed; Write-Host "`nBackend:  cd backend; uvicorn app.main:app --port 8000`nFrontend: cd frontend; npm run dev" }
  default { Write-Host "Usage: run.ps1 [seed|server|web|test|all]" }
}