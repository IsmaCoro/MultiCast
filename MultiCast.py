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
import json
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# ----------------- Utilidades -----------------
def get_local_ip() -> str:
    """
    Detecta la IP local saliente (LAN) creando un socket UDP "falso".
    Funciona en Windows sin enviar tráfico real.
    """
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
    """Comprueba si un puerto está disponible"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind((host, port))
        s.close()
        return True
    except:
        return False

def test_connection(host, port):
    """Intenta conectarse a un host:puerto para verificar si está disponible"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

def get_api_time_sync():
    """
    Obtiene la hora UTC desde la API de forma síncrona.
    Se debe ejecutar en un hilo para no bloquear asyncio.
    """
    API_URL = "http://worldtimeapi.org/api/timezone/Etc/UTC"
    try:
        response = requests.get(API_URL, timeout=5) # 5s timeout
        response.raise_for_status()
        data = response.json()
        
        # Formateamos un poco la respuesta
        utc_time_str = data['utc_datetime']
        return f"Respuesta de la API (UTC): {utc_time_str}"
        
    except Exception as e:
        print(f"[ERROR API] Fallo al contactar WorldTimeAPI: {e}")
        return "Error: No se pudo obtener la hora de la API."
    
LOCAL_IP = get_local_ip()
print(f"[INFO] IP local detectada: {LOCAL_IP}")

# Verificar puertos disponibles
print("\n--- Diagnóstico de puertos ---")
http_port_available = test_port("0.0.0.0", 8000)
ws_port_available = test_port("0.0.0.0", 8080)
print(f"Puerto HTTP 8000 disponible: {'SÍ' if http_port_available else 'NO - OCUPADO'}")
print(f"Puerto WebSocket 8080 disponible: {'SÍ' if ws_port_available else 'NO - OCUPADO'}")
if not http_port_available or not ws_port_available:
    print("ADVERTENCIA: Algunos puertos necesarios están ocupados. El servidor podría fallar.")

# ----------------- Configuración -----------------
# Multicast
MCAST_GRP  = "224.1.1.1"
MCAST_PORT = 5007

# Intenta usar la IP detectada para la interfaz de multicast
IFACE_IP = LOCAL_IP

# WebSocket: bindea a todas las interfaces
WS_HOST = "0.0.0.0"
WS_PORT = 8080

# HTTP estático: bindea a todas las interfaces
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8000

# Usar localhost para acceso local
USE_LOCALHOST = True

# Almacenamiento de clientes WebSocket
CONNECTED_CLIENTS = set()

# --- WebSocket -----------------
async def broadcast_to_websockets(message):
    if CONNECTED_CLIENTS:
        await asyncio.gather(
            *[client.send(message) for client in CONNECTED_CLIENTS],
            return_exceptions=True
        )

async def websocket_handler(websocket):
    CONNECTED_CLIENTS.add(websocket)
    print(f"Nuevo cliente web conectado. Total: {len(CONNECTED_CLIENTS)}")
    try:
        async for message in websocket:
            
            # --- Lógica de Comandos ---
            try:
                # Intentamos parsear "Sender: Message"
                sender, text = message.split(': ', 1)
            except ValueError:
                # Si no tiene el formato, lo ignoramos
                print(f"[WARN] Mensaje malformado: {message}")
                continue

            # 1. Comprobar si es el comando /time
            if text.strip() == "/time":
                print(f"[CMD] {sender} solicitó la hora (/time).")
                
                # Ejecutamos la llamada 'requests' (que es bloqueante) 
                # en un hilo separado para no detener el servidor.
                api_response = await asyncio.to_thread(get_api_time_sync)
                
                # Creamos un mensaje de "Sistema" con la respuesta
                system_message = f"Sistema: {api_response}"
                
                # Enviamos la respuesta a TODOS los clientes web
                await broadcast_to_websockets(system_message)

            # 2. Si no es un comando, es un mensaje de chat normal
            else:
                print(f"[Web -> Multicast]: {message}")

                # Enviar a multicast (lógica original)
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                try:
                    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(IFACE_IP))
                except OSError:
                    pass
                
                ttl = struct.pack('b', 1)
                send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

                try:
                    send_sock.sendto(message.encode("utf-8"), (MCAST_GRP, MCAST_PORT))
                except socket.error as e:
                    print(f"Error al enviar a multicast: {e}")
                finally:
                    send_sock.close()
            # --- Fin Lógica de Comandos ---

    except websockets.exceptions.ConnectionClosed:
        print("Cliente web desconectado.")
    finally:
        CONNECTED_CLIENTS.discard(websocket)
        print(f"Cliente web desconectado. Restantes: {len(CONNECTED_CLIENTS)}")

# ----------------- Multicast Listener (hilo) -----------------
def multicast_listener():
    """
    Escucha mensajes de Multicast y los reenvía a todos los WebSockets.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # En Windows, bind('', puerto) está bien
    recv_sock.bind(("", MCAST_PORT))

    group = socket.inet_aton(MCAST_GRP)

    # Intentar unirse a la interfaz específica
    joined = False
    try:
        iface = socket.inet_aton(IFACE_IP)
        mreq = struct.pack("4s4s", group, iface)
        recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        joined = True
        print(f"[INFO] Unido a multicast {MCAST_GRP} en interfaz {IFACE_IP}")
    except OSError as e:
        print(f"[WARN] No se pudo unir a multicast en {IFACE_IP}: {e}")

    # Si falló, usar INADDR_ANY (que el SO elija interfaz)
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
            print(f"[Multicast -> Web]: {message}")

            asyncio.run_coroutine_threadsafe(
                broadcast_to_websockets(message),
                main_loop  # definido en __main__
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
    t = threading.Thread(
        target=start_static_http_server,
        args=(project_dir, HTTP_HOST, HTTP_PORT),
        daemon=True
    )
    t.start()
    return t

def start_multicast_thread():
    t = threading.Thread(target=multicast_listener, daemon=True)
    t.start()
    return t
# ----------------- Arranque (versión robusta con asyncio.run) -----------------
async def main_async():
    project_dir = os.path.dirname(os.path.abspath(__file__))

    # 1) HTTP estático en hilo
    http_thread = start_http_thread(project_dir)

    # 2) Loop principal = loop actual (lo usará el listener multicast)
    global main_loop
    main_loop = asyncio.get_running_loop()

    # 3) WebSocket server
    print(f"Iniciando servidor WebSocket en ws://{LOCAL_IP}:{WS_PORT} (bind {WS_HOST})")

    # 4) Listener multicast en hilo
    listener_thread = start_multicast_thread()

    # 5) Abrir navegador (localhost recomendado)
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

    # 6) Mantener vivo indefinidamente mientras el WS está servido
    async with websockets.serve(websocket_handler, WS_HOST, WS_PORT):
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nCerrando servidor...")
        sys.exit(0)
