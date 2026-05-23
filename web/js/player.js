let audio;
let queue = [];
let queueIndex = -1;
let listeners = [];
const tokenKey = 'freetopify_token';
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
  audio.addEventListener('ended', () => next());
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
  };
}

export function setQueue(items, startIndex = 0) {
  queue = items.slice();
  queueIndex = startIndex;
  playCurrent();
  notify();
}

export function playCurrent() {
  const a = ensurePlayer();
  const item = currentTrack();
  if (!item) return;
  const token = localStorage.getItem(tokenKey) || '';
  const streamPath = `/stream/${encodeURI(item.path)}`;
  a.src = token ? `${streamPath}?token=${encodeURIComponent(token)}` : streamPath;
  a.play().catch(() => {});
  notify();
}

export function togglePlay() {
  const a = ensurePlayer();
  if (a.paused) a.play().catch(() => {});
  else a.pause();
  notify();
}

export function next() {
  if (queueIndex + 1 < queue.length) {
    queueIndex += 1;
    playCurrent();
  }
  notify();
}

export function prev() {
  if (queueIndex > 0) {
    queueIndex -= 1;
    playCurrent();
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
