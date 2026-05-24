import { apiGet, clearToken, getToken } from '/web/js/api.js?v=20260524-13';
import { logout } from '/web/js/auth.js?v=20260524-13';
import { renderDownloads } from '/web/js/downloader.js?v=20260524-13';
import { getCurrentLibraryPath, renderLibrary, goBackOne, hasHistory, showTrackContextMenu } from '/web/js/library.js?v=20260524-13';
import { bindKeyboardShortcuts, getPlayerState, next, onPlayerStateChange, prev, seekToPercent, setVolume, togglePlay, toggleRepeat, toggleShuffle, jumpToQueueIndex } from '/web/js/player.js?v=20260524-13';
import { connectLiveUpdates } from '/web/js/websocket.js?v=20260524-13';

const app = document.getElementById('app');
const queueList = document.getElementById('queue-list');
const globalBackBtn = document.getElementById('btn-global-back');
const projectStart = new Date('2026-05-22T19:13:29+05:30');
let aboutTimer = null;

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

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
  const playIcon = `<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M8 5v14l11-7z"/></svg>`;
  const pauseIcon = `<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>`;
  btn.innerHTML = state.paused ? playIcon : pauseIcon;

  nowTime.textContent = fmtDuration(state.currentTime);
  nowDur.textContent = fmtDuration(state.duration);
  seek.value = state.duration ? String(Math.floor((state.currentTime / state.duration) * 100)) : '0';
  vol.value = String(Math.round((state.volume || 0) * 100));

  document.getElementById('btn-shuffle').classList.toggle('ctl-active', state.shuffle);
  document.getElementById('btn-repeat').classList.toggle('ctl-active', state.repeat);

  if (track?.path) {
    const artUrl = `/thumbnail/${encodeURIComponent(track.path)}`;
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
      <div class="queue-item${i === state.queueIndex ? ' playing' : ''}" data-idx="${i}">
        ${i === state.queueIndex ? '▶ ' : `${i + 1}. `}${escapeHtml(t.title || t.name || 'Track')}
      </div>
    `).join('');
  }
}

function bindNowBar() {
  document.getElementById('btn-shuffle').addEventListener('click', () => toggleShuffle());
  document.getElementById('btn-prev').addEventListener('click', () => prev());
  document.getElementById('btn-play').addEventListener('click', () => togglePlay());
  document.getElementById('btn-next').addEventListener('click', () => next());
  document.getElementById('btn-repeat').addEventListener('click', () => toggleRepeat());
  document.getElementById('seek').addEventListener('input', (e) => seekToPercent(Number(e.target.value)));
  document.getElementById('volume').addEventListener('input', (e) => setVolume(Number(e.target.value) / 100));

  const nowBar = document.getElementById('now-bar');
  nowBar.style.cursor = 'pointer';
  nowBar.addEventListener('click', (e) => {
    // don't navigate if clicking buttons, sliders, etc.
    if (e.target.closest('button') || e.target.closest('input')) return;
    if (window.location.hash !== '#player') {
      window.location.hash = '#player';
    }
  });

  if (queueList) {
    queueList.addEventListener('click', (e) => {
      const item = e.target.closest('.queue-item');
      if (item) {
        const idx = Number(item.getAttribute('data-idx'));
        jumpToQueueIndex(idx);
      }
    });

    queueList.addEventListener('contextmenu', (e) => {
      const item = e.target.closest('.queue-item');
      if (item) {
        const idx = Number(item.getAttribute('data-idx'));
        const state = getPlayerState();
        const track = state.queue[idx];
        if (track) {
          showTrackContextMenu(e, track, document.getElementById('app-view'));
        }
      }
    });
  }
}

function setActiveLink(route) {
  document.querySelectorAll('.side-link').forEach((a) => {
    a.classList.toggle('active', a.getAttribute('href') === `#${route}`);
  });
}

function formatElapsed(start, end = new Date()) {
  let current = new Date(end.getTime());
  let years = current.getUTCFullYear() - start.getUTCFullYear();
  let months = current.getUTCMonth() - start.getUTCMonth();
  let days = current.getUTCDate() - start.getUTCDate();
  let hours = current.getUTCHours() - start.getUTCHours();
  let minutes = current.getUTCMinutes() - start.getUTCMinutes();
  let seconds = current.getUTCSeconds() - start.getUTCSeconds();

  if (seconds < 0) { seconds += 60; minutes -= 1; }
  if (minutes < 0) { minutes += 60; hours -= 1; }
  if (hours < 0) { hours += 24; days -= 1; }
  if (days < 0) {
    const prevMonth = new Date(Date.UTC(current.getUTCFullYear(), current.getUTCMonth(), 0));
    days += prevMonth.getUTCDate();
    months -= 1;
  }
  if (months < 0) { months += 12; years -= 1; }

  return { years, months, days, hours, minutes, seconds };
}

function formatElapsedLabel(diff) {
  return `${diff.years}y ${diff.months}m ${diff.days}d ${String(diff.hours).padStart(2, '0')}h ${String(diff.minutes).padStart(2, '0')}m ${String(diff.seconds).padStart(2, '0')}s`;
}

function renderAboutView() {
  const socialLinks = [
    {
      href: 'https://github.com/flexcreates', label: 'GitHub', title: 'GitHub profile', icon: 'github',
      svg: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.65.5.5 5.82.5 12.37c0 5.24 3.44 9.69 8.2 11.27.6.11.82-.27.82-.58 0-.29-.01-1.06-.02-2.08-3.34.75-4.04-1.66-4.04-1.66-.55-1.44-1.35-1.83-1.35-1.83-1.1-.78.08-.77.08-.77 1.22.09 1.86 1.28 1.86 1.28 1.08 1.9 2.84 1.35 3.53 1.03.11-.8.42-1.35.76-1.66-2.66-.31-5.46-1.37-5.46-6.1 0-1.35.47-2.45 1.24-3.32-.12-.31-.54-1.55.12-3.24 0 0 1.01-.33 3.3 1.27a11.1 11.1 0 0 1 6.01 0c2.29-1.6 3.3-1.27 3.3-1.27.66 1.69.24 2.93.12 3.24.77.87 1.24 1.97 1.24 3.32 0 4.74-2.81 5.78-5.48 6.09.43.37.82 1.1.82 2.22 0 1.61-.02 2.9-.02 3.29 0 .31.21.69.83.57A12.01 12.01 0 0 0 23.5 12.37C23.5 5.82 18.35.5 12 .5z"/></svg>`,
    },
    {
      href: 'https://instagram.com/flexcreates', label: 'Instagram', title: 'Instagram profile', icon: 'instagram',
      svg: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5Zm0 2a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3H7Zm5 2.5A5.5 5.5 0 1 1 6.5 12 5.51 5.51 0 0 1 12 6.5Zm0 2A3.5 3.5 0 1 0 15.5 12 3.5 3.5 0 0 0 12 8.5Zm5.75-3.65a1.2 1.2 0 1 1-1.2 1.2 1.2 1.2 0 0 1 1.2-1.2Z"/></svg>`,
    },
  ];

  const startLabel = projectStart.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'medium' });

  const features = [
    { emoji: '🏠', tag: 'Local-first',   title: 'Home server & LAN ready',  desc: 'Zero CDN dependency. Runs fast inside your own network — instant access, no internet needed.' },
    { emoji: '🔐', tag: 'Guest-friendly', title: 'PIN-gated sharing',         desc: 'Share read-only access via a simple PIN. Library stays safe, listening stays easy.' },
    { emoji: '📱', tag: 'Responsive',     title: 'Every screen, perfectly fit', desc: 'Adapts to desktop, tablet, and phone. Layout, spacing, and player stay balanced everywhere.' },
  ];

  app.innerHTML = `
    <section class="about-shell">

      <div class="about-hero">
        <article class="about-card about-main-card">
          <div class="about-title">
            <div>
              <div class="about-kicker">✦ Developer profile</div>
              <h2>About Freetopify</h2>
              <p class="about-subtitle">Private, folder-first music hosting with a clean browser client, local-network access, and a focused admin workflow.</p>
            </div>
            <div class="about-badge">✦ Official</div>
          </div>

          <div class="about-links-block">
            <div class="about-stat-label">Connect</div>
            <div class="social-row">
              ${socialLinks.map(link => `
                <a class="social-link" href="${link.href}" target="_blank" rel="noreferrer" title="${link.title}">
                  <span class="social-icon ${link.icon}">${link.svg}</span>
                  <span>${link.label}</span>
                </a>
              `).join('')}
            </div>
          </div>

          <div class="about-grid">
            <div class="about-stat">
              <div class="about-stat-label">Developer</div>
              <div class="about-stat-value">Aditya Singh</div>
              <div class="about-stat-small">@flexcreates</div>
            </div>
            <div class="about-stat">
              <div class="about-stat-label">First build</div>
              <div class="about-stat-value">${escapeHtml(startLabel)}</div>
              <div class="about-stat-small">Day zero 🚀</div>
            </div>
            <div class="about-stat countdown">
              <div class="about-stat-label">⏱ Live for</div>
              <div class="about-stat-value" id="project-elapsed">Loading...</div>
              <div class="about-stat-small">yr · mo · d · hr · min · sec</div>
            </div>
          </div>
        </article>

        <aside class="about-card donate-card">
          <div>
            <div class="about-kicker">☕ Support</div>
            <h2 class="donate-heading">Buy a Coffee</h2>
            <p class="about-subtitle">If Freetopify has made your music life better, a coffee would mean the world. 💜</p>
          </div>
          <a class="donate-cta" href="#" onclick="return false;">☕ Add donation link</a>
          <p class="donate-placeholder">Placeholder — swap the link above with your Ko-fi, Buy Me a Coffee, or PayPal when ready.</p>
        </aside>
      </div>

      <section class="about-strip">
        ${features.map(f => `
          <article class="about-mini-card">
            <div class="about-mini-icon">${f.emoji}</div>
            <div class="about-stat-label">${f.tag}</div>
            <div class="about-mini-title">${f.title}</div>
            <div class="about-mini-copy">${f.desc}</div>
          </article>
        `).join('')}
      </section>

    </section>
  `;

  const elapsedEl = document.getElementById('project-elapsed');
  const updateElapsed = () => { if (elapsedEl) elapsedEl.textContent = formatElapsedLabel(formatElapsed(projectStart, new Date())); };
  updateElapsed();
  if (aboutTimer) clearInterval(aboutTimer);
  aboutTimer = setInterval(updateElapsed, 1000);
}



function renderPlayerView() {
  const s = getPlayerState();
  app.innerHTML = `
    <section class="panel player-hero">
      <button id="btn-minimize" class="ctl secondary-btn" style="position:absolute;top:14px;left:14px;z-index:10;width:38px;height:38px;padding:0;border-radius:50%;" title="Go back">
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>
      </button>
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
          <div id="hero-title" class="hero-title">${escapeHtml(s.track?.title || 'Nothing playing')}</div>
          <div id="hero-path" class="hero-path">${escapeHtml(s.track?.path || '')}</div>
        </div>
      </div>
    </section>
  `;
  updateNowBar();
  const btnMin = document.getElementById('btn-minimize');
  if (btnMin) {
    btnMin.addEventListener('click', () => {
      history.back();
    });
  }
}

function renderSettings() {
  app.innerHTML = `
    <section class="panel">
      <div class="section-title">Settings</div>
      <div class="form-grid" style="gap:10px;">
        <div style="display:flex;gap:10px;flex-wrap:wrap;">
          <button id="check" class="primary-btn">Check Connection</button>
          <button id="logout" class="secondary-btn">Logout</button>
        </div>
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

  if (route !== 'about' && aboutTimer) {
    clearInterval(aboutTimer);
    aboutTimer = null;
  }

  if (route === 'library') await renderLibrary(app, getCurrentLibraryPath());
  else if (route === 'downloads') renderDownloads(app);
  else if (route === 'player') renderPlayerView();
  else if (route === 'settings') renderSettings();
  else if (route === 'about') renderAboutView();
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
