#!/usr/bin/env bash
# ============================================================
#  nvmsdl — Freetopify Music Downloader (v3)
#  Downloads YouTube links via yt-dlp into category-based Freetopify folders
#  Auto-detects playlist vs single video; explicit modes for podcasts and mixes
#  Venv: ~/Venvs/navi | Log: ~/Scripts/logs/nvmsdl.log
# ============================================================

# ── Paths ────────────────────────────────────────────────────
VENV="${FREETOPIFY_VENV:-$HOME/Venvs/navi}"
MUSIC_DIR="${FREETOPIFY_MUSIC_DIR:-$HOME/Music/freetopify}"
PLAYLIST_ROOT="$MUSIC_DIR/Playlists"
SINGLE_ROOT="$MUSIC_DIR/Singles"
PODCAST_ROOT="$MUSIC_DIR/Podcasts"
MIX_ROOT="$MUSIC_DIR/Mixes"
PLAYLIST_DIR="$MUSIC_DIR/_playlists"
LOG_DIR="$HOME/Scripts/logs"
LOG_FILE="$LOG_DIR/nvmsdl.log"
SESSION_LOG="$LOG_DIR/nvmsdl_session_$(date +%Y%m%d_%H%M%S).log"

# ── yt-dlp runtime args ───────────────────────────────────────
declare -a YTDLP_JS_ARGS=()
declare -a YTDLP_COMMON_ARGS=()

# ── Environment ──────────────────────────────────────────────
# Load NVM so yt-dlp can find the Node.js runtime
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# ── Colors & Styles ──────────────────────────────────────────
R='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

BLK='\033[30m'
RED='\033[31m'
GRN='\033[32m'
YLW='\033[33m'
BLU='\033[34m'
MAG='\033[35m'
CYN='\033[36m'
WHT='\033[37m'

BBLK='\033[90m'
BRED='\033[91m'
BGRN='\033[92m'
BYLW='\033[93m'
BBLU='\033[94m'
BMAG='\033[95m'
BCYN='\033[96m'
BWHT='\033[97m'

BG_BLK='\033[40m'
BG_BLU='\033[44m'
BG_MAG='\033[45m'
BG_CYN='\033[46m'

# ── Stats ─────────────────────────────────────────────────────
SESSION_TRACKS=0
SESSION_FAILED=0
SESSION_START=$(date +%s)

# ── Format & Genre ────────────────────────────────────────────
CURRENT_FORMAT="mp3"
CURRENT_BITRATE="320k"
CURRENT_GENRE="Music"

# ── Terminal width ────────────────────────────────────────────
TW=$(tput cols 2>/dev/null || echo 80)

# ── Helpers ──────────────────────────────────────────────────
repeat_char() { printf "%${2}s" | tr ' ' "$1"; }

divider() {
    local char="${1:-=}"
    local color="${2:-$BBLK}"
    echo -e "${color}$(repeat_char "$char" "$TW")${R}"
}

center_text() {
    local text="$1"
    local color="${2:-$WHT}"
    local clean="${text//\\033\[[0-9;]*m/}"
    local pad=$(( (TW - ${#clean}) / 2 ))
    printf "%${pad}s"
    echo -e "${color}${text}${R}"
}

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
    local level="$1"; shift
    local msg="$*"
    local ts
    ts=$(timestamp)
    echo "[$ts] [$level] $msg" >> "$LOG_FILE"
    echo "[$ts] [$level] $msg" >> "$SESSION_LOG"
}

elapsed_time() {
    local secs=$(( $(date +%s) - SESSION_START ))
    printf '%02d:%02d:%02d' $((secs/3600)) $(( (secs%3600)/60 )) $((secs%60))
}

count_library() {
    TOTAL_TRACKS=$(find "$MUSIC_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.m4a" \) 2>/dev/null | wc -l)
    TOTAL_PLAYLISTS=$(find "$PLAYLIST_DIR" -name "*.m3u" 2>/dev/null | wc -l)
    TOTAL_COLLECTIONS=$(find "$MUSIC_DIR" -mindepth 1 -maxdepth 1 -type d ! -name "_playlists" 2>/dev/null | wc -l)
}

sanitize_component() {
    local value="$1"
    value=$(printf '%s' "$value" | sed -E 's#[/\\:*?"<>|]#-#g; s/[[:space:]]+/ /g; s/^ +//; s/ +$//; s/[. ]+$//')
    printf '%s' "$value"
}

count_audio_files() {
    find "$MUSIC_DIR" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.m4a" -o -iname "*.aac" -o -iname "*.opus" -o -iname "*.wav" \) 2>/dev/null | wc -l
}

configure_yt_dlp_runtime() {
    YTDLP_JS_ARGS=()
    if command -v deno >/dev/null 2>&1; then
        YTDLP_JS_ARGS=(--js-runtimes deno)
    elif command -v node >/dev/null 2>&1; then
        YTDLP_JS_ARGS=(--js-runtimes node)
    fi
    # Reduce noisy yt-dlp output while keeping useful info; keep full raw output in logs
    YTDLP_COMMON_ARGS=(--no-warnings --no-progress --newline)
}

download_with_template() {
    local label="$1"
    local url="$2"
    local out_template="$3"
    local album="$4"
    local artist_source="$5"
    local album_artist="$6"
    local genre="$7"
    local before after diff

    echo ""
    divider "-" "$BBLK"
    echo -e " ${BYLW}${BOLD}${label} Download${R}"
    echo -e " ${BCYN}$url${R}"
    echo -e " ${BBLK}$(timestamp) | Genre: $genre${R}"
    divider "-" "$BBLK"
    echo ""

    log "INFO" "$label download: $url | Genre: $genre"

    before=$(count_audio_files)

    local parse_args=()
    if [[ "$album" != "%(album)s" ]]; then
        parse_args+=(--parse-metadata "${album}:%(album)s")
    else
        parse_args+=(--parse-metadata "%(playlist_title,album)s:%(album)s")
    fi
    
    if [[ "$artist_source" != "%(uploader)s" ]]; then
        parse_args+=(--parse-metadata "${artist_source}:%(artist)s")
    else
        parse_args+=(--parse-metadata "%(uploader,artist)s:%(artist)s")
    fi

    if [[ "$album_artist" != "Various Artists" ]]; then
        parse_args+=(--parse-metadata "${album_artist}:%(album_artist)s")
    else
        parse_args+=(--parse-metadata "Various Artists:%(album_artist)s")
    fi
    
    parse_args+=(--parse-metadata "${genre}:%(genre)s")

    "$VENV/bin/yt-dlp" \
        "${YTDLP_JS_ARGS[@]}" "${YTDLP_COMMON_ARGS[@]}" \
        --extract-audio \
        --audio-format "${CURRENT_FORMAT:-mp3}" \
        --audio-quality "${CURRENT_BITRATE:-320k}" \
        --embed-thumbnail \
        --embed-metadata \
        "${parse_args[@]}" \
        -o "$out_template" \
        "$url" 2>&1 | tee -a "$SESSION_LOG" | while IFS= read -r line; do
            # Suppress noisy, unhelpful lines from terminal output while keeping them in logs.
            # Patterns: JS runtime messages, android vr player API lines, metadata parser noise, EJS hints
            if echo "$line" | grep -Ei "Downloading android vr player API JSON|Downloading player [0-9a-f-]+|Solving JS challenges|Remote component challenge solver script|No supported JavaScript runtime could be found|Signature solving failed|challenge solving failed|\[MetadataParser\]|Parsed (album|artist|album_artist|genre)" >/dev/null 2>&1; then
                continue
            fi
            if echo "$line" | grep -qi "error\|fail\|could not"; then
                echo -e " ${BRED}✗ ${line}${R}"
            elif echo "$line" | grep -qi "downloaded\|complete\|success"; then
                echo -e " ${BGRN}✔ ${line}${R}"
            elif echo "$line" | grep -qi "skipping\|already"; then
                echo -e " ${BYLW}⊘ ${line}${R}"
            elif echo "$line" | grep -qi "found\|fetching\|searching\|extracting\|downloading"; then
                echo -e " ${BCYN}⟳ ${line}${R}"
            else
                echo -e " ${DIM}  ${line}${R}"
            fi
        done

    local exit_code="${PIPESTATUS[0]}"
    after=$(count_audio_files)
    diff=$(( after - before ))

    echo ""
    if [[ $exit_code -eq 0 ]]; then
        SESSION_TRACKS=$(( SESSION_TRACKS + diff ))
        echo -e " ${BGRN}${BOLD}✔  Done!${R}  ${BWHT}+${diff} new track(s)${R}"
        log "SUCCESS" "$label: $url | +$diff tracks"
        # Try to request a Freetopify rescan so new files appear quickly in the web UI.
        request_rescan || true
    else
        SESSION_FAILED=$(( SESSION_FAILED + 1 ))
        echo -e " ${BRED}${BOLD}✗  Failed${R}  ${BWHT}(exit $exit_code) — check $SESSION_LOG${R}"
        log "ERROR" "$label failed: $url | exit=$exit_code"
    fi
    echo ""
    divider "-" "$BBLK"
    echo ""
}

metadata_literal() {
    # If the text has spaces, wrap it in double quotes if it doesn't already have them?
    # No, yt-dlp allows plain strings directly in --parse-metadata like "My Title:%(album)s"
    # We just need to pass the string exactly.
    printf '%s' "$1"
}

# ── Header ────────────────────────────────────────────────────
draw_header() {
    clear
    TW=$(tput cols 2>/dev/null || echo 80)
    echo ""
    divider "=" "$BBLU"
    center_text "  🎵  F R E E T O P I F Y   D O W N L O A D E R  v3  🎵  " "$BCYN"
    center_text "${DIM}yt-dlp powered • YouTube → Freetopify${R}" "$BBLK"
    divider "=" "$BBLU"
    echo ""
}

# ── Stats Bar ─────────────────────────────────────────────────
draw_stats() {
    count_library
    local elapsed
    elapsed=$(elapsed_time)

    echo -e " ${BOLD}${BBLU}+--- Library -------------------------------------------+${R}"
    printf " ${BBLU}|${R}  ${BCYN}%-10s${R} ${BWHT}%-8s${R}  ${BMAG}%-10s${R} ${BWHT}%-8s${R}  ${BGRN}%-10s${R} ${BWHT}%-8s${R}  ${BBLU}|${R}\n" \
        "Tracks" "$TOTAL_TRACKS" "Playlists" "$TOTAL_PLAYLISTS" "Collections" "$TOTAL_COLLECTIONS"
    echo -e " ${BBLU}+--- Session -------------------------------------------+${R}"
    printf " ${BBLU}|${R}  ${BGRN}%-10s${R} ${BWHT}%-8s${R}  ${BRED}%-10s${R} ${BWHT}%-8s${R}  ${BYLW}%-10s${R} ${BWHT}%-8s${R}  ${BBLU}|${R}\n" \
        "Downloaded" "$SESSION_TRACKS" "Failed" "$SESSION_FAILED" "Elapsed" "$elapsed"
    printf " ${BBLU}|${R}  ${BCYN}%-10s${R} ${BWHT}%-8s${R}  ${BMAG}%-10s${R} ${BWHT}%-8s${R}  %18s  ${BBLU}|${R}\n" \
        "Format" "${CURRENT_FORMAT^^}" "Genre" "$CURRENT_GENRE" ""
    echo -e " ${BOLD}${BBLU}+------------------------------------------------------+${R}"
    echo ""
}

# ── Detect if URL is a playlist ───────────────────────────────
is_playlist_url() {
    local url="$1"
    if echo "$url" | grep -qE "list="; then
        return 0
    fi
    return 1
}

# ── Download: Playlist Mode ──────────────────────────────────
download_playlist() {
    local url="$1"
    local playlist_title safe_genre safe_playlist

    playlist_title=$("$VENV/bin/yt-dlp" --flat-playlist --print "%(playlist_title)s" "$url" 2>/dev/null | head -1)
    if [[ -z "$playlist_title" ]]; then
        playlist_title=$("$VENV/bin/yt-dlp" --flat-playlist --print "%(title)s" "$url" 2>/dev/null | head -1)
    fi
    [[ -z "$playlist_title" ]] && playlist_title="Playlist"
    safe_genre=$(sanitize_component "$CURRENT_GENRE")
    safe_playlist=$(sanitize_component "$playlist_title")

    log "INFO" "Playlist download: $playlist_title | $url | Genre: $CURRENT_GENRE"
    download_with_template \
        "Playlist" \
        "$url" \
        "$PLAYLIST_ROOT/$safe_genre/$safe_playlist/%(title)s.%(ext)s" \
        "$playlist_title" \
        "%(uploader)s" \
        "Various Artists" \
        "$CURRENT_GENRE"

    generate_m3u "$safe_genre" "$playlist_title"
}

# ── Download: Mix Mode ───────────────────────────────────────
download_mix() {
    local url="$1"
    local mix_title safe_genre safe_mix

    mix_title=$("$VENV/bin/yt-dlp" --flat-playlist --print "%(playlist_title)s" "$url" 2>/dev/null | head -1)
    if [[ -z "$mix_title" ]]; then
        mix_title=$("$VENV/bin/yt-dlp" --flat-playlist --print "%(title)s" "$url" 2>/dev/null | head -1)
    fi
    [[ -z "$mix_title" ]] && mix_title="Mix"
    safe_genre=$(sanitize_component "$CURRENT_GENRE")
    safe_mix=$(sanitize_component "$mix_title")

    log "INFO" "Mix download: $mix_title | $url | Genre: $CURRENT_GENRE"
    download_with_template \
        "Mix" \
        "$url" \
        "$MIX_ROOT/$safe_genre/$safe_mix/%(title)s.%(ext)s" \
        "$(metadata_literal "$mix_title")" \
        "$(metadata_literal "$mix_title")" \
        "$(metadata_literal "$mix_title")" \
        "$CURRENT_GENRE"

    generate_m3u "$safe_genre" "$mix_title"
}

# ── Download: Single Track Mode ──────────────────────────────
download_single() {
    local url="$1"
    local song_title

    song_title=$("$VENV/bin/yt-dlp" --print "%(title)s" "$url" 2>/dev/null | head -1)
    [[ -z "$song_title" ]] && song_title="Unknown Track"

    log "INFO" "Single download: $song_title | $url | Genre: $CURRENT_GENRE"
    download_with_template \
        "Single Track" \
        "$url" \
        "$SINGLE_ROOT/%(uploader)s/%(title)s.%(ext)s" \
        "$(metadata_literal "$song_title")" \
        "$(metadata_literal "$song_title")" \
        "$(metadata_literal "$song_title")" \
        "$CURRENT_GENRE"
}

# ── Download: Podcast Mode ───────────────────────────────────
download_podcast() {
    local url="$1"
    local episode_title

    episode_title=$("$VENV/bin/yt-dlp" --print "%(title)s" "$url" 2>/dev/null | head -1)
    [[ -z "$episode_title" ]] && episode_title="Podcast Episode"

    log "INFO" "Podcast download: $episode_title | $url"
    download_with_template \
        "Podcast" \
        "$url" \
        "$PODCAST_ROOT/%(uploader)s/Episodes/%(title)s.%(ext)s" \
        "$(metadata_literal "$episode_title")" \
        "$(metadata_literal "$episode_title")" \
        "$(metadata_literal "$episode_title")" \
        "Podcast"
}

# ── Generate M3U Playlist ─────────────────────────────────────
generate_m3u() {
    local playlist_genre="$1"
    local playlist_title="$2"

    local safe_playlist safe_genre playlist_folder m3u_file count
    safe_genre=$(sanitize_component "$playlist_genre")
    safe_playlist=$(sanitize_component "$playlist_title")
    playlist_folder="$PLAYLIST_ROOT/$safe_genre/$safe_playlist"

    if [[ ! -d "$playlist_folder" ]]; then
        echo -e " ${BRED}✗ Playlist folder not found: $playlist_folder${R}"
        return 1
    fi

    mkdir -p "$PLAYLIST_DIR/$safe_genre"
    m3u_file="$PLAYLIST_DIR/$safe_genre/${safe_playlist}.m3u"
    {
        echo "#EXTM3U"
        echo "#PLAYLIST:${playlist_title}"
        echo ""
        find "$playlist_folder" -type f \( -iname "*.mp3" -o -iname "*.flac" -o -iname "*.ogg" -o -iname "*.m4a" \) \
            | sort | while IFS= read -r f; do
                realpath --relative-to="$PLAYLIST_DIR" "$f"
            done
    } > "$m3u_file"

    count=$(grep -cve '^\(#\|$\)' "$m3u_file" 2>/dev/null || echo 0)
    echo -e " ${BMAG}♬  Playlist saved:${R} ${BCYN}${safe_playlist}.m3u${R} ${BBLK}(${count} tracks)${R}"
    log "INFO" "M3U: $m3u_file ($count tracks)"
}

# ── Rescan helper — tries Freetopify API first, then fallback note
request_rescan() {
    local api_url="${FREETOPIFY_URL:-http://127.0.0.1:7171}"
    local token="${FREETOPIFY_TOKEN:-}"

    if command -v curl >/dev/null 2>&1; then
        if [[ -n "$token" ]]; then
            if curl -fsS -X POST "$api_url/api/v1/system/rescan" -H "Authorization: Bearer $token" >/dev/null 2>&1; then
                log "INFO" "Triggered Freetopify rescan via API with token"
                return 0
            fi
        else
            # If token missing, still try and fail silently; endpoint requires auth in v1.
            curl -fsS -X POST "$api_url/api/v1/system/rescan" >/dev/null 2>&1 || true
        fi
    fi

    echo -e " ${BYLW}Note:${R} Set ${BCYN}FREETOPIFY_TOKEN${R} then rescan API works:"
    echo -e " ${BCYN}curl -X POST $api_url/api/v1/system/rescan -H 'Authorization: Bearer <token>'${R}"
    log "WARN" "Rescan not triggered automatically; missing/invalid token"
    return 1
}

# ── Help box ──────────────────────────────────────────────────
draw_help() {
    echo ""
    echo -e " ${BBLU}${BOLD}Download:${R}"
    echo -e "  ${BCYN}YouTube playlist URL${R}  → auto-routes to ${BWHT}Playlists/<genre>/<playlist>${R}"
    echo -e "  ${BCYN}YouTube video URL${R}     → auto-routes to ${BWHT}Singles/<uploader>${R}"
    echo -e "  ${BCYN}playlist <url>${R}        → force playlist layout"
    echo -e "  ${BCYN}single <url>${R}          → force singles layout"
    echo -e "  ${BCYN}podcast <url>${R}         → force podcast layout"
    echo -e "  ${BCYN}mix <url>${R}             → force mix layout"
    echo ""
    echo -e " ${BBLU}${BOLD}Commands:${R}"
    echo -e "  ${BYLW}genre <name>${R}    set genre for next download (e.g. ${BWHT}genre Hip Hop${R})"
    echo -e "  ${BYLW}flac${R}            toggle format to FLAC (lossless)"
    echo -e "  ${BYLW}mp3${R}             toggle format back to MP3 320k"
    echo -e "  ${BYLW}stats${R}           refresh library stats"
    echo -e "  ${BYLW}log${R}             show last 20 log lines"
    echo -e "  ${BYLW}clear${R}           redraw screen"
    echo -e "  ${BYLW}help${R}            show this menu"
    echo -e "  ${BYLW}exit / q${R}        quit"
    echo ""
    echo -e " ${BBLU}${BOLD}Genre presets:${R}"
    echo -e "  ${BBLK}Hip Hop, Lofi, Pop, Rock, Metal, Anime, J-Pop, Podcast, Ambient, Classical${R}"
    echo ""
}

# ── Trap Ctrl+C ───────────────────────────────────────────────
trap_exit() {
    echo ""
    echo ""
    divider "=" "$BRED"
    center_text "Session ended — $(timestamp)" "$BYLW"
    echo -e "\n ${BWHT}Downloaded: ${BGRN}${SESSION_TRACKS} tracks${R}  |  ${BRED}Failed: ${SESSION_FAILED}${R}  |  Elapsed: ${BYLW}$(elapsed_time)${R}"
    echo -e " ${BBLK}Log: $SESSION_LOG${R}"
    divider "=" "$BRED"
    echo ""
    log "INFO" "Session ended | tracks=$SESSION_TRACKS failed=$SESSION_FAILED elapsed=$(elapsed_time)"
    exit 0
}
trap trap_exit INT TERM

# ── Pre-flight checks ─────────────────────────────────────────
preflight() {
    local errors=0

    mkdir -p "$LOG_DIR" "$PLAYLIST_DIR" "$PLAYLIST_ROOT" "$SINGLE_ROOT" "$PODCAST_ROOT" "$MIX_ROOT"

    configure_yt_dlp_runtime

    if [[ ! -f "$VENV/bin/yt-dlp" ]]; then
        echo -e " ${BRED}✗ yt-dlp not found: $VENV/bin/yt-dlp${R}"
        echo -e "   Run: ${BCYN}source ~/Venvs/navi/bin/activate && pip install yt-dlp mutagen${R}"
        errors=1
    fi

    if [[ ! -d "$MUSIC_DIR" ]]; then
        echo -e " ${BRED}✗ Music dir missing: $MUSIC_DIR${R}"
        errors=1
    fi

    if ! touch "$MUSIC_DIR/.write_test" 2>/dev/null; then
        echo -e " ${BRED}✗ No write access to $MUSIC_DIR${R}"
        errors=1
    else
        rm -f "$MUSIC_DIR/.write_test"
    fi

    if [[ $errors -gt 0 ]]; then
        echo ""
        echo -e " ${BRED}Pre-flight failed. Fix the above and re-run.${R}"
        exit 1
    fi
}

# ── Format toggle ─────────────────────────────────────────────
set_format() {
    if [[ "$1" == "flac" ]]; then
        CURRENT_FORMAT="flac"
        CURRENT_BITRATE=""
        echo -e " ${BGRN}✔ Format: FLAC (lossless)${R}"
    else
        CURRENT_FORMAT="mp3"
        CURRENT_BITRATE="320k"
        echo -e " ${BGRN}✔ Format: MP3 320kbps${R}"
    fi
    log "INFO" "Format changed to $CURRENT_FORMAT"
}

# ── Main Loop ─────────────────────────────────────────────────
main() {
    preflight
    log "INFO" "=== nvmsdl v2 session started ==="

    draw_header
    draw_stats
    draw_help

    while true; do
        echo -ne " ${BMAG}${BOLD}nvmsdl${R} ${BBLK}[${CURRENT_FORMAT^^}|${CURRENT_GENRE}]${R} ${BBLU}➜${R}  "
        IFS= read -r INPUT

        # Trim whitespace
        INPUT="$(echo "$INPUT" | xargs)"

        # Exit conditions
        if [[ -z "$INPUT" ]]; then
            continue
        elif [[ "$INPUT" == "exit" || "$INPUT" == "q" || "$INPUT" == "quit" ]]; then
            trap_exit

        # Commands
        elif [[ "$INPUT" == "clear" ]]; then
            draw_header
            draw_stats

        elif [[ "$INPUT" == "stats" ]]; then
            echo ""
            draw_stats

        elif [[ "$INPUT" == "help" ]]; then
            draw_help

        elif [[ "$INPUT" == "log" ]]; then
            echo ""
            echo -e " ${BBLU}${BOLD}Last 20 log entries:${R}"
            divider "-" "$BBLK"
            tail -20 "$LOG_FILE" | while IFS= read -r line; do
                if echo "$line" | grep -q "\[ERROR\]"; then
                    echo -e " ${BRED}$line${R}"
                elif echo "$line" | grep -q "\[SUCCESS\]"; then
                    echo -e " ${BGRN}$line${R}"
                else
                    echo -e " ${BBLK}$line${R}"
                fi
            done
            echo ""

        elif [[ "$INPUT" == "flac" ]]; then
            set_format flac

        elif [[ "$INPUT" == "mp3" ]]; then
            set_format mp3

        # Genre command
        elif [[ "$INPUT" =~ ^genre[[:space:]]+ ]]; then
            CURRENT_GENRE="${INPUT#genre }"
            CURRENT_GENRE="$(echo "$CURRENT_GENRE" | xargs)"
            echo -e " ${BGRN}✔ Genre set to: ${BWHT}${CURRENT_GENRE}${R}"
            log "INFO" "Genre changed to $CURRENT_GENRE"

        elif [[ "$INPUT" =~ ^(playlist|pl)[[:space:]]+https?:// ]]; then
            url="${INPUT#* }"
            echo -e " ${BCYN}⟳  Detected: ${BOLD}Playlist${R}"
            download_playlist "$url"
            draw_stats

        elif [[ "$INPUT" =~ ^mix[[:space:]]+https?:// ]]; then
            url="${INPUT#* }"
            echo -e " ${BCYN}⟳  Detected: ${BOLD}Mix${R}"
            download_mix "$url"
            draw_stats

        elif [[ "$INPUT" =~ ^podcast[[:space:]]+https?:// ]]; then
            url="${INPUT#* }"
            echo -e " ${BCYN}⟳  Detected: ${BOLD}Podcast${R}"
            download_podcast "$url"
            draw_stats

        elif [[ "$INPUT" =~ ^(single|song|track)[[:space:]]+https?:// ]]; then
            url="${INPUT#* }"
            echo -e " ${BCYN}⟳  Detected: ${BOLD}Single Track${R}"
            download_single "$url"
            draw_stats

        # YouTube link — auto-detect playlist vs single
        elif echo "$INPUT" | grep -qE "^https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)"; then
            if is_playlist_url "$INPUT"; then
                echo -e " ${BCYN}⟳  Detected: ${BOLD}Playlist${R}"
                download_playlist "$INPUT"
            else
                echo -e " ${BCYN}⟳  Detected: ${BOLD}Single Track${R}"
                download_single "$INPUT"
            fi
            draw_stats

        # Unknown
        else
            echo -e " ${BRED}✗  Unknown input.${R} Type ${BYLW}help${R} or paste a YouTube link."
            log "WARN" "Unknown input: $INPUT"
        fi
    done
}

main
