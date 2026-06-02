<div align="center">
  <pre>
╔════════════════════════════════════════════════════╗
║███████╗ ██████╗ ███╗   ███╗███████╗██████╗ ██╗     ║
║██╔════╝██╔═══██╗████╗ ████║██╔════╝██╔══██╗██║     ║
║███████╗██║   ██║██╔████╔██║█████╗  ██║  ██║██║     ║
║╚════██║██║   ██║██║╚██╔╝██║██╔══╝  ██║  ██║██║     ║
║███████║╚██████╔╝██║ ╚═╝ ██║███████╗██████╔╝███████╗║
║╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═════╝ ╚══════╝║
╚════════════════════════════════════════════════════╝
  </pre>
  <h1>socmed-dl</h1>
  <p><strong>Download video/music from 10+ platforms — convert to x265/AV1/VP9</strong></p>
  <p>
    <a href="#-install"><kbd>📥 Install</kbd></a>
    <a href="#-usage"><kbd>🚀 Usage</kbd></a>
    <a href="#-features"><kbd>✨ Features</kbd></a>
    <a href="#-docker"><kbd>🐳 Docker</kbd></a>
  </p>

  [![PyPI](https://img.shields.io/pypi/v/socmed-dl)](https://pypi.org/project/socmed-dl/)
  [![GitHub Release](https://img.shields.io/github/v/release/Cefneal/socmed-dl)](https://github.com/Cefneal/socmed-dl/releases)
  ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android-success)
  [![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/Cefneal/socmed-dl/pkgs/container/socmed-dl)
</div>

---

## 📥 Install

### Linux (any distro)
```bash
curl -sL https://github.com/Cefneal/socmed-dl/raw/main/install.sh | bash
socmed-dl
```

### Arch Linux
```bash
yay -S socmed-dl       # AUR (soon)
# or build from PKGBUILD:
git clone https://github.com/Cefneal/socmed-dl.git
cd socmed-dl && makepkg -si
```

### macOS
```bash
brew install ffmpeg python
pip3 install socmed-dl
socmed-dl
```

### Windows
```powershell
# Auto-installer:
powershell -ExecutionPolicy Bypass -c "iex (iwr -UseBasicParsing https://github.com/Cefneal/socmed-dl/raw/main/install.ps1)"

# Or manual:
winget install FFmpeg
winget install yt-dlp
pip install socmed-dl
socmed-dl
```

### Android (Termux)
```bash
pkg update && pkg upgrade -y
pkg install python ffmpeg -y
pip install yt-dlp socmed-dl
socmed-dl
```

### Via pip (any OS)
```bash
pip install https://github.com/Cefneal/socmed-dl/releases/latest/download/socmed_dl-2.2.1-py3-none-any.whl
```

### Docker
```bash
docker run ghcr.io/cefneal/socmed-dl "https://youtube.com/watch?v=..." 1080
```

---

## 🚀 Usage

### Interactive TUI
```bash
socmed-dl
```
Just run it — paste a URL, pick quality/codec, download. Clean TUI with progress bars.

### CLI mode
```bash
# Basic
socmed-dl "https://youtube.com/watch?v=..." 720 ~/Videos

# Audio only
socmed-dl "https://youtube.com/watch?v=..." --audio --audio-format flac

# Choose codec
socmed-dl "https://youtube.com/watch?v=..." 1080 --codec av1

# Batch download (playlist or URLs)
socmed-dl "URL1" "URL2" "URL3" --concurrent 3

# List formats with file sizes
socmed-dl "URL" --list-formats

# Cookies for age-restricted / private videos
socmed-dl "URL" --cookies /path/to/cookies.txt

# Proxy
socmed-dl "URL" --proxy http://127.0.0.1:8080

# Clip a segment
socmed-dl "URL" --start-time 01:30 --end-time 03:00

# Dry run
socmed-dl "URL" --dry-run

# Save defaults
socmed-dl --config quality=1080 --config codec=x265
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **10+ Platforms** | YouTube, Facebook, Instagram, TikTok, Twitter/X, Reddit, Twitch, Vimeo, Dailymotion, Tumblr |
| **x265 (HEVC)** | ~50% smaller files than x264 at same quality |
| **AV1 / VP9 / x264** | Multiple codec options |
| **144p → 1080p** | All resolutions |
| **Audio only** | MP3, AAC, FLAC, Opus, WAV |
| **Batch download** | Playlists, multiple URLs |
| **Concurrent** | Download N videos at once (`--concurrent 3`) |
| **Resume support** | Interrupted downloads continue |
| **Cookies auth** | Age-restricted / private videos |
| **Proxy support** | HTTP/HTTPS/SOCKS |
| **Subtitles** | Auto-download & embed |
| **Thumbnails** | Embed in output file |
| **Clip trimming** | `--start-time` / `--end-time` |
| **File size display** | See size per format before downloading |
| **Rate limiting** | `--limit-rate 5` (MB/s) |
| **Config file** | `~/.config/socmed-dl/config.json` — save your defaults |
| **Dry run** | Preview without downloading |
| **Retry** | Auto-retry on network errors |
| **Docker** | `docker run ghcr.io/cefneal/socmed-dl` |
| **TUI** | Interactive menu with rich progress bars |
| **Cross-platform** | Windows · macOS · Linux · Android (Termux) |

---

## 🐳 Docker

```bash
# Pull
docker pull ghcr.io/cefneal/socmed-dl

# Run interactive
docker run -it --rm -v "$PWD:/downloads" ghcr.io/cefneal/socmed-dl

# CLI mode
docker run --rm -v "$PWD:/downloads" ghcr.io/cefneal/socmed-dl "URL" 720

# With cookies
docker run --rm -v "$PWD:/downloads" -v "/path/to/cookies.txt:/cookies.txt" \
  ghcr.io/cefneal/socmed-dl "URL" --cookies /cookies.txt
```

---

## ⚙️ Config File

Saved at `~/.config/socmed-dl/config.json`. Example:

```json
{
  "quality": 1080,
  "codec": "x265",
  "mode": "video",
  "audio_format": "flac",
  "output_dir": "~/Downloads/socmed",
  "concurrent": 2,
  "crf": 28,
  "preset": "medium",
  "subtitles": true,
  "embed_thumbnail": true,
  "cookies_file": "/path/to/cookies.txt"
}
```

---

## 📦 What's included

```
src/socmed_dl/
├── __init__.py     # Version info
├── __main__.py     # python -m entry
├── cli.py          # CLI argument parsing + main()
├── app.py          # Interactive TUI (Rich)
├── config.py       # Config file manager
├── downloader.py   # yt-dlp wrapper (formats, batch, resume)
├── converter.py    # ffmpeg x265/AV1/VP9 conversion
└── utils.py        # Helpers (platform detection, deps)
```

---

## 🏗️ Build from source

```bash
git clone https://github.com/Cefneal/socmed-dl.git
cd socmed-dl
pip install .
socmed-dl
```

---

## 📄 License

MIT
