#!/usr/bin/env bash
set -euo pipefail

echo "================================================="
echo "        Freetopify Interactive Installer         "
echo "================================================="
echo ""

USER_HOME="${HOME:-/home/$(whoami)}"
DEFAULT_MUSIC_PATH="$USER_HOME/Music/freetopify"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

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

# Music library path detection
if [ -d "$USER_HOME/Music" ]; then
  DEFAULT_MUSIC_PATH="$USER_HOME/Music/freetopify"
else
  DEFAULT_MUSIC_PATH="$USER_HOME/freetopify_music"
fi

while true; do
  read -rp "📁 Music library path [$DEFAULT_MUSIC_PATH]: " USER_MUSIC_PATH
  MUSIC_LIBRARY_PATH="${USER_MUSIC_PATH:-$DEFAULT_MUSIC_PATH}"
  
  if [ -z "$MUSIC_LIBRARY_PATH" ]; then
    echo "⚠️  Path cannot be empty."
    continue
  fi

  # Try to create it if it doesn't exist
  if mkdir -p "$MUSIC_LIBRARY_PATH" 2>/dev/null; then
    # Get absolute path safely
    MUSIC_LIBRARY_PATH="$(cd "$MUSIC_LIBRARY_PATH" && pwd)"
    echo "✅ Music library: $MUSIC_LIBRARY_PATH"
    break
  else
    echo "⚠️  Cannot create or access '$MUSIC_LIBRARY_PATH'. Please enter a valid path."
  fi
done

# Admin credentials
read -rp "👤 Admin username [admin]: " ADMIN_USERNAME
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"

read -rsp "🔑 Admin password [freetopify]: " ADMIN_PASSWORD
echo ""
ADMIN_PASSWORD="${ADMIN_PASSWORD:-freetopify}"

# Guest PIN
read -rp "👥 Guest PIN (leave blank to disable guest access) []: " GUEST_PIN

# Browser for cookie passthrough
DETECTED_BROWSER="$(detect_browser)"
if [ -n "$DETECTED_BROWSER" ]; then
  read -rp "🌐 YouTube Cookie Browser (chrome/firefox/edge) [$DETECTED_BROWSER]: " USER_BROWSER
  YTDLP_BROWSER="${USER_BROWSER:-$DETECTED_BROWSER}"
else
  read -rp "🌐 YouTube Cookie Browser (chrome/firefox/edge) [leave blank to disable]: " YTDLP_BROWSER
fi
if [ -n "$YTDLP_BROWSER" ]; then
  echo "✅ YouTube cookies: $YTDLP_BROWSER"
fi

# yt-dlp path — always use the venv binary for consistency
YTDLP_PATH="./venv/bin/yt-dlp"

# Generate a secure secret key
SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# Write .env (create or update)
if [ -f .env ]; then
  echo ""
  echo "ℹ️  Existing .env found — updating configurable paths/options only."
  sed -i "s#^MUSIC_LIBRARY_PATH=.*#MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH#" .env
  
  grep -q '^YTDLP_PATH=' .env \
    && sed -i "s#^YTDLP_PATH=.*#YTDLP_PATH=$YTDLP_PATH#" .env \
    || echo "YTDLP_PATH=$YTDLP_PATH" >> .env
    
  grep -q '^YTDLP_BROWSER=' .env \
    && sed -i "s#^YTDLP_BROWSER=.*#YTDLP_BROWSER=$YTDLP_BROWSER#" .env \
    || echo "YTDLP_BROWSER=$YTDLP_BROWSER" >> .env

  grep -q '^GUEST_PIN=' .env \
    && sed -i "s#^GUEST_PIN=.*#GUEST_PIN=$GUEST_PIN#" .env \
    || echo "GUEST_PIN=$GUEST_PIN" >> .env
else
  cat > .env <<EOF
# ─────────────────────────────────────────────
#  Freetopify — Environment Configuration
#  Copy this file to .env and fill in your values.
#  Never commit .env to version control.
# ─────────────────────────────────────────────


# ── Server ────────────────────────────────────
SERVER_HOST=0.0.0.0
SERVER_PORT=7171


# ── Auth & Security ───────────────────────────
# Generate a strong secret key:  python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=$SECRET_KEY

# Admin credentials (change before first run)
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD

# JWT token lifetime for admin sessions (hours)
TOKEN_EXPIRE_HOURS=168


# ── Paths ─────────────────────────────────────
# Where your music library lives on disk
MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH

# SQLite database file
DATABASE_PATH=./data/freetopify.db

# Path to yt-dlp binary (use full path or keep as 'yt-dlp' if on PATH)
YTDLP_PATH=$YTDLP_PATH

# Path to your Python virtual environment
VENV_PATH=./venv


# ── Downloader ────────────────────────────────
# Output audio format: mp3 | flac | ogg | m4a | opus
DEFAULT_DOWNLOAD_FORMAT=mp3

# Output bitrate (max quality for MP3 is 320k)
DEFAULT_DOWNLOAD_BITRATE=320k

# Optional: browser to read YouTube cookies from — bypasses 429 rate-limit errors.
# Requires you to be logged in to YouTube in that browser.
# Options: chrome | firefox | edge | safari  (leave blank to disable)
YTDLP_BROWSER=$YTDLP_BROWSER


# ── Logging ───────────────────────────────────
# Log level: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO
LOG_FILE=./logs/freetopify.log


# ── Network / Discovery ───────────────────────
# Your Tailscale IP — used for remote access over VPN (optional)
TAILSCALE_IP=


# ── Guest Access ──────────────────────────────
# Shared PIN for guest logins (leave blank to disable guest access)
GUEST_PIN=$GUEST_PIN

# JWT token lifetime for guest sessions (hours)
GUEST_TOKEN_EXPIRE_HOURS=1


# ── Network ───────────────────────
# Max simultaneous connections to the server (0 = unlimited)
MAX_CONNECTIONS=0
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
echo "  Start the server:   ./scripts/run_server_linux.sh"
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
