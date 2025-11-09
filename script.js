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

        // --- Esta es la condicional IF que solicitaste ---
        if (enteredPassword === correctPassword) {
            // CORRECTO: Ocultar el login y mostrar el botón de admin
            loginSection.style.display = 'none';
            adminContainer.style.display = 'block';
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