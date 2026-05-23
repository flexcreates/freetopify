#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/Music/freetopify}"

echo "[fix-music-tree] root: $ROOT"
if [ ! -d "$ROOT" ]; then
  echo "[fix-music-tree] not found: $ROOT"
  exit 1
fi

mkdir -p "$ROOT/Singles" "$ROOT/Playlists" "$ROOT/Podcasts" "$ROOT/Mixes" "$ROOT/_playlists"

# Legacy singles layout migration:
# 1) Singles/<genre>/<uploader>/Singles/* -> Singles/<uploader>/*
# 2) Singles/<uploader>/Singles/*         -> Singles/<uploader>/*
for oldsingles in "$ROOT"/Singles/*/*/Singles; do
  [ -d "$oldsingles" ] || continue

  genre_dir="$(dirname "$(dirname "$oldsingles")")"
  genre_name="$(basename "$genre_dir")"
  uploader="$(basename "$(dirname "$oldsingles")")"

  # Skip if already canonical path
  if [[ "$oldsingles" == "$ROOT/Singles/$uploader/Singles" ]]; then
    continue
  fi

  newdir="$ROOT/Singles/$uploader"
  mkdir -p "$newdir"

  find "$oldsingles" -maxdepth 1 -type f \
    \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.wav" -o -iname "*.wv" \) \
    -print0 | while IFS= read -r -d '' f; do
      base="$(basename "$f")"
      target="$newdir/$base"
      if [ -e "$target" ]; then
        stem="${base%.*}"
        ext="${base##*.}"
        target="$newdir/${stem}_migrated_from_${genre_name}.$ext"
      fi
      mv "$f" "$target"
      echo "[fix-music-tree] moved: $f -> $target"
    done
done

# Flatten remaining nested uploader Singles folders:
for nested in "$ROOT"/Singles/*/Singles; do
  [ -d "$nested" ] || continue
  uploader_dir="$(dirname "$nested")"
  uploader="$(basename "$uploader_dir")"
  newdir="$ROOT/Singles/$uploader"
  find "$nested" -maxdepth 1 -type f \
    \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.wav" -o -iname "*.wv" \) \
    -print0 | while IFS= read -r -d '' f; do
      base="$(basename "$f")"
      target="$newdir/$base"
      if [ -e "$target" ]; then
        stem="${base%.*}"
        ext="${base##*.}"
        target="$newdir/${stem}_flattened.$ext"
      fi
      mv "$f" "$target"
      echo "[fix-music-tree] moved: $f -> $target"
    done
done

# Cleanup empty dirs left by migration
find "$ROOT" -type d -empty -delete || true

echo "[fix-music-tree] done"
if command -v tree >/dev/null 2>&1; then
  tree "$ROOT"
else
  find "$ROOT" -maxdepth 5 -print
fi
