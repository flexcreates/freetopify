let ws;

export function connectLiveUpdates(onEvent) {
  const url = `ws://${location.host}/ws/live`;

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
    // Basic reconnect with backoff avoiding infinite loop on auth fail
    setTimeout(() => {
      connectLiveUpdates(onEvent);
    }, 5000);
  };
}
