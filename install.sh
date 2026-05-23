#!/usr/bin/env bash
set -euo pipefail

echo "[freetopify] install start"

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
  py_minor="$(python3 -c 'import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")')"
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
