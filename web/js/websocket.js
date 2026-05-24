import { getToken } from '/web/js/api.js?v=20260524-13';

let ws;

export function connectLiveUpdates(onEvent) {
  const token = getToken();
  if (!token) return;
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/live?token=${encodeURIComponent(token)}`;

  ws = new WebSocket(url);
  ws.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      onEvent(payload);
    } catch (_) {}
  };
  ws.onopen = () => {
    const ping = () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
        setTimeout(ping, 15000);
      }
    };
    ping();
  };
  ws.onclose = () => {
    setTimeout(() => {
      if (getToken()) {
        connectLiveUpdates(onEvent);
      }
    }, 2000);
  };
}
