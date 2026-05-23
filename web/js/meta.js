import { apiGet, apiPost, getToken } from '/web/js/api.js';

function createInput(labelText, name, value = '') {
  const wrap = document.createElement('div');
  wrap.style.display = 'grid';
  wrap.style.gap = '6px';
  const label = document.createElement('label');
  label.textContent = labelText;
  label.style.fontSize = '0.9rem';
  const input = document.createElement('input');
  input.name = name;
  input.value = value ?? '';
  input.className = 'text-input';
  wrap.appendChild(label);
  wrap.appendChild(input);
  return { wrap, input };
}

function createTextarea(labelText, name, value = '', rows = 4) {
  const wrap = document.createElement('div');
  wrap.style.display = 'grid';
  wrap.style.gap = '6px';
  const label = document.createElement('label');
  label.textContent = labelText;
  label.style.fontSize = '0.9rem';
  const ta = document.createElement('textarea');
  ta.name = name;
  ta.value = value ?? '';
  ta.rows = rows;
  ta.style.width = '100%';
  ta.className = 'text-input';
  wrap.appendChild(label);
  wrap.appendChild(ta);
  return { wrap, input: ta };
}

export async function openMetaEditor(path) {
  let data;
  try {
    data = await apiGet(`/api/v1/library/meta?path=${encodeURIComponent(path)}`);
  } catch (err) {
    alert('Failed to load metadata: ' + (err.message || err));
    return;
  }

  const modal = document.createElement('div');
  modal.className = 'meta-modal';

  const panel = document.createElement('div');
  panel.className = 'meta-panel panel';

  const title = document.createElement('div');
  title.className = 'section-title';
  title.textContent = 'Edit Metadata';

  const pathEl = document.createElement('div');
  pathEl.style.fontSize = '0.85rem';
  pathEl.style.color = 'var(--muted)';
  pathEl.textContent = path;

  const form = document.createElement('form');
  form.style.display = 'grid';
  form.style.gap = '8px';

  const tags = data.tags || {};
  const titleField = createInput('Title', 'title', tags.TIT2 || tags.title || '');
  const artistField = createInput('Artist', 'artist', tags.TPE1 || tags.artist || '');
  const albumField = createInput('Album', 'album', tags.TALB || tags.album || '');
  const trackField = createInput('Track #', 'tracknumber', tags.TRCK || tags.TRACKNUMBER || tags.tracknumber || '');
  const genreField = createInput('Genre', 'genre', tags.TCON || tags.genre || '');
  const yearField = createInput('Year', 'year', tags.TYER || tags.year || '');
  const commentField = createTextarea('Comment', 'comment', tags.COMM || tags.comment || '', 3);
  const lyricsField = createTextarea('Lyrics', 'lyrics', tags.USLT || tags.lyrics || '', 6);

  // cover preview
  const coverWrap = document.createElement('div');
  coverWrap.style.display = 'flex';
  coverWrap.style.gap = '12px';
  coverWrap.style.alignItems = 'center';
  const coverImg = document.createElement('img');
  coverImg.style.width = '96px';
  coverImg.style.height = '96px';
  coverImg.style.objectFit = 'cover';
  coverImg.style.borderRadius = '8px';
  coverImg.style.display = 'none';
  const coverLabel = document.createElement('div');
  coverLabel.style.color = 'var(--muted)';
  coverLabel.style.fontSize = '0.85rem';
  coverLabel.textContent = 'Cover art';
  coverWrap.appendChild(coverImg);
  coverWrap.appendChild(coverLabel);

  // quick buttons
  const quickWrap = document.createElement('div');
  quickWrap.style.display = 'flex';
  quickWrap.style.gap = '8px';
  const btnFilename = document.createElement('button');
  btnFilename.type = 'button';
  btnFilename.className = 'secondary-btn';
  btnFilename.textContent = 'Filename → Title';
  btnFilename.addEventListener('click', () => {
    const parts = path.split('/');
    const fname = parts[parts.length - 1] || path;
    titleField.input.value = fname.replace(/\.(mp3|flac|ogg|m4a|aac|opus|wav|wv)$/i, '').trim();
  });
  const btnInferArtist = document.createElement('button');
  btnInferArtist.type = 'button';
  btnInferArtist.className = 'secondary-btn';
  btnInferArtist.textContent = 'Infer Artist from Path';
  btnInferArtist.addEventListener('click', () => {
    const parts = path.split('/').filter(Boolean);
    if (parts.length >= 2) artistField.input.value = parts[parts.length - 2];
  });
  quickWrap.appendChild(btnFilename);
  quickWrap.appendChild(btnInferArtist);

  form.appendChild(quickWrap);
  form.appendChild(coverWrap);
  // upload control
  const uploadWrap = document.createElement('div');
  uploadWrap.style.display = 'flex';
  uploadWrap.style.alignItems = 'center';
  uploadWrap.style.gap = '8px';
  const fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.accept = 'image/*';
  fileInput.style.flex = '1';
  const uploadBtn = document.createElement('button');
  uploadBtn.type = 'button';
  uploadBtn.className = 'secondary-btn';
  uploadBtn.textContent = 'Upload Cover';
  uploadBtn.addEventListener('click', async () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return alert('Choose an image first');
    uploadBtn.disabled = true;
    uploadBtn.textContent = 'Uploading...';
    try {
      const formData = new FormData();
      formData.append('file', f);
      // path passed as query param - include in URL
      const token = getToken();
      const res = await fetch(`/api/v1/library/cover?path=${encodeURIComponent(path)}`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      // refresh cover preview
      coverImg.src = `/thumbnail/${encodeURIComponent(path)}?token=${encodeURIComponent(token)}&t=${Date.now()}`;
      coverImg.style.display = 'block';
      alert('Cover uploaded');
    } catch (err) {
      alert('Upload failed: ' + (err.message || err));
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = 'Upload Cover';
    }
  });
  uploadWrap.appendChild(fileInput);
  uploadWrap.appendChild(uploadBtn);
  form.appendChild(uploadWrap);
  form.appendChild(titleField.wrap);
  form.appendChild(artistField.wrap);
  form.appendChild(albumField.wrap);
  form.appendChild(trackField.wrap);
  form.appendChild(genreField.wrap);
  form.appendChild(yearField.wrap);
  form.appendChild(commentField.wrap);
  form.appendChild(lyricsField.wrap);

  const actions = document.createElement('div');
  actions.style.display = 'flex';
  actions.style.justifyContent = 'flex-end';
  actions.style.gap = '8px';

  const cancel = document.createElement('button');
  cancel.type = 'button';
  cancel.className = 'secondary-btn';
  cancel.textContent = 'Cancel';
  cancel.addEventListener('click', () => document.body.removeChild(modal));

  const save = document.createElement('button');
  save.type = 'submit';
  save.className = 'primary-btn';
  save.textContent = 'Save';

  actions.appendChild(cancel);
  actions.appendChild(save);

  form.appendChild(actions);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = { path, tags: {} };
    if (titleField.input.value) {
      payload.tags.title = titleField.input.value;
      payload.tags.TIT2 = titleField.input.value;
    }
    if (artistField.input.value) {
      payload.tags.artist = artistField.input.value;
      payload.tags.TPE1 = artistField.input.value;
    }
    if (albumField.input.value) {
      payload.tags.album = albumField.input.value;
      payload.tags.TALB = albumField.input.value;
    }
    if (trackField.input.value) {
      payload.tags.tracknumber = trackField.input.value;
      payload.tags.TRCK = trackField.input.value;
    }
    if (genreField.input.value) {
      payload.tags.genre = genreField.input.value;
      payload.tags.TCON = genreField.input.value;
    }
    if (yearField.input.value) {
      payload.tags.year = yearField.input.value;
      payload.tags.TYER = yearField.input.value;
    }
    if (commentField.input.value) {
      payload.tags.comment = commentField.input.value;
      payload.tags.COMM = commentField.input.value;
    }
    if (lyricsField.input.value) {
      payload.tags.lyrics = lyricsField.input.value;
      payload.tags.USLT = lyricsField.input.value;
    }

    save.disabled = true;
    save.textContent = 'Saving...';

    // simple validation
    const errors = [];
    if (yearField.input.value && !/^\d{2,4}$/.test(yearField.input.value)) errors.push('Year must be numeric');
    if (trackField.input.value && !/^\d+(\/\d+)?$/.test(trackField.input.value)) errors.push('Track # should be a number or a number/total like 3/12');
    if (errors.length) { alert(errors.join('\n')); save.disabled = false; save.textContent = 'Save'; return; }

    try {
      await apiPost('/api/v1/library/meta', payload);
      document.body.removeChild(modal);
      window.dispatchEvent(new CustomEvent('freetopify:meta-saved', { detail: { path } }));
    } catch (err) {
      alert('Save failed: ' + (err.message || err));
      save.disabled = false;
      save.textContent = 'Save';
    }
  });

  panel.appendChild(title);
  panel.appendChild(pathEl);
  panel.appendChild(form);
  modal.appendChild(panel);
  document.body.appendChild(modal);

  // load cover art via thumbnail endpoint (if available)
  (async () => {
    try {
      const token = localStorage.getItem('freetopify_token') || '';
      const url = `/thumbnail/${encodeURIComponent(path)}?token=${encodeURIComponent(token)}`;
      const img = new Image();
      img.onload = () => {
        coverImg.src = url;
        coverImg.style.display = 'block';
      };
      img.onerror = () => { coverImg.style.display = 'none'; };
      img.src = url;
    } catch (_) {
      coverImg.style.display = 'none';
    }
  })();

  // focus first field
  setTimeout(() => titleField.input.focus(), 50);
}

export default openMetaEditor;
