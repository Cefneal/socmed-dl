#!/usr/bin/env bash
# One-command installer for socmed-dl
# Works on: Arch Linux, Debian/Ubuntu, Fedora, macOS
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${HOME}/.socmed-dl-venv"
BIN_DIR="${HOME}/.local/bin"
YT_DLP_BIN="${BIN_DIR}/yt-dlp"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERR]${NC}   $*"; }

detect_pkg_manager() {
    if command -v pacman &>/dev/null; then
        echo "pacman"
    elif command -v apt-get &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v brew &>/dev/null; then
        echo "brew"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    local pm="$1"
    info "Installing system dependencies (ffmpeg)..."

    case "$pm" in
        pacman)
            sudo pacman -S --noconfirm --needed ffmpeg python python-pip 2>&1 | tail -3
            ;;
        apt)
            sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg python3 python3-pip python3-venv 2>&1 | tail -3
            ;;
        dnf)
            sudo dnf install -y ffmpeg python3 python3-pip 2>&1 | tail -3
            ;;
        brew)
            brew install ffmpeg python 2>&1 | tail -3
            ;;
        *)
            warn "Unknown package manager. Please install ffmpeg manually."
            ;;
    esac
    ok "System dependencies installed"
}

install_yt_dlp() {
    if command -v yt-dlp &>/dev/null; then
        ok "yt-dlp already installed: $(yt-dlp --version)"
        return
    fi
    if [[ -f "$YT_DLP_BIN" ]]; then
        ok "yt-dlp already installed: $($YT_DLP_BIN --version)"
        return
    fi

    info "Downloading yt-dlp..."
    mkdir -p "$BIN_DIR"
    curl -fsSL "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp" -o "$YT_DLP_BIN"
    chmod +x "$YT_DLP_BIN"
    ok "yt-dlp installed: $($YT_DLP_BIN --version)"
}

install_python_package() {
    info "Installing socmed-dl Python package..."

    # Use venv to avoid PEP 668 issues
    python3 -m venv "$VENV_DIR" 2>/dev/null || {
        warn "venv creation failed, installing system-wide..."
        python3 -m pip install "$SELF_DIR" 2>&1 | tail -3
        return
    }

    "$VENV_DIR/bin/pip" install --quiet --upgrade pip 2>/dev/null || true
    "$VENV_DIR/bin/pip" install "$SELF_DIR" 2>&1 | tail -3

    # Create wrapper script
    mkdir -p "$BIN_DIR"
    cat > "${BIN_DIR}/socmed-dl" << WRAPPER
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/socmed-dl" "\$@"
WRAPPER
    chmod +x "${BIN_DIR}/socmed-dl"

    ok "socmed-dl installed"
}

setup_path() {
    local shell_config=""
    if [[ "$SHELL" == *fish ]]; then
        shell_config="${HOME}/.config/fish/config.fish"
        mkdir -p "$(dirname "$shell_config")"
        if ! grep -q "local/bin" "$shell_config" 2>/dev/null; then
            echo "fish_add_path ${HOME}/.local/bin" >> "$shell_config"
            ok "Added ~/.local/bin to fish PATH ($shell_config)"
        fi
    elif [[ "$SHELL" == *zsh ]]; then
        shell_config="${HOME}/.zshrc"
        if ! grep -q "local/bin" "$shell_config" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_config"
            ok "Added ~/.local/bin to zsh PATH ($shell_config)"
        fi
    elif [[ "$SHELL" == *bash ]]; then
        shell_config="${HOME}/.bashrc"
        if ! grep -q "local/bin" "$shell_config" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_config"
            ok "Added ~/.local/bin to bash PATH ($shell_config)"
        fi
    fi

    # Add to current session
    export PATH="${HOME}/.local/bin:$PATH"
}

print_summary() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        socmed-dl installed!               ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Run:  ${GREEN}socmed-dl${NC}"
    echo -e "  Help: ${GREEN}socmed-dl --help${NC}"
    echo ""
    echo -e "  ${YELLOW}Interactive TUI:${NC}  socmed-dl"
    echo -e "  ${YELLOW}Download video:${NC}   socmed-dl \"URL\" 720"
    echo -e "  ${YELLOW}Download audio:${NC}   socmed-dl \"URL\" --audio"
    echo ""

    if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
        warn "Restart your terminal or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

# ─── Main ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      socmed-dl - One-Command Install       ║${NC}"
echo -e "${CYAN}║  YouTube · Facebook · Instagram → x265     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""

PM=$(detect_pkg_manager)
info "Detected package manager: ${PM}"

install_system_deps "$PM"
install_yt_dlp
install_python_package
setup_path

print_summary
