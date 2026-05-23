let audio;
let queue = [];
let originalQueue = [];
let queueIndex = -1;
let shuffleMode = false;
let repeatMode = false;
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
    shuffle: shuffleMode,
    repeat: repeatMode,
  };
}

export function setQueue(items, startIndex = 0) {
  originalQueue = items.slice();
  if (shuffleMode) {
    const currentItem = originalQueue[startIndex];
    const rest = originalQueue.filter((_, i) => i !== startIndex);
    // Fisher-Yates shuffle
    for (let i = rest.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [rest[i], rest[j]] = [rest[j], rest[i]];
    }
    queue = currentItem ? [currentItem, ...rest] : rest;
    queueIndex = 0;
  } else {
    queue = originalQueue.slice();
    queueIndex = startIndex;
  }
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
  } else if (repeatMode && queue.length > 0) {
    queueIndex = 0;
    playCurrent();
  } else {
    const a = ensurePlayer();
    a.pause();
    a.currentTime = 0;
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

export function toggleShuffle() {
  shuffleMode = !shuffleMode;
  const current = currentTrack();
  if (shuffleMode) {
    const rest = originalQueue.filter((t) => t.path !== current?.path);
    for (let i = rest.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [rest[i], rest[j]] = [rest[j], rest[i]];
    }
    queue = current ? [current, ...rest] : rest;
    queueIndex = 0;
  } else {
    queue = originalQueue.slice();
    queueIndex = queue.findIndex((t) => t.path === current?.path);
    if (queueIndex === -1) queueIndex = 0;
  }
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
