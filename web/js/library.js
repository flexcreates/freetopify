import { apiGet } from '/web/js/api.js';
import { setQueue } from '/web/js/player.js';

let currentPath = '';

function esc(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function fmtDuration(seconds) {
  if (!seconds || Number.isNaN(seconds)) return '--:--';
  const sec = Math.floor(seconds % 60).toString().padStart(2, '0');
  const min = Math.floor(seconds / 60);
  return `${min}:${sec}`;
}

function prettyName(track) {
  const base = track.title || track.name || 'Unknown Track';
  return base.replace(/\.(mp3|flac|ogg|m4a|aac|opus|wav|wv)$/i, '').trim();
}

function breadcrumb(path) {
  const chunks = path ? path.split('/') : [];
  if (!chunks.length) return '';

  // Hide technical trailing "Singles" when already inside uploader singles path.
  if (chunks.length >= 2 && chunks[chunks.length - 1] === 'Singles') {
    chunks.pop();
  }

  let acc = '';
  const links = [];
  for (const part of chunks) {
    acc = acc ? `${acc}/${part}` : part;
    links.push(`<a href="#library" data-path="${esc(acc)}">${esc(part)}</a>`);
  }
  return links.join(' / ');
}

function parentPath(path) {
  if (!path) return '';
  const parts = path.split('/').filter(Boolean);
  if (parts.length <= 1) return '';
  return parts.slice(0, -1).join('/');
}

export async function renderLibrary(mount, path = '') {
  currentPath = path;
  const data = await apiGet(`/api/v1/library/browse?path=${encodeURIComponent(path)}`);
  const folders = data.items.filter((x) => x.type === 'folder');
  const tracks = data.items.filter((x) => x.type === 'track').map((t) => ({
    ...t,
    title: prettyName(t),
    thumbnail: `/thumbnail/${encodeURIComponent(t.path)}`,
  }));

  mount.innerHTML = `
    <section class="panel">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
        <div class="section-title" style="margin:0;">Library</div>
        <button id="nav-back" class="secondary-btn">← Back</button>
      </div>
      ${breadcrumb(path) ? `<div class="crumb">${breadcrumb(path)}</div>` : ''}

      <div class="section-title">Folders</div>
      <div class="folder-grid">
        ${folders.map((f) => `
          <button class="folder-card" data-folder="${esc(f.path)}">
            <div><strong>${esc(f.name)}</strong></div>
            <div class="track-ext">${f.track_count} tracks</div>
          </button>
        `).join('') || '<div class="track-ext empty-note">No subfolders</div>'}
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px;">
        <div class="section-title" style="margin:0;">Tracks</div>
        <button id="play-all" class="primary-btn">Play All</button>
      </div>

      <table class="track-table">
        <tbody>
          ${tracks.map((t, i) => `
            <tr>
              <td>
                <button class="track-row-btn" data-track-index="${i}">
                  <img class="mini-thumb-img" src="${t.thumbnail}" data-thumb="${i}" alt="" />
                  <div class="mini-thumb-fallback" data-fallback="${i}">♪</div>
                  <div class="track-name">${esc(t.title)}</div>
                  <div class="track-ext">${esc((t.format || '').toUpperCase())}</div>
                  <div class="track-time">${fmtDuration(t.duration)}</div>
                </button>
              </td>
            </tr>
          `).join('') || '<tr><td class="track-ext empty-note">No tracks in this folder</td></tr>'}
        </tbody>
      </table>
    </section>
  `;

  mount.querySelectorAll('[data-folder]').forEach((el) => {
    el.addEventListener('click', () => renderLibrary(mount, el.getAttribute('data-folder') || ''));
  });

  mount.querySelectorAll('[data-path]').forEach((el) => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      renderLibrary(mount, el.getAttribute('data-path') || '');
    });
  });

  mount.querySelectorAll('[data-track-index]').forEach((el) => {
    el.addEventListener('click', () => {
      const idx = Number(el.getAttribute('data-track-index'));
      setQueue(tracks, idx);
      window.location.hash = '#player';
    });
  });

  tracks.forEach((t, i) => {
    const img = mount.querySelector(`[data-thumb="${i}"]`);
    const fallback = mount.querySelector(`[data-fallback="${i}"]`);
    if (!img || !fallback) return;
    const token = localStorage.getItem('freetopify_token') || '';
    img.src = `${t.thumbnail}?token=${encodeURIComponent(token)}`;
    img.addEventListener('error', () => {
      img.style.display = 'none';
      fallback.style.display = 'grid';
    });
    img.addEventListener('load', () => {
      fallback.style.display = 'none';
    });
  });

  const backBtn = mount.querySelector('#nav-back');
  if (backBtn) {
    const parent = parentPath(path);
    backBtn.disabled = !path;
    backBtn.addEventListener('click', () => renderLibrary(mount, parent));
  }

  const playAll = mount.querySelector('#play-all');
  if (playAll) {
    playAll.disabled = tracks.length === 0;
    playAll.addEventListener('click', () => {
      if (!tracks.length) return;
      setQueue(tracks, 0);
      window.location.hash = '#player';
    });
  }
}

export function getCurrentLibraryPath() {
  return currentPath;
}
