#!/usr/bin/env bash
set -uo pipefail

# Simple safe organizer for Freetopify: minimal moves, no per-artist fanout.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

ROOT_DEFAULT="$HOME/Music/freetopify"
LOG_DIR="$HOME/Scripts/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/organize_music_library_$(date +%Y%m%d_%H%M%S).log"

AUDIO_EXT='\.(mp3|flac|ogg|m4a|aac|opus|wav|wv)$'
PLAYLIST_EXT='\.(m3u|m3u8|pls)$'

MOVED=0
SKIPPED=0
FAILED=0

log() {
  local level="$1"; shift
  printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$level" "$*" | tee -a "$LOG_FILE"
}

sanitize() {
  local v="$1"
  v="$(printf '%s' "$v" | sed -E 's#[/\\:*?"<>|]#-#g; s/[[:space:]]+/ /g; s/^ +//; s/ +$//; s/[. ]+$//')"
  printf '%s' "${v:-Unknown}"
}

resolve_root() {
  local root="${1:-}"
  if [[ -z "$root" && -f "$ENV_FILE" ]]; then
    root="$(grep -E '^MUSIC_LIBRARY_PATH=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
  fi
  root="${root:-$ROOT_DEFAULT}"
  root="${root/#\~/$HOME}"
  ROOT="$(realpath "$root" 2>/dev/null || printf '%s' "$root")"
}

unique_target() {
  local target="$1"
  if [[ ! -e "$target" ]]; then
    printf '%s' "$target"
    return
  fi

  local dir base stem ext i
  dir="$(dirname "$target")"
  base="$(basename "$target")"
  stem="${base%.*}"
  ext="${base##*.}"
  i=1
  while [[ -e "$dir/${stem}_$i.$ext" ]]; do
    i=$((i + 1))
  done
  printf '%s' "$dir/${stem}_$i.$ext"
}

move_file() {
  local src="$1"
  local rel="${src#"$ROOT"/}"

  if [[ "$rel" == Music/* || "$rel" == Podcasts/* || "$rel" == Mixes/* || "$rel" == _playlists/* ]]; then
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  local dest_dir
  if [[ "$src" =~ $PLAYLIST_EXT ]]; then
    dest_dir="$ROOT/_playlists"
  elif [[ "$src" =~ $AUDIO_EXT ]]; then
    dest_dir="$ROOT/Music/Singles"
  else
    SKIPPED=$((SKIPPED + 1))
    return
  fi

  mkdir -p "$dest_dir"
  local target="$dest_dir/$(sanitize "$(basename "$src")")"
  target="$(unique_target "$target")"

  if mv -n "$src" "$target" 2>>"$LOG_FILE"; then
    MOVED=$((MOVED + 1))
    log "INFO" "Moved: $src -> $target"
  else
    FAILED=$((FAILED + 1))
    log "ERROR" "Failed: $src"
  fi
}

main() {
  resolve_root "${1:-}"
  if [[ ! -d "$ROOT" ]]; then
    echo "Root not found: $ROOT"
    exit 1
  fi

  log "INFO" "Start organize root=$ROOT"
  mkdir -p "$ROOT/Music/Singles" "$ROOT/Music/Playlists" "$ROOT/Music/Mixes" "$ROOT/Podcasts" "$ROOT/_playlists"

  while IFS= read -r -d '' f; do
    move_file "$f"
  done < <(find "$ROOT" -type f -print0)

  find "$ROOT" -depth -type d -empty -delete 2>>"$LOG_FILE" || true

  log "INFO" "Done moved=$MOVED skipped=$SKIPPED failed=$FAILED"
  echo "Completed. Log: $LOG_FILE"
}

main "$@"
