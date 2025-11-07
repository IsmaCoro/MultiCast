# MultiCast — Guía Rápida con Cloudflare Tunnel

## Dependencias
pip install websockets requests
pip install mariadb

## Instalar Cloudflare Tunnel
winget install Cloudflare.cloudflared
(O descarga manual desde: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/)

---

## Ejecutar servidor
Abre una terminal en C:\MultiCast y ejecuta:
python -u .\MultiCast.py
(No cierres esta terminal mientras se usa el servidor)

---

## Crear los túneles (en 2 terminales separadas)

### 1️⃣ Túnel HTTP (puerto 8000)

& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000 2>&1 | Select-String -Pattern 'https://.*trycloudflare\.com' -AllMatches

"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000

### 2️⃣ Túnel WebSocket (puerto 8080)

& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8080 2>&1 | Select-String -Pattern 'https://.*trycloudflare\.com' -AllMatches


---

https://rpg-finally-holds-hopkins.trycloudflare.com/index.html?ws_host=exceptional-searched-winning-slope.trycloudflare.com&ws_port=443

https://(rpg-finally-holds-hopkins).trycloudflare.com

https://(exceptional-searched-winning-slope).trycloudflare.com

## 🧩 Armar el enlace final (fórmula)
⚠️ El orden importa:  
- La URL del **puerto 8000 (HTTP)** va al inicio.  
- La URL del **puerto 8080 (WebSocket)** va en `ws_host`.

Formato:
https://<URL_HTTP>.trycloudflare.com/index.html?ws_host=<URL_WS>.trycloudflare.com&ws_port=443


Ejemplo:
https://star-nine-librarian-roulette.trycloudflare.com/index.html?ws_host=avi-scope-music-gibson.trycloudflare.com&ws_port=443

---

## Verificación final
- Mantén las 3 terminales abiertas:
  1. Servidor → python MultiCast.py
  2. Túnel 8000 → Cloudflare Tunnel HTTP
  3. Túnel 8080 → Cloudflare Tunnel WebSocket

- Abre el enlace final en tu navegador o compártelo.

---

## Notas
- Si Cloudflare muestra “Cannot determine default origin certificate path”, ignóralo (es normal sin cuenta).  
- Si el enlace no carga aún, espera unos segundos y recarga.  
- Los enlaces generados expiran tras un tiempo, puedes volver a ejecutar los comandos para crear nuevos.
