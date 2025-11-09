from flask import Flask, jsonify, send_from_directory, render_template, request, redirect, url_for
import mariadb
import os
# Se eliminaron shutil y Path, ya que no se guardarán archivos
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/fotos'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Configuración para el peso de la imagen (ya no aplica, pero se deja)

def get_connection():
    try:
        return mariadb.connect(
            user="dbpgf20750609",
            password="crm99QaeqVsrXo5Hm~8XH1yj",
            host="serverless-us-east4.sysp0000.db2.skysql.com",
            port=4050,
            database="Senores",
            ssl=True,
            ssl_verify_cert=False,
            ssl_ca="/path/to/skysql_chain_2023.pem"
        )
    except mariadb.Error as e:
        print(f"Error de conexión: {e}")
        return None

# Ruta para ver usuarios en HTML (Muestra la informacion de los usuarios junto con su imagen)
@app.route("/")
def index():
    conn = get_connection()
    if conn is None:
        return "Error de conexión a la base de datos"
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto FROM usuarios")
    
    columns = [desc[0] for desc in cursor.description]
    usuarios = []
    
    for row in cursor.fetchall():
        usuario_dict = dict(zip(columns, row))
        
        # --- MODIFICACIÓN PARA VISUALIZACIÓN ---
        # Determinar si la ruta_foto es una URL externa o un archivo local
        foto_path = usuario_dict.get('ruta_foto')
        if foto_path:
            if not (foto_path.startswith('http://') or foto_path.startswith('https://')):
                # Es un archivo local (antiguo), construir URL con url_for
                usuario_dict['ruta_foto'] = url_for('fotos', filename=foto_path)
        # Si es una URL completa (http/https), se deja como está
        # --- FIN DE MODIFICACIÓN ---
        
        usuarios.append(usuario_dict)
    
    conn.close()
    return render_template('usuarios.html', usuarios=usuarios)


# Ruta Para API mueestra los Usuraior en un fomulario JSON Pero para editarlos utiliza HTML
@app.route("/admin")
def admin():
    conn = get_connection()
    if conn is None:
        return "Error de conexión a la base de datos"
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto FROM usuarios")
    
    columns = [desc[0] for desc in cursor.description]
    usuarios = []
    
    for row in cursor.fetchall():
        usuario_dict = dict(zip(columns, row))
        
        # --- MODIFICACIÓN PARA VISUALIZACIÓN ---
        # Determinar si la ruta_foto es una URL externa o un archivo local
        foto_path = usuario_dict.get('ruta_foto')
        if foto_path:
            if not (foto_path.startswith('http://') or foto_path.startswith('https://')):
                # Es un archivo local (antiguo), construir URL con url_for
                usuario_dict['ruta_foto'] = url_for('fotos', filename=foto_path)
        # Si es una URL completa (http/https), se deja como está
        # --- FIN DE MODIFICACIÓN ---
        
        usuarios.append(usuario_dict)
    
    conn.close()
    return render_template('admin.html', usuarios=usuarios)


# Ruta para servir imágenes (Lo que hace es un link que expande la imagen a una pantalla completa)
# Esta ruta se mantiene para dar soporte a imágenes antiguas que ya estaban subidas
@app.route("/fotos/<filename>")
def fotos(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "Imagen no encontrada", 404
    

# Ruta Para la Api GET (Mostrar unicamente los datos de la pagina)
# ... (Código comentado se mantiene igual) ...


# Ruta pra la API POS (Agregación de Usuarios jijiji)
@app.route("/api/usuarios/web", methods=["POST"])
def api_agregar_usuario_web():
    try:
        # Esto simplemnete "serian" los campos para agregar los datos
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        codigo_estudiante = request.form.get('codigo_estudiante')
        curp = request.form.get('curp')
        calle = request.form.get('calle')
        
        # --- INICIO DE MODIFICACIÓN ---
        # Obtener la URL de la imagen desde el formulario
        foto_url = request.form.get('foto_url')

        # Validar campos requeridos
        if not all([nombre, apellidos, codigo_estudiante, curp, calle, foto_url]):
            return jsonify({"error": "Todos los campos, incluida la URL de la foto, son requeridos"}), 400
        
        # La ruta_foto AHORA es la URL directa
        ruta_foto = foto_url 
        
        # --- Se elimina toda la lógica de request.files, validación de archivos y generación de nombre ---
        
        # --- FIN DE MODIFICACIÓN ---

        conn = get_connection()
        if conn is None:
            return jsonify({"error": "Error de conexión a la base de datos"}), 500
        
        cursor = conn.cursor()

        # Verificar si el código ya existe
        cursor.execute("SELECT id FROM usuarios WHERE codigo_estudiante = ?", (codigo_estudiante,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": f"Ya existe un usuario con código {codigo_estudiante}"}), 400
        
        # Insertar en la base de datos (ruta_foto ahora contiene la URL)
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto))
        
        conn.commit()
        
        # --- INICIO DE MODIFICACIÓN ---
        # Se elimina toda la sección de "Guardar la imagen" (file.save)
        # --- FIN DE MODIFICACIÓN ---
        
        conn.close()
        
        # Redirigir a la página de admin para ver los cambios
        return redirect(url_for('admin'))
        
    except mariadb.Error as e:
        return jsonify({"error": f"Error de base de datos: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"Error interno: {e}"}), 500

# Se mantiene por si hay imágenes antiguas que necesiten esta carpeta
def ensure_upload_folder():
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

if __name__ == "__main__":
    ensure_upload_folder() # Se mantiene por compatibilidad con fotos antiguas
    print("Servidor iniciado en http://localhost:5000")
    print("Rutas disponibles:")
    print("  - http://localhost:5000/ (Vista web con imágenes)")
    """print("   - http://localhost:5000/api/usuarios GET (Obtener usuarios en JSON)")"""
    print("   - http://localhost:5000/admin (Interfaz de administración)")
    app.run(debug=True, host='0.0.0.0', port=5000)