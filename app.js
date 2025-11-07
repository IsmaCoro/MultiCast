// ====== Config dinámica (HTTP → ws, HTTPS → wss) ======
const WS_PORT_DEFAULT = 8080;
const WS_SCHEME = location.protocol === 'https:' ? 'wss://' : 'ws://';
const params  = new URLSearchParams(location.search);
const WS_HOST = params.get('ws_host') || location.hostname;
const WS_PORT = parseInt(params.get('ws_port') || WS_PORT_DEFAULT, 10);
const WS_URL  = `${WS_SCHEME}${WS_HOST}:${WS_PORT}`;

// ====== DOM ======
const chatWindow   = document.getElementById('chat-window');
const messageForm  = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const sendButton   = document.getElementById('send-button');
const timeButton   = document.getElementById('time-button');
const statusDot    = document.getElementById('status-dot');
const statusText   = document.getElementById('status-text');
const meNameEl     = document.getElementById('me-name');
const meInitialsEl = document.getElementById('me-initials');
const themeToggle  = document.getElementById('theme-toggle');
const htmlRoot     = document.documentElement;

// Registro (modal)
const regBackdrop  = document.getElementById('reg-backdrop');
const regForm      = document.getElementById('reg-form');
const regNameInput = document.getElementById('reg-name');
const regError     = document.getElementById('reg-error');
// Extra: checkbox "Recordarme"
let rememberBox = document.getElementById('reg-remember');

// ====== Estado ======
let socket;
let reconnectDelay = 1000;
let nickname = null;
let registered = false;

// ====== Tema ======
const savedTheme = localStorage.getItem('chat_theme') || 'light';
htmlRoot.setAttribute('data-theme', savedTheme);
themeToggle.addEventListener('click', () => {
  const current = htmlRoot.getAttribute('data-theme');
  const next = current === 'light' ? 'dark' : 'light';
  htmlRoot.setAttribute('data-theme', next);
  localStorage.setItem('chat_theme', next);
});

// ====== Helpers ======
const fmtTime = (d = new Date()) =>
  d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

function setStatus(state, text) {
  statusDot.dataset.state = state;
  statusText.textContent = text;
}

function setComposerEnabled(enabled) {
  messageInput.disabled = !enabled;
  timeButton.disabled = !enabled;
  sendButton.disabled = !enabled || messageInput.value.trim().length === 0;
}

function displayMessage(fullMessage) {
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

function validateNickname(name) {
  if (!name) return false;
  const trimmed = name.trim();
  if (trimmed.length < 3 || trimmed.length > 32) return false;
  if (/^usuarioan[oó]nimo$/i.test(trimmed)) return false;
  return true;
}

// ====== Registro obligatorio ======
function showRegistration(msg = 'Regístrate para entrar') {
  regBackdrop.hidden = false;
  regBackdrop.style.display = 'grid';
  setComposerEnabled(false);
  setStatus('warn', msg);
  setTimeout(() => regNameInput?.focus(), 0);
}

// cierre agresivo para evitar overlays persistentes
function closeRegistration() {
  regBackdrop.hidden = true;
  regBackdrop.style.display = 'none';
  // opcional: elimina del DOM para que no interfiera con clics
  setTimeout(() => {
    if (regBackdrop && regBackdrop.parentNode) {
      // comentar si prefieres mantener en DOM
      // regBackdrop.parentNode.removeChild(regBackdrop);
    }
  }, 50);
}

// ESTE ES EL NUEVO BLOQUE COMPLETO (PÉGALO AQUÍ):
function completeRegistration(name) {
  nickname = name.trim();
  registered = true;
  
  // ¡CAMBIO IMPORTANTE!
  // Siempre guardamos el alias, sin importar la casilla.
  localStorage.setItem('chat_nickname', nickname);
  if (rememberBox) rememberBox.checked = true; // Sincroniza la casilla

  meNameEl.textContent = nickname;
  meInitialsEl.textContent = nickname.trim().charAt(0).toUpperCase() || 'U';
  closeRegistration();
  setComposerEnabled(false); // se habilita tras handshake OK
  connect();
}

// Intento reanudar sesión: AUTO-REGISTRA si el alias guardado es válido.
(function initRegistration() {
  // Asegurarnos que el checkbox exista primero
  if (!rememberBox) {
    const cb = document.createElement('label');
    cb.style.display = 'flex'; cb.style.alignItems = 'center'; cb.style.gap = '8px';
    cb.innerHTML = '<input type="checkbox" id="reg-remember"> Recordarme en este navegador';
    regForm?.insertBefore(cb, regForm.querySelector('button'));
    rememberBox = cb.querySelector('input');
  }

  const stored = localStorage.getItem('chat_nickname');

  // ¡AQUÍ ESTÁ LA MAGIA!
  // Si encontramos un alias guardado Y es válido...
  if (stored && validateNickname(stored)) {
    // Rellenamos los campos (aunque el modal no se verá)
    if (regNameInput) regNameInput.value = stored;
    rememberBox.checked = true;
    
    // ...¡simplemente completamos el registro y conectamos!
    console.log('Alias válido encontrado, reanudando sesión:', stored);
    completeRegistration(stored);
  } else {
    // Si no hay alias guardado (o era inválido)...
    if (stored) {
      // Limpiamos un posible alias inválido
      localStorage.removeItem('chat_nickname');
    }
    rememberBox.checked = false;
    
    // ...mostramos el modal de registro como antes.
    console.log('No se encontró alias válido, mostrando modal.');
    showRegistration();
  }
})();

regForm?.addEventListener('submit', (e) => {
  e.preventDefault();
  const candidate = regNameInput.value;
  if (!validateNickname(candidate)) {
    regError.hidden = false;
    regNameInput.setAttribute('aria-invalid', 'true');
    regNameInput.focus();
    return;
  }
  regError.hidden = true;
  regNameInput.removeAttribute('aria-invalid');
  completeRegistration(candidate);
});

// ====== UX ======
messageInput.addEventListener('input', () => {
  sendButton.disabled = messageInput.value.trim().length === 0 || messageInput.disabled;
});
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendButton.disabled) messageForm.requestSubmit();
  }
});

timeButton.addEventListener('click', () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    alert('No se puede solicitar la hora: WebSocket no conectado.');
    return;
  }
  socket.send('/time');
  messageInput.focus();
});

// ====== WebSocket con handshake REGISTER y token ======
function connect() {
  if (!registered || !nickname) return;

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
    setStatus('warn', 'Registrando…');
    socket.send(`REGISTER ${nickname}`);
    setTimeout(() => {
      if (socket && socket.readyState === WebSocket.OPEN && messageInput.disabled) {
        console.warn('[WS] Reintentando REGISTER…');
        socket.send(`REGISTER ${nickname}`);
      }
    }, 2500);
  };

  socket.onmessage = (event) => {
    const data = String(event.data);
    const lower = data.toLowerCase();

    // preferimos token
    if (data === 'SYSTEM:REGISTER_OK' || (lower.startsWith('sistema:') && lower.includes('registro ok'))) {
      setStatus('ok', `Conectado como ${nickname}`);
      setComposerEnabled(true);
      closeRegistration();
      return;
    }

    if (lower.startsWith('sistema:') && (lower.includes('alias inválido') || lower.includes('ya está en uso') || lower.includes('debes registrarte'))) {
      setComposerEnabled(false);
      showRegistration('Alias inválido o en uso. Elige otro.');
      displayMessage(data);
      return;
    }

    displayMessage(data);
  };

  socket.onclose = () => {
    setStatus('err', 'Desconectado');
    setComposerEnabled(false);
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

messageForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const txt = messageInput.value.trim();
  if (!txt || !socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(txt);
  messageInput.value = '';
  sendButton.disabled = true;
});