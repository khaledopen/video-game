# Installe Python 3.11 et les dependances DANS ce dossier (rien n'est modifie ailleurs).
# Usage : powershell -ExecutionPolicy Bypass -File installer.ps1 [-Dev]
param([switch]$Dev)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$env:UV_PYTHON_INSTALL_DIR = "$root\.runtime\python"
$env:UV_CACHE_DIR = "$root\.runtime\cache"
$env:UV_PYTHON_PREFERENCE = "only-managed"
$uv = "$root\.runtime\uv\uv.exe"

if (-not (Test-Path $uv)) {
    Write-Host "Telechargement de uv (gestionnaire Python open source, github.com/astral-sh/uv)..."
    New-Item -ItemType Directory -Force "$root\.runtime\uv" | Out-Null
    $zip = "$root\.runtime\uv.zip"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip "$root\.runtime\uv" -Force
    Remove-Item $zip
}
if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
    & $uv python install 3.11 --no-bin --no-registry
    if ($LASTEXITCODE -ne 0) { throw "Installation de Python impossible." }
    & $uv venv --python 3.11 "$root\.venv"
}
$req = if ($Dev) { "requirements-dev.txt" } else { "requirements.txt" }
& $uv pip install --python "$root\.venv\Scripts\python.exe" -r "$root\$req"
if ($LASTEXITCODE -ne 0) { throw "Installation des dependances impossible." }
Write-Host "Installation terminee. Lancez lancer.bat" -ForegroundColor Cyan
