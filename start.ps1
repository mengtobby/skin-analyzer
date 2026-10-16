# One-command launcher: creates the Python venv and frontend build if needed, then starts
# the backend (which serves the dashboard) and opens it as an app window.
#   .\start.ps1                    # saved input (camera:0 on first run)
#   .\start.ps1 -Source camera:1   # another camera
#   .\start.ps1 -Dev               # Vite dev server with hot reload on http://localhost:5173
param(
    [string]$Source = "",
    [int]$Port = 8000,
    [switch]$Dev
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
$frontend = Join-Path $root "frontend"

function Find-Python312 {
    # MediaPipe wheels are tested on 3.12; prefer it explicitly.
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += , @("py", "-3.12") }
    if (Get-Command python3.12 -ErrorAction SilentlyContinue) { $candidates += , @("python3.12") }
    $pyenvRoot = Join-Path $env:USERPROFILE ".pyenv\pyenv-win\versions"
    if (Test-Path $pyenvRoot) {
        Get-ChildItem $pyenvRoot -Directory -Filter "3.12*" | ForEach-Object {
            $candidates += , @((Join-Path $_.FullName "python.exe"))
        }
    }
    $candidates += , @("python")
    foreach ($c in $candidates) {
        $exe = $c[0]; $extra = @($c | Select-Object -Skip 1)
        try { $ver = & $exe @extra -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null } catch { continue }
        if ($ver -eq "3.12") { return , $c }
    }
    throw "Python 3.12 not found. Install it (https://www.python.org/downloads/) and re-run."
}

if (-not (Test-Path $venvPy)) {
    $py = Find-Python312
    Write-Host "Creating Python 3.12 virtual environment (.venv)..."
    & $py[0] @($py | Select-Object -Skip 1) -m venv (Join-Path $root ".venv")
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r (Join-Path $root "backend\requirements.txt")
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    npm --prefix $frontend ci
}

$sourceArgs = @()
if ($Source) { $sourceArgs = @("--source", $Source) }

Push-Location (Join-Path $root "backend")
try {
    if ($Dev) {
        $vite = Start-Process -FilePath "npm.cmd" -ArgumentList "--prefix", $frontend, "run", "dev" -PassThru -NoNewWindow
        try { & $venvPy -m skin_analyzer @sourceArgs --port $Port }
        finally { if ($vite -and -not $vite.HasExited) { Stop-Process -Id $vite.Id -Force } }
    } else {
        if (-not (Test-Path (Join-Path $frontend "dist\index.html"))) {
            Write-Host "Building dashboard..."
            npm --prefix $frontend run build
        }
        & $venvPy -m skin_analyzer @sourceArgs --port $Port --open
    }
} finally {
    Pop-Location
}
