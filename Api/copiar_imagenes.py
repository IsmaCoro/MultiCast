import shutil
from pathlib import Path

def copiar_imagenes_inteligente():
    upload_dir = Path('uploads/fotos')
    upload_dir.mkdir(parents=True, exist_ok=True)

    print("🖼️ Iniciando copia de imágenes...")

    # Mapeo de imágenes para el SEEDER (las originales)
    archivos_a_copiar = {
        r"C:\Users\TheOne\Downloads\EH.jfif": "user_8889.jpg",
        r"C:\Users\TheOne\Downloads\Justic3.jfif": "user_6967.jpg", 
        r"C:\Users\TheOne\Downloads\ZzZ.jfif": "user_6254.jpg",
        r"C:\Users\TheOne\Downloads\WHo.jfif": "user_2077.jpg",
        r"C:\Users\TheOne\Downloads\Waste.jfif": "user_9584.jpg",
        r"C:\Users\TheOne\Downloads\unnamed.webp": "user_4599.webp",
        r"C:\Users\TheOne\Downloads\GtKgVPeakAAAAwv.jfif": "user_7663.jpg",
        r"C:\Users\TheOne\Downloads\Gtfdw5aaoAARWEU.jfif": "user_4421.jpg",
        r"C:\Users\TheOne\Downloads\GtEvjxTasAAf_5A.jfif": "user_6452.jpg",
        r"C:\Users\TheOne\Downloads\GoUrc4vXYAA2Dw8.jfif": "user_9599.jpg"
    }

    # Verificar qué imágenes ya existen para NO duplicar
    imagenes_existentes = [arch.name for arch in upload_dir.glob('*')]
    print(f"Imágenes existentes: {len(imagenes_existentes)}")
    
    # Copiar SOLO las imágenes que NO existen
    copiadas = 0
    for origen, destino in archivos_a_copiar.items():
        if destino in imagenes_existentes:
            print(f"⏭ Saltada: {destino} (ya existe)")
            continue  # Saltar esta imagen
            
        destino_path = upload_dir / destino
        try:
            shutil.copy(origen, destino_path)
            print(f" {Path(origen).name} → {destino}")
            copiadas += 1
        except FileNotFoundError:
            print(f" No encontrado: {origen}")
        except Exception as e:
            print(f"Error: {e}")

    print(f" Proceso completado! {copiadas} nuevas imágenes copiadas")

if __name__ == "__main__":
    copiar_imagenes_inteligente()