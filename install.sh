#!/usr/bin/env bash
set -euo pipefail

echo "================================================="
echo "        Freetopify Interactive Installer         "
echo "================================================="
echo ""

USER_HOME="${HOME:-/home/$(whoami)}"
DEFAULT_MUSIC_PATH="$USER_HOME/Music/freetopify"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Helper: pick first available apt package ──────────
pick_pkg() {
  for pkg in "$@"; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
      echo "$pkg"; return 0
    fi
  done
  return 1
}

# ── Helper: detect installed browser ─────────────────
detect_browser() {
  for b in firefox google-chrome chromium-browser chromium; do
    if command -v "$b" >/dev/null 2>&1; then
      case "$b" in
        firefox) echo "firefox"; return ;;
        google-chrome) echo "chrome"; return ;;
        chromium*) echo "chromium"; return ;;
      esac
    fi
  done
  echo ""  # none detected
}

# ─────────────────────────────────────────────────────
echo "[1/3] Installing System Dependencies..."
if command -v apt >/dev/null 2>&1; then
  py_minor="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  venv_pkg="$(pick_pkg "python${py_minor}-venv" "python3-venv" || true)"
  pip_pkg="$(pick_pkg "python3-pip" || true)"

  install_pkgs=(
    sqlite3
    ffmpeg
    curl
    # nodejs: required by yt-dlp to solve YouTube JS signatures.
    # Without it, some YouTube downloads fail with "Signature solving failed".
    # It is a lightweight runtime and installs cleanly on all Debian/Ubuntu systems.
    nodejs
  )

  if [ -n "${venv_pkg:-}" ]; then install_pkgs+=("$venv_pkg"); fi
  if [ -n "${pip_pkg:-}" ];  then install_pkgs+=("$pip_pkg");  fi

  sudo apt-get update -qq
  sudo apt-get install -y "${install_pkgs[@]}"
  echo "✅ System dependencies installed."
else
  echo "⚠️  Non-APT system detected. Please manually install: python3-venv, ffmpeg, sqlite3, nodejs"
fi

# ─────────────────────────────────────────────────────
echo ""
echo "[2/3] Configuring Your Setup..."

# Music library path
read -rp "📁 Music library path [$DEFAULT_MUSIC_PATH]: " USER_MUSIC_PATH
MUSIC_LIBRARY_PATH="${USER_MUSIC_PATH:-$DEFAULT_MUSIC_PATH}"
mkdir -p "$MUSIC_LIBRARY_PATH"
echo "✅ Music library: $MUSIC_LIBRARY_PATH"

# Admin credentials
read -rp "👤 Admin username [admin]: " ADMIN_USERNAME
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"

read -rsp "🔑 Admin password [freetopify]: " ADMIN_PASSWORD
echo ""
ADMIN_PASSWORD="${ADMIN_PASSWORD:-freetopify}"

# Auto-detect browser for YouTube cookie bypass
DETECTED_BROWSER="$(detect_browser)"
if [ -n "$DETECTED_BROWSER" ]; then
  echo "🌐 Detected browser: $DETECTED_BROWSER (will be used for YouTube cookie bypass)"
  YTDLP_BROWSER="$DETECTED_BROWSER"
else
  echo "⚠️  No browser detected — YTDLP_BROWSER left blank (set manually in .env if needed)"
  YTDLP_BROWSER=""
fi

# yt-dlp path — always use the venv binary for consistency
YTDLP_PATH="./venv/bin/yt-dlp"

# Generate a secure secret key
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Write .env (create or update)
if [ -f .env ]; then
  echo ""
  echo "ℹ️  Existing .env found — updating paths and browser only."
  sed -i "s#^MUSIC_LIBRARY_PATH=.*#MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH#" .env
  
  grep -q '^YTDLP_PATH=' .env \
    && sed -i "s#^YTDLP_PATH=.*#YTDLP_PATH=$YTDLP_PATH#" .env \
    || echo "YTDLP_PATH=$YTDLP_PATH" >> .env
    
  grep -q '^YTDLP_BROWSER=' .env \
    && sed -i "s#^YTDLP_BROWSER=.*#YTDLP_BROWSER=$YTDLP_BROWSER#" .env \
    || echo "YTDLP_BROWSER=$YTDLP_BROWSER" >> .env
else
  cat > .env <<EOF
# ── Server ────────────────────────────────────
SERVER_HOST=0.0.0.0
SERVER_PORT=7171

# ── Auth & Security ───────────────────────────
SECRET_KEY=$SECRET_KEY
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
TOKEN_EXPIRE_HOURS=168
SECURE_COOKIES=false

# ── Paths ─────────────────────────────────────
MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH
DATABASE_PATH=./data/freetopify.db
YTDLP_PATH=$YTDLP_PATH
VENV_PATH=./venv

# ── Downloader ────────────────────────────────
DEFAULT_DOWNLOAD_FORMAT=mp3
DEFAULT_DOWNLOAD_BITRATE=320k
YTDLP_BROWSER=$YTDLP_BROWSER

# ── Logging ───────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=./logs/freetopify.log

# ── Network / Discovery ───────────────────────
MDNS_HOSTNAME=freetopify
ENABLE_MDNS=true
TAILSCALE_IP=

# ── Guest Access ──────────────────────────────
GUEST_PIN=
GUEST_TOKEN_EXPIRE_HOURS=1

# ── Party Mode / DJ Hub ───────────────────────
MAX_CONNECTIONS=0
PARTY_BUFFER_MS=500
EOF
  echo "✅ .env created with auto-generated secret key."
fi

# ─────────────────────────────────────────────────────
echo ""
echo "[3/3] Setting up Python Environment..."
if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✅ Python dependencies installed."

echo ""
echo "================================================="
echo "   🎉 Freetopify is installed and ready! 🎉      "
echo "================================================="
echo ""
echo "  Start the server:   ./scripts/run_server.sh"
echo "  Open in browser:    http://localhost:7171"
echo "  Admin login:        $ADMIN_USERNAME / [your password]"
if [ -n "$YTDLP_BROWSER" ]; then
echo "  YouTube cookies:    $YTDLP_BROWSER (auto-configured ✅)"
fi
echo ""
echo "  To auto-start on boot:"
echo "    sudo cp freetopify.service /etc/systemd/system/"
echo "    sudo systemctl enable --now freetopify"
echo "================================================="
