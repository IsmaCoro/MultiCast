import mariadb
import sys

try:
    conn = mariadb.connect(
        user="root",
        password="admin665",
        host="localhost",
        port=3307,  
        database="Senores"
    )

    print("Conexión exitosa con la base de Datos!")

except mariadb.Error as e:
    print(f"¿ No se encontro una conexion con la Base de Datos: {e}")
    sys.exit(1)

cursor = conn.cursor()

print("\nTablas de Senores:")
cursor.execute("SHOW TABLES")
for table in cursor.fetchall():
    print("-", table[0])

print("\nDatos dentro de la tabla:")
cursor.execute("SELECT * FROM usuarios")

usuarios = cursor.fetchall()

for row in usuarios:
    print(row)

conn.close()