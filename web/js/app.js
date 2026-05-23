import { apiGet, clearToken, getToken } from '/web/js/api.js';
import { logout } from '/web/js/auth.js';
import { renderDownloads } from '/web/js/downloader.js';
import { getCurrentLibraryPath, renderLibrary, goBackOne, hasHistory } from '/web/js/library.js';
import { bindKeyboardShortcuts, getPlayerState, next, onPlayerStateChange, prev, seekToPercent, setVolume, togglePlay } from '/web/js/player.js';
import { connectLiveUpdates } from '/web/js/websocket.js';

const app = document.getElementById('app');
const queueList = document.getElementById('queue-list');
const globalBackBtn = document.getElementById('btn-global-back');

function updateGlobalBackButton() {
  if (!globalBackBtn) return;
  globalBackBtn.disabled = !hasHistory();
}

if (globalBackBtn) {
  globalBackBtn.addEventListener('click', async () => {
    const prev = goBackOne();
    if (prev !== null) {
      await renderLibrary(app, prev, true);
      updateGlobalBackButton();
    }
  });
}

function fmtDuration(seconds) {
  if (!seconds || Number.isNaN(seconds)) return '0:00';
  const sec = Math.floor(seconds % 60).toString().padStart(2, '0');
  const min = Math.floor(seconds / 60);
  return `${min}:${sec}`;
}

function updateNowBar() {
  const state = getPlayerState();
  const track = state.track;

  const titleEl = document.getElementById('now-title');
  const subEl = document.getElementById('now-sub');
  const btn = document.getElementById('btn-play');
  const nowTime = document.getElementById('now-time');
  const nowDur = document.getElementById('now-dur');
  const seek = document.getElementById('seek');
  const vol = document.getElementById('volume');
  const thumbImg = document.getElementById('now-thumb-img');
  const thumbFallback = document.getElementById('now-thumb-fallback');
  const heroArt = document.getElementById('hero-art');
  const heroFallback = document.getElementById('hero-fallback');
  const disk = document.getElementById('vinyl-disk');

  titleEl.textContent = track?.title || 'Nothing playing';
  subEl.textContent = track?.path || 'Pick a song from Library';
  btn.textContent = state.paused ? '▶' : '⏸';

  nowTime.textContent = fmtDuration(state.currentTime);
  nowDur.textContent = fmtDuration(state.duration);
  seek.value = state.duration ? String(Math.floor((state.currentTime / state.duration) * 100)) : '0';
  vol.value = String(Math.round((state.volume || 0) * 100));

  if (track?.path) {
    const token = localStorage.getItem('freetopify_token') || '';
    const artUrl = `/thumbnail/${encodeURIComponent(track.path)}?token=${encodeURIComponent(token)}`;
    thumbImg.src = artUrl;
    thumbImg.style.display = 'block';
    thumbFallback.style.display = 'none';
    thumbImg.onerror = () => {
      thumbImg.style.display = 'none';
      thumbFallback.style.display = 'grid';
    };

    if (heroArt) {
      heroArt.src = artUrl;
      heroArt.style.display = 'block';
      if (heroFallback) heroFallback.style.display = 'none';
      heroArt.onerror = () => {
        heroArt.style.display = 'none';
        if (heroFallback) heroFallback.style.display = 'grid';
      };
    }
  } else {
    thumbImg.style.display = 'none';
    thumbFallback.style.display = 'grid';
    if (heroArt) heroArt.style.display = 'none';
    if (heroFallback) heroFallback.style.display = 'grid';
  }

  if (disk) {
    disk.classList.toggle('spinning', !state.paused && !!track);
  }

  const heroTitle = document.getElementById('hero-title');
  const heroPath = document.getElementById('hero-path');
  if (heroTitle) heroTitle.textContent = track?.title || 'Nothing playing';
  if (heroPath) heroPath.textContent = track?.path || '';

  if (!state.queue.length) {
    queueList.textContent = 'No tracks queued';
  } else {
    queueList.innerHTML = state.queue.map((t, i) => `
      <div style="padding:7px 0; border-bottom:1px solid rgba(98,168,255,.1); color:${i === state.queueIndex ? '#e6f2ff' : '#9db8d2'};">
        ${i + 1}. ${t.title || t.name || 'Track'}
      </div>
    `).join('');
  }
}

function bindNowBar() {
  document.getElementById('btn-prev').addEventListener('click', () => prev());
  document.getElementById('btn-play').addEventListener('click', () => togglePlay());
  document.getElementById('btn-next').addEventListener('click', () => next());
  document.getElementById('seek').addEventListener('input', (e) => seekToPercent(Number(e.target.value)));
  document.getElementById('volume').addEventListener('input', (e) => setVolume(Number(e.target.value) / 100));
}

function setActiveLink(route) {
  document.querySelectorAll('.side-link').forEach((a) => {
    a.classList.toggle('active', a.getAttribute('href') === `#${route}`);
  });
}

function renderPlayerView() {
  const s = getPlayerState();
  app.innerHTML = `
    <section class="panel player-hero">
      <div class="player-ambient"></div>
      <div class="player-stage">
        <div class="vinyl-wrap">
          <div id="vinyl-disk" class="vinyl-disk ${!s.paused && s.track ? 'spinning' : ''}">
            <div class="vinyl-grooves"></div>
            <img id="hero-art" class="vinyl-art" alt="" />
            <div id="hero-fallback" class="vinyl-fallback">♪</div>
            <div class="vinyl-core"></div>
          </div>
        </div>
        <div class="player-meta">
          <div class="section-title">Now Playing</div>
          <div id="hero-title" class="hero-title">${s.track?.title || 'Nothing playing'}</div>
          <div id="hero-path" class="hero-path">${s.track?.path || ''}</div>
        </div>
      </div>
    </section>
  `;
  updateNowBar();
}

function renderSettings() {
  app.innerHTML = `
    <section class="panel">
      <div class="section-title">Settings</div>
      <div class="form-grid">
        <button id="check" class="primary-btn">Check Connection</button>
        <button id="logout" class="primary-btn">Logout</button>
        <pre id="status" class="log"></pre>
      </div>
    </section>
  `;

  app.querySelector('#check').addEventListener('click', async () => {
    const status = app.querySelector('#status');
    try {
      const health = await apiGet('/api/v1/system/health');
      const me = await apiGet('/auth/me');
      status.textContent = JSON.stringify({ health, me }, null, 2);
    } catch (err) {
      status.textContent = err.message;
    }
  });

  app.querySelector('#logout').addEventListener('click', logout);
}

async function renderRoute() {
  if (!getToken()) {
    window.location.href = '/web/login.html';
    return;
  }

  try {
    await apiGet('/auth/me');
  } catch (_) {
    clearToken();
    window.location.href = '/web/login.html';
    return;
  }

  const route = (window.location.hash || '#library').replace('#', '');
  setActiveLink(route);

  if (route === 'library') await renderLibrary(app, getCurrentLibraryPath());
  else if (route === 'downloads') renderDownloads(app);
  else if (route === 'player') renderPlayerView();
  else if (route === 'settings') renderSettings();
  else window.location.hash = '#library';
}

window.addEventListener('hashchange', renderRoute);
bindKeyboardShortcuts();
bindNowBar();
onPlayerStateChange(updateNowBar);
connectLiveUpdates((payload) => {
  if (payload?.event === 'library_update' && (window.location.hash || '#library') === '#library') {
    renderLibrary(app, getCurrentLibraryPath()).catch(() => {});
  }
});
updateNowBar();
renderRoute();
// Keep global back button state in sync
window.addEventListener('freetopify:history-changed', updateGlobalBackButton);
window.addEventListener('freetopify:meta-saved', updateGlobalBackButton);
updateGlobalBackButton();
