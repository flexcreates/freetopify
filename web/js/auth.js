import { apiPost, clearToken, setToken } from '/web/js/api.js?v=20260524-13';

export async function login(username, password) {
  const result = await apiPost('/auth/login', { username, password });
  setToken(result.access_token);
  return result;
}

export async function guestJoin(name, pin) {
  const result = await apiPost('/auth/guest', { name, pin });
  setToken(result.access_token);
  return result;
}

export function logout() {
  apiPost('/auth/logout', {}).catch(() => {}).finally(() => {
    clearToken();
    window.location.href = '/web/login.html';
  });
}

function bindLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button');
    const activeMode = document.querySelector('.role-option.is-active')?.dataset.mode || 'admin';

    button.disabled = true;
    button.textContent = activeMode === 'admin' ? 'Signing in...' : 'Joining...';

    try {
      if (activeMode === 'guest') {
        const name = document.getElementById('guest-name').value.trim();
        const pin = document.getElementById('guest-pin').value;
        await guestJoin(name, pin);
      } else {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        await login(username, password);
      }
      window.location.href = '/web/index.html#library';
    } catch (err) {
      alert(err.message || (activeMode === 'guest' ? 'Guest join failed' : 'Login failed'));
    } finally {
      button.disabled = false;
      button.textContent = activeMode === 'admin' ? 'Continue as Admin' : 'Continue as Guest';
    }
  });
}

bindLoginForm();
