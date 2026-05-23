#!/usr/bin/env bash
set -euo pipefail

echo "[freetopify] install start"

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

if command -v apt >/dev/null 2>&1; then
  echo "[freetopify] apt found"
  py_minor="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  venv_pkg="$(pick_pkg "python${py_minor}-venv" "python3-venv" || true)"
  pip_pkg="$(pick_pkg "python3-pip" || true)"
  install_pkgs=(sqlite3 ffmpeg yt-dlp curl bluez bluez-tools)
  if [ -n "${venv_pkg:-}" ]; then install_pkgs+=("$venv_pkg"); fi
  if [ -n "${pip_pkg:-}" ]; then install_pkgs+=("$pip_pkg"); fi

  if sudo -n true 2>/dev/null; then
    sudo apt update
    sudo apt install -y "${install_pkgs[@]}"
  else
    echo "[freetopify] sudo password needed. run this manually:"
    echo "sudo apt update && sudo apt install -y ${install_pkgs[*]}"
  fi
fi

# Configure music library path based on OS.
if [ "$OS_NAME" = "Linux" ]; then
  mkdir -p "$DEFAULT_MUSIC_PATH"
  echo "[freetopify] linux detected -> music library: $DEFAULT_MUSIC_PATH"

  if [ -f .env ]; then
    if grep -q '^MUSIC_LIBRARY_PATH=' .env; then
      sed -i "s#^MUSIC_LIBRARY_PATH=.*#MUSIC_LIBRARY_PATH=$DEFAULT_MUSIC_PATH#" .env
    else
      printf '\nMUSIC_LIBRARY_PATH=%s\n' "$DEFAULT_MUSIC_PATH" >> .env
    fi
  else
    if [ -f .env.example ]; then
      cp .env.example .env
      sed -i "s#^MUSIC_LIBRARY_PATH=.*#MUSIC_LIBRARY_PATH=$DEFAULT_MUSIC_PATH#" .env
    else
      cat > .env <<EOF
MUSIC_LIBRARY_PATH=$DEFAULT_MUSIC_PATH
SERVER_PORT=7171
SERVER_HOST=0.0.0.0
SECRET_KEY=CHANGE_ME_GENERATE_A_REAL_SECRET_KEY_HERE
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
    fi
  fi
else
  echo "[freetopify] non-linux OS detected ($OS_NAME); keeping MUSIC_LIBRARY_PATH from existing .env"
fi

if [ ! -d venv ]; then
  python3 -m venv venv || true
fi

if [ -x venv/bin/pip ]; then
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  echo "[freetopify] venv/pip missing. install python3-venv + python3-pip first."
fi

echo "[freetopify] optional BT NAP: sudo bt-network -s nap"
echo "[freetopify] install done"
