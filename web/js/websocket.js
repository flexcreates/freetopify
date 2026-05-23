import { getToken } from '/web/js/api.js';

let ws;

export function connectLiveUpdates(onEvent) {
  if (!getToken()) return;
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/live`;

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
    setTimeout(() => connectLiveUpdates(onEvent), 2000);
  };
}
