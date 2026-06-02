#!/usr/bin/env bash
# socmed-dl — Universal Installer for Linux / macOS
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="https://github.com/Cefneal/socmed-dl"
VENV_DIR="${HOME}/.socmed-dl-venv"
BIN_DIR="${HOME}/.local/bin"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERR]${NC}   $*"; }

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════╗"
echo "║      socmed-dl - Universal Installer       ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

detect_pkg_manager() {
    command -v pacman &>/dev/null && echo "pacman" && return
    command -v apt-get &>/dev/null && echo "apt" && return
    command -v dnf &>/dev/null && echo "dnf" && return
    command -v brew &>/dev/null && echo "brew" && return
    command -v pkg &>/dev/null && echo "pkg" && return
    echo "unknown"
}

install_ffmpeg() {
    local pm="$1"
    info "Installing ffmpeg..."
    case "$pm" in
        pacman) sudo pacman -S --noconfirm --needed ffmpeg python python-pip 2>&1 | tail -2 ;;
        apt)    sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg python3 python3-pip python3-venv 2>&1 | tail -2 ;;
        dnf)    sudo dnf install -y ffmpeg python3 python3-pip 2>&1 | tail -2 ;;
        brew)   brew install ffmpeg python 2>&1 | tail -2 ;;
        pkg)    pkg install ffmpeg python311 2>&1 | tail -2 ;;  # Termux
        *)      warn "Install ffmpeg manually"; return ;;
    esac
    ok "ffmpeg ready"
}

install_yt_dlp() {
    if command -v yt-dlp &>/dev/null; then ok "yt-dlp: $(yt-dlp --version)"; return; fi
    info "Downloading yt-dlp..."
    mkdir -p "$BIN_DIR"
    curl -fsSL "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp" -o "$BIN_DIR/yt-dlp"
    chmod +x "$BIN_DIR/yt-dlp"
    ok "yt-dlp: $("$BIN_DIR/yt-dlp" --version)"
}

install_socmed_dl() {
    if command -v socmed-dl &>/dev/null; then
        warn "socmed-dl already installed, upgrading..."
    fi

    # Try pip from source first
    if [[ -d "$SELF_DIR/src" ]]; then
        info "Installing from local source..."
        python3 -m pip install --quiet --upgrade "$SELF_DIR" 2>/dev/null && { ok "socmed-dl installed from source"; return; }
    fi

    # Fallback: pip from GitHub release
    WHL_URL="${REPO}/releases/latest/download/socmed_dl-2.2.1-py3-none-any.whl"
    info "Installing from GitHub release..."
    python3 -m pip install --quiet --upgrade "$WHL_URL" 2>/dev/null && { ok "socmed-dl installed from GitHub release"; return; }

    # Final fallback: venv
    info "Setting up virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip setuptools wheel
    if [[ -d "$SELF_DIR/src" ]]; then
        "$VENV_DIR/bin/pip" install "$SELF_DIR"
    else
        "$VENV_DIR/bin/pip" install "${REPO}/releases/latest/download/socmed_dl-2.2.1-py3-none-any.whl"
    fi
    mkdir -p "$BIN_DIR"
    cat > "$BIN_DIR/socmed-dl" << 'VEOF'
#!/usr/bin/env bash
exec "$HOME/.socmed-dl-venv/bin/socmed-dl" "$@"
VEOF
    chmod +x "$BIN_DIR/socmed-dl"
    ok "socmed-dl installed (venv)"
}

setup_path() {
    local rc
    case "${SHELL##*/}" in
        fish) rc="${HOME}/.config/fish/config.fish"; mkdir -p "$(dirname "$rc")"
              grep -q 'local/bin' "$rc" 2>/dev/null || echo "fish_add_path ${HOME}/.local/bin" >> "$rc" ;;
        zsh)  rc="${HOME}/.zshrc"
              grep -q 'local/bin' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc" ;;
        bash) rc="${HOME}/.bashrc"
              grep -q 'local/bin' "$rc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc" ;;
    esac
    export PATH="${HOME}/.local/bin:$PATH"
}

PM=$(detect_pkg_manager)
info "Package manager: ${PM}"
install_ffmpeg "$PM"
install_yt_dlp
install_socmed_dl
setup_path

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        socmed-dl v2.0.0 installed!        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "  Run:   socmed-dl              (interactive TUI)"
echo "         socmed-dl URL 720      (CLI mode)"
echo "         socmed-dl --help       (all options)"
echo ""
echo "  Docker: docker run ghcr.io/cefneal/socmed-dl URL 720"
echo ""
if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    warn "Restart terminal or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
