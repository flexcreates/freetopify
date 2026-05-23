const tokenKey = 'freetopify_token';

export function getToken() {
  return localStorage.getItem(tokenKey) || '';
}

export function setToken(token) {
  localStorage.setItem(tokenKey, token);
}

export function clearToken() {
  localStorage.removeItem(tokenKey);
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const data = await response.json();
      if (data.detail) message = data.detail;
    } catch (_) {}
    throw new Error(message);
  }

  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  return response.text();
}

export function apiGet(path) { return request(path); }
export function apiPost(path, payload) { return request(path, { method: 'POST', body: JSON.stringify(payload) }); }
export function apiDelete(path) { return request(path, { method: 'DELETE' }); }
