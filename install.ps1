# socmed-dl Windows Installer (PowerShell)
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "socmed-dl Installer"

Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      socmed-dl - Windows Installer         ║" -ForegroundColor Cyan
Write-Host "║  YouTube · Facebook · Instagram → x265     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ─── Check Python ──────────────────────────────────────────────────────────────
function Install-Python {
    Write-Host "[INFO]  Python tidak ditemukan. Menginstall Python..." -ForegroundColor Cyan
    winget install "Python.Python.3.14" --silent --accept-package-agreements 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[INFO]  Download Python dari python.org ..." -ForegroundColor Cyan
        $url = "https://www.python.org/ftp/python/3.14.0/python-3.14.0-amd64.exe"
        $out = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri $url -OutFile $out
        Start-Process -Wait -FilePath $out -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1"
    }
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "[OK]    Python terinstall" -ForegroundColor Green
}

try { python --version | Out-Null } catch { Install-Python }

# ─── Check pip ─────────────────────────────────────────────────────────────────
python -m pip install --upgrade pip --quiet 2>$null

# ─── Install FFmpeg ────────────────────────────────────────────────────────────
try {
    ffmpeg -version | Out-Null
    Write-Host "[OK]    FFmpeg sudah terinstall" -ForegroundColor Green
} catch {
    Write-Host "[INFO]  Menginstall FFmpeg via winget..." -ForegroundColor Cyan
    winget install "FFmpeg" --silent --accept-package-agreements 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[INFO]  Download FFmpeg manual..." -ForegroundColor Cyan
        $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        $zip = "$env:TEMP\ffmpeg.zip"
        $dest = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
        Invoke-WebRequest -Uri $url -OutFile $zip
        Expand-Archive -Path $zip -DestinationPath "$env:TEMP\ffmpeg" -Force
        Copy-Item "$env:TEMP\ffmpeg\ffmpeg-*\bin\ffmpeg.exe" "$dest" -Force
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "[OK]    FFmpeg terinstall" -ForegroundColor Green
}

# ─── Install yt-dlp ────────────────────────────────────────────────────────────
try {
    yt-dlp --version | Out-Null
    Write-Host "[OK]    yt-dlp sudah terinstall: $(yt-dlp --version)" -ForegroundColor Green
} catch {
    Write-Host "[INFO]  Menginstall yt-dlp..." -ForegroundColor Cyan
    winget install "yt-dlp" --silent --accept-package-agreements 2>$null
    if ($LASTEXITCODE -ne 0) {
        $url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        $dest = "$env:LOCALAPPDATA\Microsoft\WindowsApps\yt-dlp.exe"
        Invoke-WebRequest -Uri $url -OutFile $dest
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "[OK]    yt-dlp terinstall" -ForegroundColor Green
}

# ─── Install socmed-dl ─────────────────────────────────────────────────────────
Write-Host "[INFO]  Menginstall socmed-dl..." -ForegroundColor Cyan
python -m pip install rich --quiet 2>&1 | Out-Null

# Copy script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $scriptDir "src\socmed_dl\main.py"
$destDir = "$env:LOCALAPPDATA\socmed-dl"
$dest = "$destDir\socmed-dl.py"
$bat = "$env:LOCALAPPDATA\Microsoft\WindowsApps\socmed-dl.cmd"

New-Item -ItemType Directory -Path $destDir -Force | Out-Null
Copy-Item -Path $src -Destination $dest -Force

@"
@echo off
python "$dest" %*
"@ | Out-File -FilePath $bat -Encoding ascii

Write-Host "[OK]    socmed-dl terinstall" -ForegroundColor Green

# ─── Selesai ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        socmed-dl installed!                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Jalankan:  socmed-dl" -ForegroundColor Green
Write-Host "  Bantuan:   socmed-dl --help" -ForegroundColor Green
Write-Host ""
Write-Host "  Interactive : socmed-dl                        " -ForegroundColor Yellow
Write-Host "  Download    : socmed-dl `"URL`" 720             " -ForegroundColor Yellow
Write-Host "  Audio only  : socmed-dl `"URL`" --audio        " -ForegroundColor Yellow
Write-Host ""
Write-Host "  RESTART TERMINAL agar PATH termuat ulang!" -ForegroundColor Red
