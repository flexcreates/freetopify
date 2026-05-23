import { apiGet, apiPost, apiDelete } from '/web/js/api.js';
import { openMetaEditor } from '/web/js/meta.js';
import { setQueue } from '/web/js/player.js';

let currentPath = '';

const HISTORY_KEY = 'freetopify_path_history';

function getHistory() {
  try { return JSON.parse(sessionStorage.getItem(HISTORY_KEY) || '[]'); } catch { return []; }
}

function pushHistory(path) {
  const hist = getHistory();
  // avoid duplicates at top
  if (hist.length === 0 || hist[hist.length - 1] !== path) {
    hist.push(path);
    sessionStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
  }
}

function popHistory() {
  const hist = getHistory();
  if (!hist.length) return null;
  const last = hist.pop();
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
  return last;
}

export function goBackOne() {
  const hist = getHistory();
  if (!hist.length) return null;
  const prev = hist.pop();
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(hist));
  return prev;
}

export function hasHistory() {
  const h = getHistory();
  return h.length > 0;
}

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

// Context menu: cut/copy/paste/delete/rename/meta
  const fmClipboardKey = 'freetopify_fs_clipboard';

  function setClipboard(obj) {
    sessionStorage.setItem(fmClipboardKey, JSON.stringify(obj));
  }
  function getClipboard() {
    const v = sessionStorage.getItem(fmClipboardKey);
    return v ? JSON.parse(v) : null;
  }

  function hideMenu(menu) {
    if (menu && menu.parentNode) menu.parentNode.removeChild(menu);
  }

  function showMenu(items, x, y) {
    hideMenu(document.getElementById('fm-context-menu'));
    const menu = document.createElement('div');
    menu.id = 'fm-context-menu';
    menu.style.position = 'fixed';
    menu.style.left = x + 'px';
    menu.style.top = y + 'px';
    menu.style.zIndex = 9999;
    menu.style.background = '#071526';
    menu.style.border = '1px solid rgba(126,188,255,0.12)';
    menu.style.padding = '6px';
    menu.style.borderRadius = '6px';
    menu.style.boxShadow = '0 8px 24px rgba(2,10,22,0.6)';
    items.forEach((it) => {
      const el = document.createElement('div');
      el.textContent = it.label;
      el.style.padding = '6px 10px';
      el.style.cursor = 'pointer';
      el.style.color = '#dfeefb';
      el.addEventListener('click', () => {
        try { it.onClick(); } catch (e) { console.error(e); }
        hideMenu(menu);
      });
      el.addEventListener('mouseenter', () => el.style.background = 'rgba(126,188,255,0.06)');
      el.addEventListener('mouseleave', () => el.style.background = 'transparent');
      menu.appendChild(el);
    });
    document.body.appendChild(menu);
    setTimeout(() => {
      const onDoc = (e) => { if (!menu.contains(e.target)) hideMenu(menu); };
      document.addEventListener('click', onDoc, { once: true });
    }, 10);
  }

  // use `apiPost` from /web/js/api.js to ensure Authorization header

  
export async function renderLibrary(mount, path = '', isBack = false) {
  // push previous path into history for back navigation
  const prev = currentPath;
  if (!isBack && typeof prev === 'string' && prev !== path) {
    pushHistory(prev);
    window.dispatchEvent(new CustomEvent('freetopify:history-changed'));
  }
  currentPath = path;
  const data = await apiGet(`/api/v1/library/browse?path=${encodeURIComponent(path)}`);
  const folders = data.items.filter((x) => x.type === 'folder');
  const tracks = data.items.filter((x) => x.type === 'track').map((t) => ({
    ...t,
    title: prettyName(t),
    thumbnail: `/thumbnail/${encodeURIComponent(t.path)}`,
  }));
  const token = localStorage.getItem('freetopify_token') || '';

  mount.innerHTML = `
    <section class="panel">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
        <div class="section-title" style="margin:0;">Library</div>
      </div>
      ${breadcrumb(path) ? `<div class="crumb">${breadcrumb(path)}</div>` : ''}

      <div class="section-title">Folders</div>
      <div class="folder-grid">
        ${folders.map((f) => `
          <button class="folder-card" data-folder="${esc(f.path)}">
            <div class="folder-card-cover-wrap">
              <img class="folder-card-cover" src="/api/v1/library/cover?path=${encodeURIComponent(f.path)}&t=${Date.now()}${token ? '&token='+encodeURIComponent(token) : ''}" alt="" />
            </div>
            <div class="folder-card-body">
              <strong>${esc(f.name)}</strong>
              <div class="track-ext">${f.track_count} tracks${f.child_count ? `, ${f.child_count} folders` : ''}</div>
            </div>
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

  // immediate setup: show loaded images
  mount.querySelectorAll('.folder-card-cover').forEach((img) => {
    img.addEventListener('error', () => { img.style.display = 'none'; });
    img.addEventListener('load', () => { img.style.display = 'block'; img.style.opacity = 1; });
  });

  // in-panel back button removed — use global back button in header

  const playAll = mount.querySelector('#play-all');
  if (playAll) {
    playAll.disabled = tracks.length === 0;
    playAll.addEventListener('click', () => {
      if (!tracks.length) return;
      setQueue(tracks, 0);
      window.location.hash = '#player';
    });
  }

  // Attach contextmenu to folders
  mount.querySelectorAll('[data-folder]').forEach((el) => {
    el.addEventListener('contextmenu', (ev) => {
      ev.preventDefault();
      const folder = el.getAttribute('data-folder');
      const items = [
        { label: 'Cut', onClick: () => setClipboard({ action: 'cut', type: 'folder', path: folder }) },
        { label: 'Copy', onClick: () => setClipboard({ action: 'copy', type: 'folder', path: folder }) },
        { label: 'Paste', onClick: async () => {
            const cb = getClipboard();
            if (!cb) return alert('Clipboard empty');
            if (cb.path === folder) return alert('Cannot paste into same folder');
            try {
              if (cb.action === 'cut') await apiPost('/api/v1/library/move', { src: cb.path, dst_folder: folder });
              else await apiPost('/api/v1/library/copy', { src: cb.path, dst_folder: folder });
              await renderLibrary(mount, getCurrentLibraryPath());
            } catch (err) { alert(err.message || err); }
          }
        },
        { label: 'Rename', onClick: async () => {
            const name = prompt('New name for folder:', folder.split('/').pop() || '');
            if (!name) return;
            try {
              await apiPost('/api/v1/library/rename', { path: folder, new_name: name });
              await renderLibrary(mount, getCurrentLibraryPath());
            } catch (err) { alert(err.message || err); }
          }
        },
        { label: 'Delete', onClick: async () => {
            if (!confirm('Delete folder and all contents?')) return;
            try { await apiPost('/api/v1/library/delete', { path: folder }); await renderLibrary(mount, getCurrentLibraryPath()); } catch (err) { alert(err.message || err); }
          }
        }
      ];
      showMenu(items, ev.clientX, ev.clientY);
    });
  });

  // Attach contextmenu to tracks
  mount.querySelectorAll('[data-track-index]').forEach((el) => {
    el.addEventListener('contextmenu', (ev) => {
      ev.preventDefault();
      const idx = Number(el.getAttribute('data-track-index'));
      const track = tracks[idx];
      const path = track.path;
      const items = [
        { label: 'Cut', onClick: () => setClipboard({ action: 'cut', type: 'track', path }) },
        { label: 'Copy', onClick: () => setClipboard({ action: 'copy', type: 'track', path }) },
        { label: 'Paste', onClick: async () => {
            const cb = getClipboard();
            if (!cb) return alert('Clipboard empty');
            try {
              const dst = getCurrentLibraryPath();
              if (cb.action === 'cut') await apiPost('/api/v1/library/move', { src: cb.path, dst_folder: dst });
              else await apiPost('/api/v1/library/copy', { src: cb.path, dst_folder: dst });
              await renderLibrary(mount, getCurrentLibraryPath());
            } catch (err) { alert(err.message || err); }
          }
        },
        { label: 'Rename', onClick: async () => {
            const name = prompt('New filename:', track.name || track.title || '');
            if (!name) return;
            try { await apiPost('/api/v1/library/rename', { path, new_name: name }); await renderLibrary(mount, getCurrentLibraryPath()); } catch (err) { alert(err.message || err); }
          }
        },
        { label: 'Delete', onClick: async () => {
            if (!confirm('Delete this file?')) return;
            try { await apiPost('/api/v1/library/delete', { path }); await renderLibrary(mount, getCurrentLibraryPath()); } catch (err) { alert(err.message || err); }
          }
        },
          { label: 'View Metadata', onClick: async () => {
              try {
                const data = await apiGet(`/api/v1/library/meta?path=${encodeURIComponent(path)}`);
                alert(JSON.stringify(data, null, 2));
              } catch (err) { alert(err.message || err); }
            }
          },
          { label: 'Edit Metadata', onClick: async () => {
              try {
                await openMetaEditor(path);
              } catch (err) { alert(err.message || err); }
            }
          }
      ];
      showMenu(items, ev.clientX, ev.clientY);
    });
  });
}

export function getCurrentLibraryPath() {
  return currentPath;
}

export function showTrackContextMenu(ev, track, mount) {
  ev.preventDefault();
  const path = track.path;
  const items = [
    { label: 'Cut', onClick: () => setClipboard({ action: 'cut', type: 'track', path }) },
    { label: 'Copy', onClick: () => setClipboard({ action: 'copy', type: 'track', path }) },
    { label: 'Paste', onClick: async () => {
        const cb = getClipboard();
        if (!cb) return alert('Clipboard empty');
        try {
          const dst = getCurrentLibraryPath();
          if (cb.action === 'cut') await apiPost('/api/v1/library/move', { src: cb.path, dst_folder: dst });
          else await apiPost('/api/v1/library/copy', { src: cb.path, dst_folder: dst });
          if (mount) await renderLibrary(mount, getCurrentLibraryPath());
        } catch (err) { alert(err.message || err); }
      }
    },
    { label: 'Rename', onClick: async () => {
        const name = prompt('New filename:', track.name || track.title || '');
        if (!name) return;
        try { await apiPost('/api/v1/library/rename', { path, new_name: name }); if (mount) await renderLibrary(mount, getCurrentLibraryPath()); } catch (err) { alert(err.message || err); }
      }
    },
    { label: 'Delete', onClick: async () => {
        if (!confirm('Delete this file?')) return;
        try { await apiPost('/api/v1/library/delete', { path }); if (mount) await renderLibrary(mount, getCurrentLibraryPath()); } catch (err) { alert(err.message || err); }
      }
    },
    { label: 'View Metadata', onClick: async () => {
        try {
          const data = await apiGet(`/api/v1/library/meta?path=${encodeURIComponent(path)}`);
          alert(JSON.stringify(data, null, 2));
        } catch (err) { alert(err.message || err); }
      }
    },
    { label: 'Edit Metadata', onClick: async () => {
        try {
          await openMetaEditor(path);
        } catch (err) { alert(err.message || err); }
      }
    }
  ];
  showMenu(items, ev.clientX, ev.clientY);
}
