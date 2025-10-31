import requests
import json
import os
import urllib.parse
import time
import datetime

# --- Configuración ---
BASE_API_URL = "https://larepublica.pe/api/search/articles"
PAGE_LIMIT = 10 
OUTPUT_FILE = "news_scrapers/noticias_partidos.json"

# Solo se guardarán noticias desde esta fecha en adelante.
START_DATE_LIMIT = datetime.datetime(2025, 1, 1)

PARTIDOS_KEYWORDS = [
    # Partidos (y siglas comunes)
    'Acción Popular',
    'Ahora Nación',
    'Alianza para el Progreso', 'APP',
    'Avanza País',
    'Batalla Perú',
    'Fe en el Perú',
    'Frente Popular Agrícola', 'FREPAP',
    'Fuerza Popular',
    'Juntos por el Perú',
    'Libertad Popular',
    'Nuevo Perú',
    'Partido Aprista Peruano', 'APRA',
    'Ciudadanos por el Perú',
    'Partido Cívico Obras',
    'Partido de los Trabajadores y Emprendedores', 'PTE-Perú',
    'Partido del Buen Gobierno',
    'Partido Demócrata Unido Perú',
    'Partido Demócrata Verde',
    'Partido Democrático Federal',
    'Somos Perú',
    'Partido Frente de la Esperanza 2021',
    'Partido Morado',
    'Partido País para Todos',
    'Partido Patriótico del Perú',
    'Partido Político Cooperación Popular',
    'Partido Político Fuerza Moderna',
    'Partido Político Integridad Democrática',
    'Partido Político Nacional Perú Libre', 'Perú Libre',
    'Partido Político Perú Acción',
    'Partido Político Perú Primero',
    'Partido Político Peruanos Unidos: ¡Somos Libres!', 'Somos Libres',
    'Partido Político Popular Voces del Pueblo',
    'Partido Político PRIN',
    'Partido Popular Cristiano', 'PPC',
    'Partido SiCreo',
    'Partido Unidad y Paz',
    'Perú Moderno',
    'Podemos Perú',
    'Primero la Gente',
    'Progresemos',
    'Renovación Popular',
    'Salvemos al Perú',
    'Un Camino Diferente',

    # Involucrados clave
    'Keiko Fujimori',
    'Vladimir Cerrón',
    'Rafael López Aliaga',
    'César Acuña',
    'Dina Boluarte',
    'Pedro Castillo',
    
    # Términos generales
    'elecciones perú',
    'ONPE',
    'JNE',
    'encuestas'
]

# --- Funciones del Script ---

def cargar_noticias_existentes(archivo):
    if not os.path.exists(archivo):
        return {}
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Advertencia: {archivo} está corrupto. Se creará uno nuevo.")
        return {}

def guardar_noticias(archivo, datos):
    try:
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        print(f"\n¡Éxito! Noticias guardadas y actualizadas en {archivo}")
    except IOError as e:
        print(f"\nError al escribir en el archivo {archivo}: {e}")

def main():
    print("--- Iniciando scraper de La República (Modo Paciente + Filtro de Fecha Corregido) ---")
    
    noticias_guardadas = cargar_noticias_existentes(OUTPUT_FILE)
    print(f"Se cargaron {len(noticias_guardadas)} noticias existentes desde {OUTPUT_FILE}.")
    
    nuevas_noticias_contador_total = 0
    
    for query in PARTIDOS_KEYWORDS:
        print(f"\n--- Buscando término: '{query}' (desde {START_DATE_LIMIT.date()}) ---")
        
        for page_num in range(1, PAGE_LIMIT + 1):
            
            encoded_query = urllib.parse.quote(query)
            full_url = f"{BASE_API_URL}?search={encoded_query}&limit=30&page={page_num}&order_by=update_date"
            
            print(f"Obteniendo: Página {page_num} para '{query}'...")

            try:
                response = requests.get(full_url)
                response.raise_for_status()
                data = response.json()
                articulos_api = data.get('articles', {}).get('data', [])
                
                if not articulos_api:
                    print(f"No se encontraron más resultados para '{query}'.")
                    break
                
                nuevas_en_esta_pagina = 0
                for articulo in articulos_api:
                    article_id = articulo.get('_id')
                    article_date_str = articulo.get('update_date') # ej: '2025-10-26 21:05:26'
                    
                    if not article_id or not article_date_str:
                        continue 

                    # --- 1. VERIFICACIÓN DE FECHA ---
                    try:
                        # --- ¡AQUÍ ESTÁ LA CORRECCIÓN! ---
                        # Se cambió '%Y-%m-%d %H%M%S' por '%Y-%m-%d %H:%M:%S'
                        article_date = datetime.datetime.strptime(article_date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        print(f"Advertencia: Ignorando artículo {article_id} con fecha no válida {article_date_str}")
                        continue
                    
                    if article_date >= START_DATE_LIMIT:
                        if article_id not in noticias_guardadas:
                            nuevas_en_esta_pagina += 1
                            noticias_guardadas[article_id] = articulo
                    else:
                        pass 
                
                nuevas_noticias_contador_total += nuevas_en_esta_pagina
                print(f"Resultados: {nuevas_en_esta_pagina} noticias nuevas (de 2025) añadidas.")

                time.sleep(0.5) 
                
            except requests.exceptions.RequestException as e:
                print(f"Error al conectar con la API para '{query}': {e}")
                break
            except json.JSONDecodeError:
                print(f"Error: La respuesta de la API para '{query}' no fue un JSON válido.")
                break

    print("\n--- Scraping completado ---")
    print(f"Total de noticias nuevas (de 2025) agregadas en esta ejecución: {nuevas_noticias_contador_total}")
    print(f"Total de noticias en la base de datos ahora: {len(noticias_guardadas)}")
    
    guardar_noticias(OUTPUT_FILE, noticias_guardadas)

if __name__ == "__main__":
    main()