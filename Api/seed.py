import mariadb
from faker import Faker
import random
from pathlib import Path

fake = Faker("es_MX")

try:
    conn = mariadb.connect(
    user="root",
    password="admin665",
    host="localhost",
    port=3307,
    database="Senores"
)

except mariadb.Error as e:
    print(f"¿ No se encontro una conexion con la Base de Datos: {e}")

upload_dir = Path('uploads/fotos')
upload_dir.mkdir(parents=True, exist_ok=True)

cursor = conn.cursor()

# Esto es para borrar todos los datos de los seeder como hacer un migrate refresh
#cursor.execute("DELETE FROM usuarios")
#conn.commit()


for i in range(10):
    nombre = fake.first_name()
    apellidos = fake.last_name()
    codigo = random.randint(1000, 9999)  
    curp = fake.unique.bothify(text='????######XXXXXX##')  
    calle = fake.street_address()
    
    # Solo el nombre del archivo, NO la ruta completa
    ruta_foto = f"user_{codigo}.jpg" 

    cursor.execute("""
        INSERT INTO usuarios (nombre, apellidos, codigo_estudiante, curp, calle, ruta_foto)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (nombre, apellidos, codigo, curp, calle, ruta_foto))

conn.commit()
conn.close()

print("Seeder completado: 10 usuarios insertados")
