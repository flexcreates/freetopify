#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[%s] [INFO] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

warn() {
  printf '[%s] [WARN] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

log "Freetopify macOS installer starting"

if ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew is not installed. Install from https://brew.sh and rerun."
  exit 1
fi

log "Installing system dependencies with Homebrew"
brew update
brew install python ffmpeg sqlite node || true

USER_HOME="${HOME:-$PROJECT_ROOT}"
if [ -d "$USER_HOME/Music" ]; then
  DEFAULT_MUSIC_PATH="$USER_HOME/Music/freetopify"
else
  DEFAULT_MUSIC_PATH="$USER_HOME/freetopify_music"
fi

read -rp "Music library path [$DEFAULT_MUSIC_PATH]: " USER_MUSIC_PATH
MUSIC_LIBRARY_PATH="${USER_MUSIC_PATH:-$DEFAULT_MUSIC_PATH}"
mkdir -p "$MUSIC_LIBRARY_PATH"
MUSIC_LIBRARY_PATH="$(cd "$MUSIC_LIBRARY_PATH" && pwd)"

read -rp "Admin username [admin]: " ADMIN_USERNAME
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"

read -rsp "Admin password [freetopify]: " ADMIN_PASSWORD
echo ""
ADMIN_PASSWORD="${ADMIN_PASSWORD:-freetopify}"

read -rp "Guest PIN (leave blank to disable): " GUEST_PIN

DETECTED_BROWSER=""
for candidate in safari chrome firefox edge; do
  case "$candidate" in
    safari)
      [ -d "/Applications/Safari.app" ] && DETECTED_BROWSER="safari" && break
      ;;
    chrome)
      [ -d "/Applications/Google Chrome.app" ] && DETECTED_BROWSER="chrome" && break
      ;;
    firefox)
      [ -d "/Applications/Firefox.app" ] && DETECTED_BROWSER="firefox" && break
      ;;
    edge)
      [ -d "/Applications/Microsoft Edge.app" ] && DETECTED_BROWSER="edge" && break
      ;;
  esac
done

if [ -n "$DETECTED_BROWSER" ]; then
  read -rp "YouTube Cookie Browser (chrome/firefox/edge/safari) [$DETECTED_BROWSER]: " USER_BROWSER
  YTDLP_BROWSER="${USER_BROWSER:-$DETECTED_BROWSER}"
else
  read -rp "YouTube Cookie Browser (chrome/firefox/edge/safari) [blank=disable]: " YTDLP_BROWSER
fi

SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
YTDLP_PATH="./venv/bin/yt-dlp"

if [ -f .env ]; then
  log "Existing .env found; updating configurable values"
  sed -i '' "s#^MUSIC_LIBRARY_PATH=.*#MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH#" .env
  sed -i '' "s#^YTDLP_PATH=.*#YTDLP_PATH=$YTDLP_PATH#" .env || true

  grep -q '^YTDLP_PATH=' .env || echo "YTDLP_PATH=$YTDLP_PATH" >> .env
  grep -q '^YTDLP_BROWSER=' .env \
    && sed -i '' "s#^YTDLP_BROWSER=.*#YTDLP_BROWSER=$YTDLP_BROWSER#" .env \
    || echo "YTDLP_BROWSER=$YTDLP_BROWSER" >> .env
  grep -q '^GUEST_PIN=' .env \
    && sed -i '' "s#^GUEST_PIN=.*#GUEST_PIN=$GUEST_PIN#" .env \
    || echo "GUEST_PIN=$GUEST_PIN" >> .env
else
  cat > .env <<EOF
SERVER_HOST=0.0.0.0
SERVER_PORT=7171
SECRET_KEY=$SECRET_KEY
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
TOKEN_EXPIRE_HOURS=168
MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH
DATABASE_PATH=./data/freetopify.db
YTDLP_PATH=$YTDLP_PATH
VENV_PATH=./venv
DEFAULT_DOWNLOAD_FORMAT=mp3
DEFAULT_DOWNLOAD_BITRATE=320k
YTDLP_BROWSER=$YTDLP_BROWSER
LOG_LEVEL=INFO
LOG_FILE=./logs/freetopify.log
TAILSCALE_IP=
GUEST_PIN=$GUEST_PIN
GUEST_TOKEN_EXPIRE_HOURS=1
MAX_CONNECTIONS=0
EOF
fi

log "Setting up Python virtual environment"
if [ ! -d venv ]; then
  python3 -m venv venv
fi

source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Install complete"
echo "Start server: python3 freetopify.py start"
