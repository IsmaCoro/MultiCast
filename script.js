// Espera a que la página cargue
document.addEventListener('DOMContentLoaded', (event) => {
    
    // --- CONFIGURACIÓN ---
    // ¡CAMBIA ESTA CLAVE POR LA TUYA!
    const correctPassword = "admin123"; 
    // --- FIN CONFIGURACIÓN ---

    // Seleccionar los elementos de la página
    const unlockButton = document.getElementById('unlock-button');
    const passwordInput = document.getElementById('password-input');
    const loginSection = document.getElementById('login-section');
    const adminContainer = document.getElementById('admin-button-container');

    // Función para verificar la clave
     function checkPassword() {
    const enteredPassword = passwordInput.value;

    if (enteredPassword === correctPassword) {
        // CORRECTO: Ocultar el login y mostrar el botón de admin
        loginSection.style.display = 'none';
        adminContainer.style.display = 'block';

        // --- AÑADE ESTE BLOQUE DE CÓDIGO AQUÍ ---
        const params = new URLSearchParams(location.search);
        const adminHost = params.get('admin_host');
        const adminButton = document.getElementById('admin-redirect-button');

        if (adminButton) {
          if (adminHost) {
            // Si el parámetro admin_host existe, crea la URL pública
            adminButton.onclick = () => {
                const chatHost = location.hostname; // El host del chat (8000)
                const wsHost = params.get('ws_host');
                // Pasa todos los hosts al admin para que pueda volver
                window.location.href = `https://${adminHost}/admin?chat_host=${chatHost}&ws_host=${wsHost}&admin_host=${adminHost}`;
            };
          } else {
            // Si no, usa el enlace local (para que siga funcionando en tu PC)
            adminButton.onclick = () => {
              window.location.href = 'http://localhost:5000/admin';
            };
          }
        }
        // --- FIN DEL BLOQUE NUEVO ---

    } else {
        // INCORRECTO: Avisar al usuario
        alert("Clave incorrecta.");
        passwordInput.value = ""; // Limpiar el campo
    }
    }

    // Asignar la función al botón de desbloqueo
    unlockButton.addEventListener('click', checkPassword);
    
    // Opcional: Permitir presionar "Enter" en el campo de texto
    passwordInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            checkPassword();
        }
    });
});