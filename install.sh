#!/usr/bin/env bash
set -euo pipefail

echo "================================================="
echo "        Freetopify Interactive Installer         "
echo "================================================="
echo ""

OS_NAME="$(uname -s || echo unknown)"
USER_HOME="${HOME:-/home/$(whoami)}"
DEFAULT_MUSIC_PATH="$USER_HOME/Music/freetopify"

pick_pkg() {
  for pkg in "$@"; do
    if apt-cache show "$pkg" >/dev/null 2>&1; then
      echo "$pkg"
      return 0
    fi
  done
  return 1
}

echo "[1/3] Checking System Dependencies..."
if command -v apt >/dev/null 2>&1; then
  py_minor="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  venv_pkg="$(pick_pkg "python${py_minor}-venv" "python3-venv" || true)"
  pip_pkg="$(pick_pkg "python3-pip" || true)"
  install_pkgs=(sqlite3 ffmpeg curl bluez bluez-tools)
  
  # Note: yt-dlp installed via pip later is usually better, but we can install the apt one as a fallback
  
  if [ -n "${venv_pkg:-}" ]; then install_pkgs+=("$venv_pkg"); fi
  if [ -n "${pip_pkg:-}" ]; then install_pkgs+=("$pip_pkg"); fi

  if sudo -n true 2>/dev/null; then
    sudo apt update
    sudo apt install -y "${install_pkgs[@]}"
  else
    echo "⚠️  Sudo permission is required to install system dependencies (ffmpeg, sqlite3, python-venv)."
    sudo apt update
    sudo apt install -y "${install_pkgs[@]}"
  fi
  echo "✅ System dependencies installed."
else
  echo "⚠️  Non-APT system detected. Please manually ensure python3-venv, ffmpeg, and sqlite3 are installed."
fi

echo ""
echo "[2/3] Configuring Library..."
read -p "Enter the full path where you want to create your Music Library [$DEFAULT_MUSIC_PATH]: " USER_MUSIC_PATH
MUSIC_LIBRARY_PATH="${USER_MUSIC_PATH:-$DEFAULT_MUSIC_PATH}"

mkdir -p "$MUSIC_LIBRARY_PATH"
echo "✅ Music library ready at: $MUSIC_LIBRARY_PATH"

if [ -f .env ]; then
  if grep -q '^MUSIC_LIBRARY_PATH=' .env; then
    sed -i "s#^MUSIC_LIBRARY_PATH=.*#MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH#" .env
  else
    printf '\nMUSIC_LIBRARY_PATH=%s\n' "$MUSIC_LIBRARY_PATH" >> .env
  fi
else
  cat > .env <<EOF
MUSIC_LIBRARY_PATH=$MUSIC_LIBRARY_PATH
SERVER_PORT=7171
SERVER_HOST=0.0.0.0
SECRET_KEY=$(head -c 32 /dev/urandom | base64)
TOKEN_EXPIRE_HOURS=720
ADMIN_USERNAME=admin
ADMIN_PASSWORD=freetopify
DATABASE_PATH=./data/freetopify.db
YTDLP_PATH=yt-dlp
VENV_PATH=./venv
DEFAULT_DOWNLOAD_FORMAT=mp3
DEFAULT_DOWNLOAD_BITRATE=320k
LOG_LEVEL=INFO
LOG_FILE=./logs/freetopify.log
MDNS_HOSTNAME=freetopify
ENABLE_MDNS=false
TAILSCALE_IP=
EOF
  echo "✅ Auto-generated .env configuration."
fi

echo ""
echo "[3/3] Setting up Python Virtual Environment..."
if [ ! -d venv ]; then
  python3 -m venv venv
fi

if [ -x venv/bin/pip ]; then
  source venv/bin/activate
  pip install --upgrade pip
  # yt-dlp is best installed via pip to ensure the latest version for YouTube extraction fixes
  pip install yt-dlp
  pip install -r requirements.txt
  echo "✅ Python dependencies installed."
else
  echo "❌ Error: Virtual environment was not created properly."
  exit 1
fi

echo ""
echo "================================================="
echo "        🎉 Freetopify is ready to run! 🎉        "
echo "================================================="
echo "To start the server manually, run:"
echo "  source venv/bin/activate"
echo "  uvicorn server.main:app --host 0.0.0.0 --port 7171"
echo ""
echo "To install it as a background service so it auto-starts on boot:"
echo "  sudo cp freetopify.service /etc/systemd/system/"
echo "  sudo systemctl enable --now freetopify"
echo "================================================="
