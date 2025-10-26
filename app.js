// ====== Config dinámica (HTTP → ws, HTTPS → wss) ======
const WS_PORT_DEFAULT = 8080;
const WS_SCHEME = location.protocol === 'https:' ? 'wss://' : 'ws://';

// Permite overrides opcionales por querystring: ?ws_host=192.168.1.74&ws_port=8080
const params  = new URLSearchParams(location.search);
const WS_HOST = params.get('ws_host') || location.hostname;
const WS_PORT = parseInt(params.get('ws_port') || WS_PORT_DEFAULT, 10);
const WS_URL  = `${WS_SCHEME}${WS_HOST}:${WS_PORT}`;

// ====== DOM ======
const chatWindow   = document.getElementById('chat-window');
const messageForm  = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const sendButton   = document.getElementById('send-button');
const statusDot    = document.getElementById('status-dot');
const statusText   = document.getElementById('status-text');
const meNameEl     = document.getElementById('me-name');
const meInitialsEl = document.getElementById('me-initials');
const themeToggle  = document.getElementById('theme-toggle');
const htmlRoot     = document.documentElement;

// ====== Nickname ======
let nickname = localStorage.getItem('chat_nickname');
if (!nickname) {
  nickname = prompt('Por favor, ingresa tu nombre de usuario:') || 'UsuarioAnónimo';
  localStorage.setItem('chat_nickname', nickname);
}
meNameEl.textContent = nickname;
meInitialsEl.textContent = nickname.trim().charAt(0).toUpperCase() || 'U';

// ====== Tema (light/dark) ======
const savedTheme = localStorage.getItem('chat_theme') || 'light';
htmlRoot.setAttribute('data-theme', savedTheme);
themeToggle.addEventListener('click', () => {
  const current = htmlRoot.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  htmlRoot.setAttribute('data-theme', next);
  localStorage.setItem('chat_theme', next);
});

// ====== UX ======
messageInput.addEventListener('input', () => {
  sendButton.disabled = messageInput.value.trim().length === 0;
});
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendButton.disabled) messageForm.requestSubmit();
  }
});

// ====== Helpers ======
const fmtTime = (d = new Date()) =>
  d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

function setStatus(state, text) {
  statusDot.dataset.state = state; // 'ok' | 'warn' | 'err'
  statusText.textContent = text;
}

function displayMessage(fullMessage) {
  // Formato esperado: "Remitente: Mensaje"
  const [sender, ...msgParts] = String(fullMessage).split(': ');
  const messageText = msgParts.join(': ');

  const wrapper = document.createElement('div');
  wrapper.classList.add('message');

  if (sender === 'Sistema') {
    wrapper.classList.add('system');
  } else if (sender === nickname) {
    wrapper.classList.add('mine');
  } else {
    wrapper.classList.add('other');
  }

  const meta = document.createElement('div');
  meta.classList.add('meta');

  const nameEl = document.createElement('span');
  nameEl.classList.add('sender');
  nameEl.textContent = sender || '—';
  meta.appendChild(nameEl);

  const timeEl = document.createElement('span');
  timeEl.classList.add('time');
  timeEl.textContent = fmtTime();
  meta.appendChild(timeEl);

  const textEl = document.createElement('div');
  textEl.classList.add('text');
  textEl.textContent = messageText || '';

  wrapper.appendChild(meta);
  wrapper.appendChild(textEl);

  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ====== WebSocket con reconexión ======
let socket;
let reconnectDelay = 1000; // 1s, 2s, 4s, ... máx 10s

function connect() {
  setStatus('warn', 'Conectando…');
  try {
    console.log('[WS] Conectando a', WS_URL);
    socket = new WebSocket(WS_URL);
  } catch {
    setStatus('err', 'Error de conexión');
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    setStatus('ok', `Conectado a ${WS_HOST}:${WS_PORT}`);
    reconnectDelay = 1000;
    const joinMsg = `Sistema: ${nickname} se ha unido al chat.`;
    displayMessage(joinMsg); // local
    socket.send(joinMsg);    // broadcast
  };

  socket.onmessage = (event) => {
    displayMessage(event.data);
  };

  socket.onclose = () => {
    setStatus('err', 'Desconectado');
    scheduleReconnect();
  };

  socket.onerror = () => {
    setStatus('err', 'Error de WebSocket');
  };
}

function scheduleReconnect() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
  setTimeout(connect, reconnectDelay);
  reconnectDelay = Math.min(reconnectDelay * 2, 10000);
}

connect();

// ====== Envío ======
messageForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const txt = messageInput.value.trim();
  if (!txt || !socket || socket.readyState !== WebSocket.OPEN) return;

  const full = `${nickname}: ${txt}`;
  socket.send(full);
  messageInput.value = '';
  sendButton.disabled = true;
});
