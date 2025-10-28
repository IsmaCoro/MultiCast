import asyncio
import websockets
import socket
import struct
import threading
import sys
import os
import webbrowser
import time
import requests
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# ----------------- Utilidades -----------------
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def test_port(host, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind((host, port))
        s.close()
        return True
    except:
        return False

def get_api_time_sync():
    TZ_MAIN = "America/Mexico_City"
    URLS = [
    "https://timeapi.io/api/Time/current/zone?timeZone=America/Mexico_City",
    "https://timeapi.io/api/Time/current/zone?timeZone=America/Bahia_Banderas",
    ]

    SP_MONTHS = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    SP_WEEKDAYS = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]

    def fmt_es(dt: datetime, tzname: str) -> str:
        wd = SP_WEEKDAYS[dt.weekday()]
        month = SP_MONTHS[dt.month - 1]
        return f"{wd} {dt.day:02d} de {month} de {dt.year} — {dt:%H:%M:%S} ({tzname})"

    for url in URLS:
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            data = r.json()
            
            dt_iso = data.get("dateTime") or data.get("date_time") or data.get("datetime")
            tzname = data.get("timeZone") or data.get("timezone") or TZ_MAIN

            if not dt_iso:
                continue

            dt_remote = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
            dt_remote_local = dt_remote.astimezone(ZoneInfo(tzname))

            # Obtener hora local del sistema
            dt_local = datetime.now().astimezone()

            # Calcular diferencia
            diff = dt_local - dt_remote_local
            diff_seconds = abs(diff.total_seconds())

            hours, remainder = divmod(diff_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            sign = "diferencia" if diff.total_seconds() > 0 else "diferencia"
            diff_text = (
                f"La hora local tiene una {sign} de "
                f"{int(hours)}h {int(minutes)}m {seconds:.3f}s respecto a {tzname}."
            )

            # --- MODIFICACIÓN ---
            # Se eliminaron las líneas que sobrescribían la variable 'diff_text'
            # para conservar los segundos y milisegundos.
            
            # Mostrar por consola
            tz_label = getattr(dt_local.tzinfo, "key", str(dt_local.tzinfo) or "Local")
            print(f"[INFO] Hora local: {fmt_es(dt_local, tz_label)}")
            print(f"[INFO] Hora remota: {fmt_es(dt_remote_local, tzname)}")
            print(f"[INFO] Diferencia: {diff_text}")

            # Enviar al chat
            return f"🕒 {fmt_es(dt_remote_local, tzname)}\n{diff_text}"
        except Exception as e:
            print(f"[ERROR API] {url} -> {e}")

    # Fallback sin red
    try:
        tz = ZoneInfo(TZ_MAIN)
        dt_local = datetime.now(tz)
        return f"Hora local (sin API): {fmt_es(dt_local, TZ_MAIN)}"
    except Exception as e:
        print(f"[ERROR Fallback] zoneinfo -> {e}")
        return "Error: No se pudo obtener la hora."



LOCAL_IP = get_local_ip()
print(f"[INFO] IP local detectada: {LOCAL_IP}")

print("\n--- Diagnóstico de puertos ---")
print(f"Puerto HTTP 8000 disponible: {'SÍ' if test_port('0.0.0.0', 8000) else 'NO - OCUPADO'}")
print(f"Puerto WebSocket 8080 disponible: {'SÍ' if test_port('0.0.0.0', 8080) else 'NO - OCUPADO'}")

# ----------------- Configuración -----------------
MCAST_GRP  = "224.1.1.1"
MCAST_PORT = 5007
IFACE_IP   = LOCAL_IP

WS_HOST = "0.0.0.0"
WS_PORT = 8080
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8000
USE_LOCALHOST = True

# ----------------- Registro / Sesiones -----------------
CONNECTED_CLIENTS = set()
CLIENT_NICKS = {}   # websocket -> nickname
ACTIVE_NICKS = set()

NICK_RE = re.compile(r"^[A-Za-zÀ-ÿ0-9 _.\-]{3,32}$")

def is_valid_nick(nick: str) -> bool:
    if not nick: return False
    n = nick.strip()
    if len(n) < 3 or len(n) > 32: return False
    if re.fullmatch(r"(?i)usuarioan[oó]nimo", n): return False
    if not NICK_RE.fullmatch(n): return False
    return True

# ----------------- Deduplicación por eco multicast -----------------
RECENT_SENT   = {}      # dict[str, float] => {"Nick: texto": timestamp}
RECENT_WINDOW = 5.0     # ventana de tiempo para considerar eco/duplicado

# ----------------- Helpers de envío -----------------
async def send_system(websocket, text: str):
    try:
        await websocket.send(f"Sistema: {text}")
    except Exception:
        pass

async def send_control(websocket, control: str):
    try:
        await websocket.send(control)
    except Exception:
        pass

async def broadcast_system(text: str):
    if CONNECTED_CLIENTS:
        await asyncio.gather(*[send_system(ws, text) for ws in list(CONNECTED_CLIENTS)], return_exceptions=True)

async def broadcast_chat_line(full_line: str):
    if CONNECTED_CLIENTS:
        await asyncio.gather(*[ws.send(full_line) for ws in list(CONNECTED_CLIENTS)], return_exceptions=True)

# ----------------- WebSocket handler -----------------
async def websocket_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"Nuevo cliente web conectado. Total: {len(CONNECTED_CLIENTS)}")
    registered = False
    nickname = None
    try:
        async for raw in websocket:
            msg = str(raw).strip()

            # 0) Handshake de registro obligatorio: "REGISTER <nick>"
            if not registered:
                if msg.upper().startswith("REGISTER "):
                    candidate = msg[9:].strip()
                    if not is_valid_nick(candidate):
                        await send_system(websocket, "Alias inválido. Debe tener 3–32 caracteres y no puede ser 'UsuarioAnónimo'.")
                        continue
                    if candidate in ACTIVE_NICKS:
                        await send_system(websocket, f"El alias '{candidate}' ya está en uso. Elige otro.")
                        continue
                    nickname = candidate
                    CLIENT_NICKS[websocket] = nickname
                    ACTIVE_NICKS.add(nickname)
                    registered = True
                    # Token de control + mensaje humano
                    await send_control(websocket, "SYSTEM:REGISTER_OK")
                    await send_system(websocket, f"Registro OK. ¡Bienvenido, {nickname}!")
                    await broadcast_system(f"{nickname} se ha unido al chat.")
                    print(f"[REGISTER] {nickname} registrado.")
                    continue
                else:
                    await send_system(websocket, "Debes registrarte primero. Envía: REGISTER <tu_alias>")
                    continue

            # 1) Comando /time
            if msg == "/time":
                api_response = await asyncio.to_thread(get_api_time_sync)
                await broadcast_system(api_response)
                continue

            # 2) Mensaje normal: el servidor formatea "<nick>: <texto>"
            if msg:
                full_line = f"{nickname}: {msg}"
                print(f"[Web -> Multicast]: {full_line}")

                # a) Broadcast a websockets
                await broadcast_chat_line(full_line)

                # b) Preparar socket multicast
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                try:
                    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(IFACE_IP))
                except OSError:
                    pass

                ttl = struct.pack('b', 1)
                send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

                # Evitar eco local de multicast (duplica mensajes en el mismo proceso)
                try:
                    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
                except OSError:
                    pass

                # --- DEDUP: MARCAR ANTES DE ENVIAR (evita carrera con el listener) ---
                now = time.time()
                RECENT_SENT[full_line] = now
                # limpieza del diccionario
                for m, ts in list(RECENT_SENT.items()):
                    if now - ts > RECENT_WINDOW:
                        RECENT_SENT.pop(m, None)

                # c) Enviar a multicast
                try:
                    send_sock.sendto(full_line.encode("utf-8"), (MCAST_GRP, MCAST_PORT))
                except socket.error as e:
                    print(f"Error al enviar a multicast: {e}")
                finally:
                    send_sock.close()

    except websockets.exceptions.ConnectionClosed:
        print("Cliente web desconectado.")
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        old = CLIENT_NICKS.pop(websocket, None)
        if old and old in ACTIVE_NICKS:
            ACTIVE_NICKS.discard(old)
            asyncio.get_event_loop().create_task(broadcast_system(f"{old} salió del chat."))
        print(f"Cliente web desconectado. Restantes: {len(CONNECTED_CLIENTS)}")

# ----------------- Multicast Listener (hilo) -----------------
def multicast_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    recv_sock.bind(("", MCAST_PORT))

    group = socket.inet_aton(MCAST_GRP)

    joined = False
    try:
        iface = socket.inet_aton(IFACE_IP)
        mreq = struct.pack("4s4s", group, iface)
        recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        joined = True
        print(f"[INFO] Unido a multicast {MCAST_GRP} en interfaz {IFACE_IP}")
    except OSError as e:
        print(f"[WARN] No se pudo unir a multicast en {IFACE_IP}: {e}")

    if not joined:
        try:
            mreq_any = struct.pack("4sL", group, socket.INADDR_ANY)
            recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq_any)
            print(f"[INFO] Unido a multicast {MCAST_GRP} usando INADDR_ANY")
        except OSError as e:
            print(f"[ERROR] Falló unión a multicast (INADDR_ANY): {e}")
            return

    print(f"Escuchando mensajes multicast en {MCAST_GRP}:{MCAST_PORT}...")

    while True:
        try:
            data, addr = recv_sock.recvfrom(65535)
            message = data.decode("utf-8", errors="replace")

            # Barrera 1: si parece venir de mi propia IP, ignorar
            if addr and addr[0] == IFACE_IP:
                continue

            # Barrera 2: si lo acabo de marcar, ignorar (eco/rebote)
            ts = RECENT_SENT.get(message)
            if ts is not None and (time.time() - ts) <= RECENT_WINDOW:
                continue

            # Reenviar al chat web
            asyncio.run_coroutine_threadsafe(
                broadcast_chat_line(message),
                main_loop
            )
        except socket.error as e:
            print(f"Error de socket multicast: {e}")
        except Exception as e:
            print(f"Error en listener multicast: {e}")

# ----------------- HTTP estático (hilo) -----------------
def start_static_http_server(directory: str, host: str = HTTP_HOST, port: int = HTTP_PORT):
    os.chdir(directory)
    TCPServer.allow_reuse_address = True
    handler = SimpleHTTPRequestHandler
    with TCPServer((host, port), handler) as httpd:
        print(f"Servidor HTTP estático en http://{LOCAL_IP}:{port}/ (sirviendo {directory})")
        httpd.serve_forever()

# ----------------- Arranque -----------------
def start_http_thread(project_dir: str):
    t = threading.Thread(target=start_static_http_server, args=(project_dir, HTTP_HOST, HTTP_PORT), daemon=True)
    t.start()
    return t

def start_multicast_thread():
    t = threading.Thread(target=multicast_listener, daemon=True)
    t.start()
    return t

# ----------------- Main -----------------
async def main_async():
    project_dir = os.path.dirname(os.path.abspath(__file__))

    start_http_thread(project_dir)
    global main_loop
    main_loop = asyncio.get_running_loop()

    start_multicast_thread()

    browser_ip = "localhost" if USE_LOCALHOST else LOCAL_IP
    url = f"http://{browser_ip}:{HTTP_PORT}/index.html"
    print(f"Abriendo navegador: {url}")
    try:
        webbrowser.open_new_tab(url)
        print(f"Si no se abre, entra manualmente a: {url}")
        print(f"También puedes: http://localhost:{HTTP_PORT}/index.html")
    except Exception as e:
        print(f"No se pudo abrir el navegador automáticamente: {e}")
        print(f"Abre esta URL manualmente: {url}")

    async with websockets.serve(websocket_handler, WS_HOST, WS_PORT):
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
        sys.exit(0)