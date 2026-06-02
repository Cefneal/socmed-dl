# socmed-dl Windows Installer (PowerShell)
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "socmed-dl Installer"

Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      socmed-dl - Windows Installer         ║" -ForegroundColor Cyan
Write-Host "║  YouTube · TikTok · Twitter · Reddit → x265║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

function Test-Command($cmd) { try { Get-Command $cmd -ErrorAction Stop } catch {} }

# ── Python ─────────────────────────────────────────────────────────────────────
if (-not (Test-Command python)) {
    Write-Host "[INFO]  Installing Python..." -ForegroundColor Cyan
    winget install "Python.Python.3.14" --silent --accept-package-agreements 2>$null
    if ($LASTEXITCODE -ne 0) {
        $url = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
        Invoke-WebRequest -UseBasicParsing $url -OutFile "$env:TEMP\python.exe"
        Start-Process -Wait "$env:TEMP\python.exe" -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1"
    }
    $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}

# ── FFmpeg ─────────────────────────────────────────────────────────────────────
if (-not (Test-Command ffmpeg)) {
    Write-Host "[INFO]  Installing FFmpeg..." -ForegroundColor Cyan
    $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    $zip = "$env:TEMP\ffmpeg.zip"
    Invoke-WebRequest -UseBasicParsing $url -OutFile $zip
    Expand-Archive $zip -DestinationPath "$env:TEMP\ffmpeg" -Force
    $exe = (Get-ChildItem "$env:TEMP\ffmpeg\ffmpeg-*\bin\ffmpeg.exe").FullName
    Copy-Item $exe "$env:SystemRoot\System32\ffmpeg.exe" -Force
    Write-Host "[OK]    FFmpeg installed" -ForegroundColor Green
} else { Write-Host "[OK]    FFmpeg already installed" -ForegroundColor Green }

# ── yt-dlp ─────────────────────────────────────────────────────────────────────
if (-not (Test-Command yt-dlp)) {
    Write-Host "[INFO]  Installing yt-dlp..." -ForegroundColor Cyan
    $url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    Invoke-WebRequest -UseBasicParsing $url -OutFile "$env:SystemRoot\System32\yt-dlp.exe"
    Write-Host "[OK]    yt-dlp installed" -ForegroundColor Green
} else { Write-Host "[OK]    yt-dlp already installed: $(yt-dlp --version)" -ForegroundColor Green }

# ── socmed-dl ──────────────────────────────────────────────────────────────────
Write-Host "[INFO]  Installing socmed-dl..." -ForegroundColor Cyan
python -m pip install rich --quiet 2>&1 | Out-Null

# Try pip from GitHub release
$pipOk = $false
$whlUrl = "https://github.com/Cefneal/socmed-dl/releases/latest/download/socmed_dl-2.2.1-py3-none-any.whl"
python -m pip install $whlUrl --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) { $pipOk = $true }

if (-not $pipOk) {
    # Fallback: download ZIP from GitHub
    $url = "https://github.com/Cefneal/socmed-dl/archive/main.zip"
    Invoke-WebRequest -UseBasicParsing $url -OutFile "$env:TEMP\socmed-dl.zip"
    Expand-Archive "$env:TEMP\socmed-dl.zip" -DestinationPath "$env:TEMP\socmed-dl" -Force
    python -m pip install "$env:TEMP\socmed-dl\socmed-dl-main" --quiet 2>&1 | Out-Null
}

Write-Host "[OK]    socmed-dl installed" -ForegroundColor Green

# ── Done ───────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        socmed-dl installed!                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Run:   socmed-dl              (interactive)"
Write-Host "         socmed-dl URL 720      (CLI mode)"
Write-Host "         socmed-dl --help       (all options)"
Write-Host ""
Write-Host "  Docker: docker run ghcr.io/cefneal/socmed-dl URL 720"
Write-Host ""
Write-Host "  RESTART TERMINAL if 'socmed-dl' not found!" -ForegroundColor Red
