# agregar_usuario.py
import mariadb
import shutil
from pathlib import Path

def agregar_usuario_manual():
    try:
        conn = mariadb.connect(
            user="root",
            password="admin665",
            host="localhost",
            port=3307,
            database="Senores"
        )
        cursor = conn.cursor()
        
        # Estos son los datos del nuevo USUARIO Debes absolutamente - CAMBIAR ESTO ===
        nombre = "Jaime"
        apellidos = "Agurre"
        codigo_estudiante = 2358
        curp = "Utabs5181674XXXXXX94"
        calle = "Cinchas 24"
        ruta_foto = f"user_{codigo_estudiante}.jpg"
        
        # OJITOOOOO DEBES DE CAMBIAR ESTA RUTA POR LA DE TU IMAGEN REAL ===

        origen_imagen = r"C:\Users\TheOne\Downloads\Kive.jfif"
        
        # Verificar si el código ya existe
        cursor.execute("SELECT id FROM usuarios WHERE codigo_estudiante = ?", (codigo_estudiante,))
        if cursor.fetchone():
            print(f"Ya existe un usuario con código {codigo_estudiante}")
            conn.close()
            return
        
        # Insertar en la base de datos
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto))
        
        conn.commit()
        print(" Usuario agregado a la base de datos")
        
        # Copiar la imagen
        upload_dir = Path('uploads/fotos')
        destino_imagen = upload_dir / ruta_foto
        
        try:
            shutil.copy(origen_imagen, destino_imagen)
            print(f"Imagen copiada: {destino_imagen}")
        except FileNotFoundError:
            print(f"❌ No se encontró la imagen en: {origen_imagen}")
            print("ℹPuedes copiar la imagen manualmente a uploads/fotos/")
        
        conn.close()
        
    except mariadb.Error as e:
        print(f" Error de base de datos: {e}")

if __name__ == "__main__":
    agregar_usuario_manual()