import { apiPost, clearToken, setToken } from '/web/js/api.js';

export async function login(username, password) {
  const result = await apiPost('/auth/login', { username, password });
  setToken(result.access_token);
  document.cookie = `freetopify_token=${encodeURIComponent(result.access_token)}; Path=/; SameSite=Lax; Max-Age=${Math.max(0, Number(result.expires_in) || 0)}`;
  return result;
}

export function logout() {
  clearToken();
  document.cookie = 'freetopify_token=; Path=/; SameSite=Lax; Max-Age=0';
  window.location.href = '/web/login.html';
}

function bindLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const button = form.querySelector('button');
    button.disabled = true;
    button.textContent = 'Logging in...';

    try {
      await login(username, password);
      window.location.href = '/web/index.html#library';
    } catch (err) {
      alert(err.message || 'Login failed');
    } finally {
      button.disabled = false;
      button.textContent = 'Login';
    }
  });
}

bindLoginForm();
