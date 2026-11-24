# One-command launcher: creates the Python venv, reinstalls dependencies when their lists
# change, rebuilds the dashboard when its sources are newer than the build, then starts the
# backend (which serves the dashboard) and opens it as an app window.
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

function Get-FileStamp([string]$Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

function Test-StampCurrent([string]$Source, [string]$StampFile) {
    # True when $StampFile records the current hash of $Source (deps already installed from it).
    # An empty stamp (interrupted write) reads as no output at all; "$(...)" turns that into "" = stale.
    (Test-Path -LiteralPath $StampFile) -and ("$(Get-Content -LiteralPath $StampFile -Raw)".Trim() -eq (Get-FileStamp $Source))
}

function Write-Stamp([string]$Source, [string]$StampFile) {
    Set-Content -LiteralPath $StampFile -Value (Get-FileStamp $Source) -Encoding ascii
}

function Invoke-Checked([string]$What, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$What failed (exit code $LASTEXITCODE)." }
}

function Test-DashboardStale([string]$Frontend) {
    # The build is stale when any shipped frontend input is newer than dist\index.html.
    # Test files are ignored: they do not change the built dashboard.
    $built = Join-Path $Frontend "dist\index.html"
    if (-not (Test-Path -LiteralPath $built)) { return $true }
    $builtAt = (Get-Item -LiteralPath $built).LastWriteTimeUtc
    $inputs = @(Get-ChildItem -LiteralPath (Join-Path $Frontend "src") -Recurse -File |
        Where-Object { $_.Name -notmatch '\.test\.tsx?$' })
    # Build inputs at the frontend root: index.html, the lockfile and every vite/tsconfig variant.
    $inputs += @(Get-ChildItem -LiteralPath $Frontend -File |
        Where-Object { $_.Name -in "index.html", "package-lock.json" -or $_.Name -like "vite.config.*" -or $_.Name -like "tsconfig*.json" })
    $publicDir = Join-Path $Frontend "public"
    if (Test-Path -LiteralPath $publicDir) { $inputs += @(Get-ChildItem -LiteralPath $publicDir -Recurse -File) }
    return [bool]($inputs | Where-Object { $_.LastWriteTimeUtc -gt $builtAt } | Select-Object -First 1)
}

if ($MyInvocation.InvocationName -eq '.') { return }  # dot-sourced: expose the helpers only

if (-not (Test-Path $venvPy)) {
    $py = Find-Python312
    Write-Host "Creating Python 3.12 virtual environment (.venv)..."
    Invoke-Checked "Creating the virtual environment" { & $py[0] @($py | Select-Object -Skip 1) -m venv (Join-Path $root ".venv") }
    Invoke-Checked "Upgrading pip" { & $venvPy -m pip install --upgrade pip }
}

# Reinstall whenever a dependency list changes (for example after a git pull).
$requirements = Join-Path $root "backend\requirements.txt"
$requirementsStamp = Join-Path $root ".venv\requirements.sha256"
if (-not (Test-StampCurrent $requirements $requirementsStamp)) {
    Write-Host "Installing Python dependencies..."
    Invoke-Checked "Installing Python dependencies" { & $venvPy -m pip install -r $requirements }
    Write-Stamp $requirements $requirementsStamp
}

$lockfile = Join-Path $frontend "package-lock.json"
$lockStamp = Join-Path $frontend "node_modules\.lockfile.sha256"
$installedLock = Join-Path $frontend "node_modules\.package-lock.json"
if (-not (Test-Path -LiteralPath $lockStamp) -and (Test-Path -LiteralPath $installedLock) -and
    (Get-Item -LiteralPath $installedLock).LastWriteTimeUtc -ge (Get-Item -LiteralPath $lockfile).LastWriteTimeUtc) {
    # Adopt an install made before stamps existed instead of wiping it with npm ci.
    Write-Stamp $lockfile $lockStamp
}
if (-not (Test-StampCurrent $lockfile $lockStamp)) {
    Write-Host "Installing frontend dependencies..."
    Invoke-Checked "Installing frontend dependencies" { npm --prefix $frontend ci }
    Write-Stamp $lockfile $lockStamp
}

$sourceArgs = @()
if ($Source) { $sourceArgs = @("--source", $Source) }

Push-Location (Join-Path $root "backend")
try {
    if ($Dev) {
        $vite = Start-Process -FilePath "npm.cmd" -ArgumentList "--prefix", $frontend, "run", "dev" -PassThru -NoNewWindow
        try { & $venvPy -m skin_analyzer @sourceArgs --port $Port --dev }
        finally { if ($vite -and -not $vite.HasExited) { Stop-Process -Id $vite.Id -Force } }
    } else {
        if (Test-DashboardStale $frontend) {
            Write-Host "Building dashboard..."
            Invoke-Checked "Building the dashboard" { npm --prefix $frontend run build }
        }
        & $venvPy -m skin_analyzer @sourceArgs --port $Port --open
    }
} finally {
    Pop-Location
}
