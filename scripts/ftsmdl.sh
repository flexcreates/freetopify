#!/usr/bin/env bash
set -uo pipefail

# ftsmdl - Freetopify terminal downloader aligned with server download layout

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

LOG_DIR="$HOME/Scripts/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/ftsmdl_$(date +%Y%m%d_%H%M%S).log"

VENV_DEFAULT="$PROJECT_ROOT/venv"
VENV_PATH="${FREETOPIFY_VENV:-$VENV_DEFAULT}"
MUSIC_DIR="${FREETOPIFY_MUSIC_DIR:-}"
YTDLP_PATH=""
YTDLP_BROWSER="${YTDLP_BROWSER:-}"

CURRENT_FORMAT="mp3"
CURRENT_BITRATE="320k"

log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" | tee -a "$LOG_FILE"
}

load_env_defaults() {
  if [[ -f "$ENV_FILE" ]]; then
    local env_music env_ytdlp env_browser
    env_music="$(grep -E '^MUSIC_LIBRARY_PATH=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
    env_ytdlp="$(grep -E '^YTDLP_PATH=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
    env_browser="$(grep -E '^YTDLP_BROWSER=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"

    if [[ -z "$MUSIC_DIR" && -n "$env_music" ]]; then
      MUSIC_DIR="$env_music"
    fi
    if [[ -z "$YTDLP_PATH" && -n "$env_ytdlp" ]]; then
      YTDLP_PATH="$env_ytdlp"
    fi
    if [[ -z "$YTDLP_BROWSER" && -n "$env_browser" ]]; then
      YTDLP_BROWSER="$env_browser"
    fi
  fi

  if [[ -z "$MUSIC_DIR" ]]; then
    MUSIC_DIR="$HOME/Music/freetopify"
  fi

  MUSIC_DIR="${MUSIC_DIR/#\~/$HOME}"
  if [[ -z "$YTDLP_PATH" ]]; then
    YTDLP_PATH="$VENV_PATH/bin/yt-dlp"
  fi
}

sanitize_component() {
  local value="$1"
  value="$(printf '%s' "$value" | sed -E 's#[/\\:*?"<>|]#-#g; s/[[:space:]]+/ /g; s/^ +//; s/ +$//; s/[. ]+$//')"
  printf '%s' "$value"
}

pick_format() {
  local ans
  printf 'Choose format [1=mp3, 2=flac] (default 1): '
  IFS= read -r ans
  if [[ "$ans" == "2" || "${ans,,}" == "flac" ]]; then
    CURRENT_FORMAT="flac"
    CURRENT_BITRATE=""
  else
    CURRENT_FORMAT="mp3"
    CURRENT_BITRATE="320k"
  fi
}

select_or_create_folder_path() {
  mkdir -p "$MUSIC_DIR"

  mapfile -t dirs < <(find "$MUSIC_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)

  echo ""
  echo "Music root: $MUSIC_DIR"
  echo "Available top-level folders:"
  if [[ ${#dirs[@]} -eq 0 ]]; then
    echo "  (none yet)"
  else
    local i=1
    for d in "${dirs[@]}"; do
      printf '  %d) %s\n' "$i" "$d"
      i=$((i + 1))
    done
  fi
  echo "  n) Create new folder path"

  local choice
  printf 'Pick folder number(s) comma-separated, or n: '
  IFS= read -r choice

  local path_parts=()

  if [[ "${choice,,}" == "n" ]]; then
    local new_path
    printf 'Enter new folder path (example: Music/Playlists/Chill): '
    IFS= read -r new_path
    new_path="$(sanitize_component "$new_path")"
    [[ -z "$new_path" ]] && new_path="Music/Playlists"
    path_parts+=("$new_path")
  else
    IFS=',' read -r -a picks <<< "$choice"
    for p in "${picks[@]}"; do
      p="$(echo "$p" | xargs)"
      if [[ "$p" =~ ^[0-9]+$ ]] && (( p >= 1 && p <= ${#dirs[@]} )); then
        path_parts+=("${dirs[$((p-1))]}")
      fi
    done

    if [[ ${#path_parts[@]} -eq 0 ]]; then
      echo "No valid folder selected. Using Music/Singles"
      path_parts=("Music" "Singles")
    fi

    printf 'Append extra nested folder path (optional): '
    local extra
    IFS= read -r extra
    if [[ -n "$extra" ]]; then
      extra="$(sanitize_component "$extra")"
      path_parts+=("$extra")
    fi
  fi

  local rel_path="${path_parts[0]}"
  local idx
  for ((idx=1; idx<${#path_parts[@]}; idx++)); do
    rel_path="$rel_path/${path_parts[$idx]}"
  done

  rel_path="${rel_path#./}"
  DEST_DIR="$MUSIC_DIR/$rel_path"
  mkdir -p "$DEST_DIR"
  log "INFO" "Selected destination: $DEST_DIR"
}

choose_download_type() {
  local url="$1"
  local ans
  if echo "$url" | grep -qE 'list='; then
    DEFAULT_TYPE="playlist"
  else
    DEFAULT_TYPE="single"
  fi

  printf 'Download type [single/playlist/podcast/mix] (default %s): ' "$DEFAULT_TYPE"
  IFS= read -r ans
  ans="${ans,,}"
  case "$ans" in
    single|playlist|podcast|mix) JOB_TYPE="$ans" ;;
    *) JOB_TYPE="$DEFAULT_TYPE" ;;
  esac
}

output_template_for_type() {
  case "$JOB_TYPE" in
    single) printf '%s' "$DEST_DIR/%(title)s.%(ext)s" ;;
    podcast) printf '%s' "$DEST_DIR/%(uploader)s/%(title)s.%(ext)s" ;;
    mix) printf '%s' "$DEST_DIR/%(playlist_title,s_title)s/%(title)s.%(ext)s" ;;
    *) printf '%s' "$DEST_DIR/%(playlist_title,s_title)s/%(title)s.%(ext)s" ;;
  esac
}

download() {
  local url="$1"
  local out_tpl
  out_tpl="$(output_template_for_type)"

  local -a cmd
  cmd=(
    "$YTDLP_PATH"
    --extract-audio
    --audio-format "$CURRENT_FORMAT"
    --embed-metadata
    --embed-thumbnail
    --newline
    --retries 10
    --retry-sleep 5
    --sleep-interval 2
    --max-sleep-interval 5
    -o "$out_tpl"
  )

  if [[ -n "$CURRENT_BITRATE" ]]; then
    cmd+=(--audio-quality "$CURRENT_BITRATE")
  fi

  if [[ -n "$YTDLP_BROWSER" ]]; then
    cmd+=(--cookies-from-browser "$YTDLP_BROWSER")
  fi

  cmd+=(--remote-components ejs:github)

  if command -v node >/dev/null 2>&1; then
    cmd+=(--js-runtimes "node:$(command -v node)")
  elif command -v nodejs >/dev/null 2>&1; then
    cmd+=(--js-runtimes "node:$(command -v nodejs)")
  fi

  cmd+=("$url")

  log "INFO" "Starting download type=$JOB_TYPE format=$CURRENT_FORMAT url=$url"
  "${cmd[@]}" 2>&1 | tee -a "$LOG_FILE"
  local code="${PIPESTATUS[0]}"
  if [[ "$code" -eq 0 ]]; then
    log "INFO" "Download completed"
  else
    log "ERROR" "Download failed with exit=$code"
  fi
  return "$code"
}

preflight() {
  if [[ ! -x "$YTDLP_PATH" ]]; then
    if command -v yt-dlp >/dev/null 2>&1; then
      YTDLP_PATH="$(command -v yt-dlp)"
    fi
  fi

  if [[ ! -x "$YTDLP_PATH" ]]; then
    echo "yt-dlp not found at: $YTDLP_PATH"
    echo "Install dependencies first (python3 freetopify.py install) or set YTDLP_PATH in .env"
    exit 1
  fi

  if [[ ! -d "$MUSIC_DIR" ]]; then
    printf 'Music directory does not exist (%s). Create it? [y/N]: ' "$MUSIC_DIR"
    local ans
    IFS= read -r ans
    if [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]; then
      mkdir -p "$MUSIC_DIR"
    else
      exit 1
    fi
  fi
}

main() {
  load_env_defaults
  preflight

  echo "ftsmdl - Freetopify Downloader"
  echo "Log: $LOG_FILE"

  while true; do
    select_or_create_folder_path

    local url
    printf 'Enter YouTube URL (or q to quit): '
    IFS= read -r url
    url="$(echo "$url" | xargs)"
    if [[ "$url" == "q" || "$url" == "quit" || "$url" == "exit" ]]; then
      break
    fi
    if [[ -z "$url" ]]; then
      echo "URL is required."
      continue
    fi

    choose_download_type "$url"
    pick_format

    if download "$url"; then
      echo "Done: $DEST_DIR"
    else
      echo "Failed. See log: $LOG_FILE"
    fi

    printf 'Download another? [Y/n]: '
    local again
    IFS= read -r again
    if [[ "${again,,}" == "n" || "${again,,}" == "no" ]]; then
      break
    fi
  done
}

main "$@"
