import mariadb
import sys

try:
    conn = mariadb.connect(
        user="dbpgf20750609",
        password="crm99QaeqVsrXo5Hm~8XH1yj",
        host="serverless-us-east4.sysp0000.db2.skysql.com",
        port=4050,
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