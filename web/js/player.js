let audio;
let queue = [];
let queueIndex = -1;
let shuffleMode = false;
let repeatMode = false;
let listeners = [];
const volumeKey = 'freetopify_volume';

function notify() {
  const state = getPlayerState();
  for (const fn of listeners) fn(state);
}

function ensurePlayer() {
  if (audio) return audio;
  audio = new Audio();
  audio.preload = 'metadata';
  const saved = Number(localStorage.getItem(volumeKey));
  audio.volume = Number.isFinite(saved) ? Math.max(0, Math.min(1, saved)) : 0.8;
  audio.addEventListener('ended', () => {
    console.log('[PLAYER] audio "ended" event fired.');
    next();
  });
  audio.addEventListener('timeupdate', notify);
  audio.addEventListener('play', notify);
  audio.addEventListener('pause', notify);
  audio.addEventListener('loadedmetadata', notify);
  return audio;
}

function currentTrack() {
  if (queueIndex < 0 || queueIndex >= queue.length) return null;
  return queue[queueIndex];
}

export function onPlayerStateChange(fn) {
  listeners.push(fn);
  return () => {
    listeners = listeners.filter((f) => f !== fn);
  };
}

export function getPlayerState() {
  const a = ensurePlayer();
  return {
    paused: a.paused,
    currentTime: a.currentTime,
    duration: Number.isFinite(a.duration) ? a.duration : 0,
    src: a.src,
    volume: a.volume,
    queue,
    queueIndex,
    track: currentTrack(),
    shuffle: shuffleMode,
    repeat: repeatMode,
  };
}

export function setQueue(items, startIndex = 0) {
  queue = items.slice();
  queueIndex = startIndex;
  playCurrent();
  notify();
}

export function jumpToQueueIndex(idx) {
  if (idx >= 0 && idx < queue.length) {
    queueIndex = idx;
    playCurrent();
    notify();
  }
}

export function addToQueue(item) {
  const queuedItem = { ...item, isQueued: true };
  if (queue.length === 0) {
    queue.push(queuedItem);
    queueIndex = 0;
    playCurrent();
  } else {
    // Find the end of the manually queued block
    let insertIdx = queueIndex + 1;
    while (insertIdx < queue.length && queue[insertIdx].isQueued) {
      insertIdx++;
    }
    queue.splice(insertIdx, 0, queuedItem);
  }
  notify();
}

export function playNext(item) {
  const queuedItem = { ...item, isQueued: true };
  if (queue.length === 0) {
    queue.push(queuedItem);
    queueIndex = 0;
    playCurrent();
  } else {
    queue.splice(queueIndex + 1, 0, queuedItem);
  }
  notify();
}

export function removeFromQueue(idx) {
  if (idx >= 0 && idx < queue.length) {
    queue.splice(idx, 1);
    if (idx < queueIndex) {
      queueIndex--; // Shift current playing index back
    } else if (idx === queueIndex) {
      // We removed the currently playing track
      if (queue.length === 0) {
        queueIndex = -1;
        const a = ensurePlayer();
        a.pause();
        a.removeAttribute('data-playing-path');
        a.src = '';
      } else {
        // Play the next track (which has now fallen into current queueIndex)
        if (queueIndex >= queue.length) queueIndex = 0;
        playCurrent();
      }
    }
    notify();
  }
}

export function playCurrent() {
  const a = ensurePlayer();
  const item = currentTrack();
  if (!item) return;
  // Fix: encodeURIComponent for the path part to handle special characters correctly
  const encodedPath = item.path.split('/').map(encodeURIComponent).join('/');
  const streamPath = `/stream/${encodedPath}`;
  const newSrc = streamPath;

  console.log(`[PLAYER] playCurrent() called. item.path: ${item.path}`);
  if (a.getAttribute('data-playing-path') === item.path) {
    // Exact same track (e.g. single song loop) - reload to guarantee restart on streams
    console.log(`[PLAYER] Exact same track detected. Reloading for repeat.`);
    a.src = newSrc;
    a.load();
    a.play().catch(e => console.error('[PLAYER] Play error:', e));
  } else {
    console.log(`[PLAYER] New track detected. Updating src and calling load().`);
    a.setAttribute('data-playing-path', item.path);
    a.src = newSrc;
    a.load();
    a.play().catch(e => console.error('[PLAYER] Play error:', e));
  }
  notify();
}

export function togglePlay() {
  const a = ensurePlayer();
  if (a.paused) a.play().catch(() => {});
  else a.pause();
  notify();
}

export function next() {
  if (queue.length === 0) return;

  const current = queue[queueIndex];

  if (shuffleMode) {
    if (current && current.isQueued) {
      queue.splice(queueIndex, 1);
    }
    let nextIdx = Math.floor(Math.random() * queue.length);
    if (queue.length > 1 && nextIdx === queueIndex) {
      nextIdx = (nextIdx + 1) % queue.length;
    }
    queueIndex = nextIdx;
    playCurrent();
  } else {
    if (current && current.isQueued) {
      // Consume the queued track
      queue.splice(queueIndex, 1);
      if (queueIndex >= queue.length) queueIndex = 0;
      playCurrent();
    } else {
      if (queueIndex + 1 < queue.length) {
        queueIndex += 1;
        playCurrent();
      } else {
        if (repeatMode) {
          queueIndex = 0;
          playCurrent();
        } else {
          // Stop playback at end of playlist
          const a = ensurePlayer();
          a.pause();
          a.currentTime = 0;
          queueIndex = 0;
          a.removeAttribute('data-playing-path');
          a.src = '';
        }
      }
    }
  }
  notify();
}

export function prev() {
  const a = ensurePlayer();
  // If more than 3 seconds in, just restart the current song
  if (a.currentTime > 3) {
    a.currentTime = 0;
    notify();
    return;
  }

  if (queue.length === 0) return;

  if (shuffleMode) {
    let prevIdx = Math.floor(Math.random() * queue.length);
    if (queue.length > 1 && prevIdx === queueIndex) {
      prevIdx = (prevIdx - 1 + queue.length) % queue.length;
    }
    queueIndex = prevIdx;
    playCurrent();
  } else {
    if (queueIndex > 0) {
      queueIndex -= 1;
      playCurrent();
    } else {
      // Wrap around to the last song (Permanent Loop)
      queueIndex = queue.length - 1;
      playCurrent();
    }
  }
  notify();
}

export function seekToPercent(percent) {
  const a = ensurePlayer();
  if (!a.duration || Number.isNaN(a.duration)) return;
  a.currentTime = Math.max(0, Math.min(a.duration, (percent / 100) * a.duration));
  notify();
}

export function seekBy(seconds) {
  const a = ensurePlayer();
  a.currentTime = Math.max(0, a.currentTime + seconds);
  notify();
}

export function setVolume(value) {
  const a = ensurePlayer();
  a.volume = Math.max(0, Math.min(1, value));
  localStorage.setItem(volumeKey, String(a.volume));
  notify();
}

export function toggleShuffle() {
  shuffleMode = !shuffleMode;
  notify();
}

export function toggleRepeat() {
  repeatMode = !repeatMode;
  notify();
}

export function bindKeyboardShortcuts() {
  window.addEventListener('keydown', (e) => {
    if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
    if (e.code === 'Space') {
      e.preventDefault();
      togglePlay();
    } else if (e.key === 'ArrowLeft') {
      seekBy(-5);
    } else if (e.key === 'ArrowRight') {
      seekBy(5);
    } else if (e.key.toLowerCase() === 'm') {
      const a = ensurePlayer();
      a.muted = !a.muted;
      notify();
    }
  });
}
