import { apiGet, apiPost, getToken } from '/web/js/api.js';

export function renderDownloads(mount) {
  mount.innerHTML = `
    <section class="panel">
      <div class="section-title">Downloads</div>
      <form id="dl-form" class="form-grid">
        <input id="dl-url" class="text-input" placeholder="YouTube URL" required />
        <input id="dl-genre" class="text-input" placeholder="Genre" value="Music" />
        <select id="dl-format" class="select-input"><option value="mp3">MP3</option><option value="flac">FLAC</option></select>
        <button type="submit" class="primary-btn">Start Download</button>
      </form>
      <pre id="dl-log" class="log"></pre>
      <div class="section-title" style="margin-top:12px;">Recent Jobs</div>
      <ul id="dl-jobs" class="queue-list"></ul>
    </section>
  `;

  const form = mount.querySelector('#dl-form');
  const logEl = mount.querySelector('#dl-log');
  const jobsEl = mount.querySelector('#dl-jobs');
  let jobsTimer = null;

  async function refreshJobs() {
    try {
      const jobs = await apiGet('/api/v1/download/jobs');
      jobsEl.innerHTML = jobs.items.slice(0, 20)
        .map((j) => `<li><strong>${j.status}</strong> - ${j.url}</li>`)
        .join('') || '<li>No jobs</li>';
    } catch (err) {
      jobsEl.innerHTML = `<li>${err.message}</li>`;
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    logEl.textContent = '';
    const body = {
      url: mount.querySelector('#dl-url').value.trim(),
      type: 'auto',
      genre: mount.querySelector('#dl-genre').value.trim() || 'Music',
      format: mount.querySelector('#dl-format').value,
      bitrate: '320k',
    };

    try {
      const res = await apiPost('/api/v1/download/start', body);
      const token = getToken();
      const es = new EventSource(`/api/v1/download/progress/${res.job_id}?token=${encodeURIComponent(token)}`);
      es.onmessage = (evt) => {
        logEl.textContent += `${evt.data}\n`;
        logEl.scrollTop = logEl.scrollHeight;
        refreshJobs();
      };
      es.onerror = () => {
        es.close();
        refreshJobs();
      };
    } catch (err) {
      logEl.textContent = err.message;
    }
  });

  refreshJobs();
  jobsTimer = setInterval(refreshJobs, 2000);
  window.addEventListener('hashchange', () => {
    if (jobsTimer) clearInterval(jobsTimer);
  }, { once: true });
}
