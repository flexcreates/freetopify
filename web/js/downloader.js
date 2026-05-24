import { apiGet, apiPost } from '/web/js/api.js';

// ── Helpers ────────────────────────────────────────────────
function esc(v) {
  return String(v ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');
}

function fmt(bytes) {
  if (!bytes) return '';
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

// ── State ──────────────────────────────────────────────────
let selectedFolders = new Set();   // Set of { path, absolute } objects (keyed by path)
let allFolders      = [];          // flat list from server

// ── Main render ────────────────────────────────────────────
export function renderDownloads(mount) {
  selectedFolders = new Set();
  allFolders = [];

  mount.innerHTML = `
    <section class="panel dl-shell">

      <!-- ── URL + Controls bar ── -->
      <div class="dl-top-bar">
        <div class="dl-top-bar-inner">
          <input id="dl-url" class="dl-url-input" placeholder="⏎  Paste a YouTube URL — single track or full playlist…" autocomplete="off" spellcheck="false" />
          <div class="dl-controls-row">
            <div class="dl-format-group">
              <button class="dl-fmt-btn active" data-fmt="mp3">MP3</button>
              <button class="dl-fmt-btn" data-fmt="flac">FLAC</button>
            </div>
            <button id="dl-submit" class="dl-submit-btn" disabled>
              <span class="dl-submit-icon">↓</span> Download
            </button>
          </div>
        </div>
        <div id="dl-selection-bar" class="dl-selection-bar hidden">
          <span id="dl-sel-text"></span>
          <button id="dl-clear-sel" class="dl-clear-btn">✕ Clear</button>
        </div>
      </div>

      <!-- ── Folder picker ── -->
      <div class="dl-section">
        <div class="dl-section-head">
          <span class="dl-section-label">📂 Pick destination folder(s)</span>
          <span class="dl-section-hint">Click one or more — download goes to all selected</span>
          <button id="dl-refresh-btn" class="dl-refresh-btn" title="Reload folders">↻</button>
        </div>
        <div id="dl-folder-grid" class="dl-folder-grid">
          <div class="dl-folder-skeleton"></div>
          <div class="dl-folder-skeleton"></div>
          <div class="dl-folder-skeleton"></div>
          <div class="dl-folder-skeleton"></div>
        </div>
      </div>

      <!-- ── Active jobs ── -->
      <div class="dl-section" id="dl-jobs-section">
        <div class="dl-section-head">
          <span class="dl-section-label">⚡ Recent Jobs</span>
        </div>
        <div id="dl-jobs-list" class="dl-jobs-list">
          <p class="dl-empty-msg">No recent downloads</p>
        </div>
      </div>

      <!-- ── Permanent history ── -->
      <div class="dl-section" id="dl-history-section">
        <div class="dl-section-head">
          <span class="dl-section-label">📜 Download History</span>
          <span class="dl-section-hint">Saved locally on device · never deleted</span>
        </div>
        <div id="dl-history-list" class="dl-history-list">
          <p class="dl-empty-msg">No history yet</p>
        </div>
      </div>

    </section>

    <!-- ── New-folder modal ── -->
    <div id="dl-modal" class="dl-modal-overlay hidden" role="dialog" aria-modal="true">
      <div class="dl-modal-box">
        <p class="dl-modal-title">✨ Create new folder</p>
        <input id="dl-modal-input" class="dl-modal-input" placeholder="Folder name (e.g. Chill Vibes)" maxlength="80" autocomplete="off" />
        <p id="dl-modal-error" class="dl-modal-error hidden"></p>
        <div class="dl-modal-actions">
          <button id="dl-modal-cancel" class="dl-modal-cancel">Cancel</button>
          <button id="dl-modal-confirm" class="dl-modal-confirm">Create</button>
        </div>
      </div>
    </div>
  `;

  // ── Wire up controls ───────────────────────────────────
  const urlInput   = mount.querySelector('#dl-url');
  const submitBtn  = mount.querySelector('#dl-submit');
  const selBar     = mount.querySelector('#dl-selection-bar');
  const selText    = mount.querySelector('#dl-sel-text');
  const clearBtn   = mount.querySelector('#dl-clear-sel');
  const refreshBtn = mount.querySelector('#dl-refresh-btn');
  const jobsList   = mount.querySelector('#dl-jobs-list');

  // Format toggle
  let chosenFormat = 'mp3';
  mount.querySelectorAll('.dl-fmt-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      mount.querySelectorAll('.dl-fmt-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      chosenFormat = btn.dataset.fmt;
    });
  });

  // URL → enable/disable submit
  urlInput.addEventListener('input', syncSubmit);

  // Clear selection
  clearBtn.addEventListener('click', () => {
    selectedFolders.clear();
    syncSubmit();
    renderFolders();
  });

  // Refresh
  refreshBtn.addEventListener('click', loadFolders);

  // Submit
  submitBtn.addEventListener('click', handleDownload);
  urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') handleDownload(); });

  // Modal wiring
  const modal       = mount.querySelector('#dl-modal');
  const modalInput  = mount.querySelector('#dl-modal-input');
  const modalErr    = mount.querySelector('#dl-modal-error');
  const modalCancel = mount.querySelector('#dl-modal-cancel');
  const modalConfirm= mount.querySelector('#dl-modal-confirm');

  modalCancel.addEventListener('click', closeModal);
  modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
  modalConfirm.addEventListener('click', confirmNewFolder);
  modalInput.addEventListener('keydown', e => { if (e.key === 'Enter') confirmNewFolder(); });

  function openModal() {
    modalInput.value = '';
    modalErr.classList.add('hidden');
    modal.classList.remove('hidden');
    setTimeout(() => modalInput.focus(), 50);
  }
  function closeModal() { modal.classList.add('hidden'); }

  async function confirmNewFolder() {
    const name = modalInput.value.trim();
    if (!name) return;
    modalConfirm.disabled = true;
    modalErr.classList.add('hidden');
    try {
      const res = await apiPost('/api/v1/library/mkdir', { path: name });
      closeModal();
      await loadFolders();
      // auto-select the new folder
      const created = allFolders.find(f => f.path === res.path || f.name === name);
      if (created) {
        selectedFolders.add(created.path);
        syncSubmit();
        renderFolders();
      }
    } catch (err) {
      modalErr.textContent = err.message || 'Could not create folder';
      modalErr.classList.remove('hidden');
    } finally {
      modalConfirm.disabled = false;
    }
  }

  // ── Folder loading ─────────────────────────────────────
  async function loadFolders() {
    const grid = mount.querySelector('#dl-folder-grid');
    grid.innerHTML = `
      <div class="dl-folder-skeleton"></div>
      <div class="dl-folder-skeleton"></div>
      <div class="dl-folder-skeleton"></div>
    `;
    try {
      const data = await apiGet('/api/v1/library/browse?path=');
      allFolders = (data.items || []).filter(i => i.type === 'folder');
      renderFolders();
    } catch (err) {
      grid.innerHTML = `<p class="dl-empty-msg">Could not load folders: ${esc(err.message)}</p>`;
    }
  }

  function renderFolders() {
    const grid = mount.querySelector('#dl-folder-grid');

    // New-folder card always first
    const newCard = `
      <button class="dl-folder-card dl-new-folder-card" id="dl-new-folder-btn">
        <span class="dl-folder-plus">＋</span>
        <span class="dl-folder-card-name">New Folder</span>
      </button>
    `;

    const folderCards = allFolders.map(f => {
      const isSelected = selectedFolders.has(f.path);
      const trackLabel = f.track_count ? `${f.track_count} track${f.track_count !== 1 ? 's' : ''}` : 'empty';
      return `
        <button class="dl-folder-card${isSelected ? ' selected' : ''}" data-path="${esc(f.path)}" data-abs="${esc(f.absolute_path || '')}">
          <span class="dl-folder-icon">◈</span>
          <span class="dl-folder-card-name">${esc(f.name)}</span>
          <span class="dl-folder-card-meta">${esc(trackLabel)}</span>
          ${isSelected ? '<span class="dl-folder-check">✓</span>' : ''}
        </button>
      `;
    }).join('');

    grid.innerHTML = newCard + folderCards;

    // Bind new-folder
    mount.querySelector('#dl-new-folder-btn').addEventListener('click', openModal);

    // Bind folder toggles
    grid.querySelectorAll('.dl-folder-card[data-path]').forEach(card => {
      card.addEventListener('click', () => {
        const path = card.dataset.path;
        if (selectedFolders.has(path)) {
          selectedFolders.delete(path);
        } else {
          selectedFolders.add(path);
        }
        syncSubmit();
        renderFolders();
      });
    });

    // Update selection bar
    if (selectedFolders.size > 0) {
      const names = allFolders
        .filter(f => selectedFolders.has(f.path))
        .map(f => f.name).join(', ');
      selText.textContent = `${selectedFolders.size} folder${selectedFolders.size > 1 ? 's' : ''} selected: ${names}`;
      selBar.classList.remove('hidden');
    } else {
      selBar.classList.add('hidden');
    }
  }

  function syncSubmit() {
    const hasUrl = urlInput.value.trim().length > 0;
    const hasDest = selectedFolders.size > 0;
    submitBtn.disabled = !(hasUrl && hasDest);
    submitBtn.classList.toggle('ready', hasUrl && hasDest);
  }

  // ── Download handler ───────────────────────────────────
  async function handleDownload() {
    const url = urlInput.value.trim();
    if (!url || selectedFolders.size === 0) return;

    submitBtn.disabled = true;
    submitBtn.textContent = '…';

    const targets = allFolders.filter(f => selectedFolders.has(f.path));

    for (const folder of targets) {
      const body = {
        url,
        type: 'auto',
        genre: folder.name,
        format: chosenFormat,
        bitrate: '320k',
        output_dir: folder.absolute_path || null,
      };
      try {
        const res = await apiPost('/api/v1/download/start', body);
        spawnJobCard(jobsList, res.job_id, folder.name, url);
      } catch (err) {
        spawnErrorCard(jobsList, folder.name, err.message);
      }
    }

    // Reset
    urlInput.value = '';
    selectedFolders.clear();
    renderFolders();
    syncSubmit();
    submitBtn.textContent = '';
    submitBtn.innerHTML = '<span class="dl-submit-icon">↓</span> Download';
  }

  // ── Job card ───────────────────────────────────────────
  function spawnJobCard(container, jobId, folderName, url) {
    // Remove empty message
    container.querySelector('.dl-empty-msg')?.remove();

    const card = document.createElement('div');
    card.className = 'dl-job-card';
    card.id = `job-${jobId}`;
    card.innerHTML = `
      <div class="dl-job-header">
        <span class="dl-job-badge queued">queued</span>
        <span class="dl-job-folder">📂 ${esc(folderName)}</span>
        <span class="dl-job-url">${esc(url.length > 55 ? url.slice(0, 55) + '…' : url)}</span>
        <button class="dl-job-toggle" title="Toggle log">▾</button>
      </div>
      <pre class="dl-job-log"></pre>
    `;
    container.prepend(card);

    const badge  = card.querySelector('.dl-job-badge');
    const log    = card.querySelector('.dl-job-log');
    const toggle = card.querySelector('.dl-job-toggle');

    toggle.addEventListener('click', () => {
      log.classList.toggle('collapsed');
      toggle.textContent = log.classList.contains('collapsed') ? '▸' : '▾';
    });

    // Stream progress
    const es = new EventSource(`/api/v1/download/progress/${jobId}`);
    es.onmessage = evt => {
      try {
        const d = JSON.parse(evt.data);
        if (d.log) { log.textContent += d.log + '\n'; log.scrollTop = log.scrollHeight; }
        if (d.status) {
          badge.textContent = d.status;
          badge.className = `dl-job-badge ${d.status}`;
        }
        if (d.status === 'done' || d.status === 'failed') { es.close(); refreshJobs(); }
      } catch { log.textContent += evt.data + '\n'; }
    };
    es.onerror = () => { es.close(); refreshJobs(); };
  }

  function spawnErrorCard(container, folderName, message) {
    container.querySelector('.dl-empty-msg')?.remove();
    const card = document.createElement('div');
    card.className = 'dl-job-card error';
    card.innerHTML = `
      <div class="dl-job-header">
        <span class="dl-job-badge failed">error</span>
        <span class="dl-job-folder">📂 ${esc(folderName)}</span>
        <span class="dl-job-url">${esc(message)}</span>
      </div>
    `;
    container.prepend(card);
  }

  // ── Recent jobs refresh ────────────────────────────────
  async function refreshJobs() {
    try {
      const { items } = await apiGet('/api/v1/download/jobs');
      const list = mount.querySelector('#dl-jobs-list');
      if (!items?.length) { list.innerHTML = '<p class="dl-empty-msg">No recent downloads</p>'; return; }

      // Only show jobs whose card doesn't already exist (live-streamed)
      items.slice(0, 10).forEach(j => {
        const existing = mount.querySelector(`#job-${j.job_id}`);
        if (existing) {
          const badge = existing.querySelector('.dl-job-badge');
          if (badge) { badge.textContent = j.status; badge.className = `dl-job-badge ${j.status}`; }
        }
      });
    } catch { /* ignore */ }
  }

  // ── Download history ───────────────────────────────────
  async function loadHistory() {
    const list = mount.querySelector('#dl-history-list');
    if (!list) return;
    try {
      const { items } = await apiGet('/api/v1/download/history');
      if (!items?.length) {
        list.innerHTML = '<p class="dl-empty-msg">No history yet — downloads will appear here permanently</p>';
        return;
      }
      list.innerHTML = items.map(entry => `
        <div class="dl-history-row">
          <span class="dl-history-icon">♫</span>
          <span class="dl-history-title">${esc(entry.title)}</span>
          <span class="dl-history-folder">📂 ${esc(entry.folder)}</span>
          <span class="dl-history-format dl-fmt-pill">${esc(entry.format?.toUpperCase() || '')}</span>
          <span class="dl-history-ts">${esc(entry.ts)}</span>
        </div>
      `).join('');
    } catch {
      list.innerHTML = '<p class="dl-empty-msg">Could not load history</p>';
    }
  }

  // ── Init ───────────────────────────────────────────────
  loadFolders();
  loadHistory();
  const timer = setInterval(refreshJobs, 3000);
  window.addEventListener('hashchange', () => clearInterval(timer), { once: true });
}
