import requests
import json
import os
import re
import time
import datetime

# --- Configuración ---
API_URL = "https://elperuano.pe/portal/_SearchNews"
BASE_URL = "https://elperuano.pe/"
PAGE_SIZE = 10
PAGE_LIMIT = 5
# --- ¡CAMBIO! Apuntar al archivo JSON principal ---
OUTPUT_FILE = "news_scrapers/noticias_partidos.json" 

# Solo se guardarán noticias desde esta fecha en adelante.
START_DATE_LIMIT = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)

# Keywords para buscar (puedes usar las mismas que La República o unas específicas)
KEYWORDS = [
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

# --- Funciones Auxiliares ---

def _parse_elperuano_date(date_str):
    """Convierte el formato /Date(timestamp)/ a datetime."""
    if not date_str: return None
    match = re.search(r"\((\d+)\)", date_str)
    if not match: return None
    try:
        timestamp_ms = int(match.group(1))
        return datetime.datetime.fromtimestamp(timestamp_ms / 1000, tz=datetime.timezone.utc)
    except (ValueError, TypeError):
        return None

def cargar_noticias_existentes(archivo):
    """Carga el JSON principal. Devuelve {} si no existe o está corrupto."""
    if not os.path.exists(archivo):
        return {}
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Advertencia: El archivo principal {archivo} está corrupto. Se iniciará/continuará desde cero.")
        return {}

def guardar_noticias(archivo, datos):
    """Guarda el diccionario de noticias actualizado en el archivo JSON principal."""
    try:
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        # --- ¡CAMBIO! Mensaje actualizado ---
        print(f"\n¡Éxito! Base de datos principal ({archivo}) actualizada con noticias de El Peruano.")
    except IOError as e:
        print(f"\nError al escribir en el archivo {archivo}: {e}")

# --- Función Principal ---

def main():
    """Función principal del scraper stateful de El Peruano, actualizando el JSON principal."""
    print("--- Iniciando scraper de El Peruano (Actualizando JSON principal) ---")

    noticias_guardadas = cargar_noticias_existentes(OUTPUT_FILE)
    print(f"Se cargaron {len(noticias_guardadas)} noticias existentes desde {OUTPUT_FILE}.")

    nuevas_noticias_elperuano = 0

    for query in KEYWORDS:
        print(f"\n--- [El Peruano] Buscando término: '{query}' (desde {START_DATE_LIMIT.date()}) ---")

        for page_num in range(1, PAGE_LIMIT + 1):

            # --- CORRECTION: Initialize HERE, before the try block ---
            nuevas_en_esta_pagina = 0
            # ---------------------------------------------------------

            params = {
                'pageIndex': page_num,
                'pageSize': PAGE_SIZE,
                'claves': query
            }

            print(f"Obteniendo [El Peruano]: Página {page_num} para '{query}'...")

            try:
                response = requests.get(API_URL, params=params, timeout=15)
                response.raise_for_status()
                articulos_api = response.json()

                if not isinstance(articulos_api, list) or not articulos_api:
                    print(f"No se encontraron más resultados [El Peruano] para '{query}'.")
                    break

                # Initialization moved outside/above the 'try' block
                # nuevas_en_esta_pagina = 0 # <-- REMOVED FROM HERE
                all_articles_on_page_are_old = True

                for articulo in articulos_api:
                    article_id_int = articulo.get('intNoticiaId')
                    article_date_obj = _parse_elperuano_date(articulo.get('dtmFecha'))

                    if not article_id_int or not article_date_obj:
                        continue

                    if article_date_obj >= START_DATE_LIMIT:
                        all_articles_on_page_are_old = False
                        article_id_str_prefixed = f"elperuano_{article_id_int}"

                        if article_id_str_prefixed not in noticias_guardadas:
                            url_slug = articulo.get("URLFriendLy", "").lstrip('/')
                            full_url = BASE_URL + url_slug
                            noticia_para_guardar = {
                                "_id": article_id_str_prefixed,
                                "title": articulo.get("vchTitulo"),
                                "type": "article",
                                "date": article_date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                                "update_date": article_date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                                "created_at": article_date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                                "slug": url_slug,
                                "data": {
                                    "__typename": "ArticleDataType",
                                    "teaser": articulo.get("vchBajada") or articulo.get("vchDescripcion"),
                                    "authors": [],
                                    "tags": [{'__typename': 'TagType', 'name': query, 'slug': f'/tag/{query.lower()}'}],
                                    "categories": [{'__typename': 'CategoryReferenceType', 'name': articulo.get('Seccion', 'Desconocida'), 'slug': f"/{articulo.get('Seccion', 'desconocida').lower()}"}],
                                    "multimedia": [{
                                        "__typename": 'MultimediaType',
                                        "type": "image",
                                        "path": articulo.get("vchRutaCompletaFotografia"),
                                        "data": {
                                            "__typename": "MultimediaDataType",
                                            "title": articulo.get("vchTitulo"),
                                            "alt": articulo.get("vchTitulo"),
                                        }
                                    }]
                                },
                                "metadata_seo": {"keywords": query},
                                "metadata": [{"key": "source", "value": "El Peruano"}],
                                "has_video": False
                            }
                            nuevas_en_esta_pagina += 1
                            noticias_guardadas[article_id_str_prefixed] = noticia_para_guardar
                    else:
                        pass

                # This line is now safe, nuevas_en_esta_pagina always exists
                nuevas_noticias_elperuano += nuevas_en_esta_pagina
                print(f"Resultados [El Peruano]: {nuevas_en_esta_pagina} noticias nuevas (de 2025) añadidas al JSON principal.")

                if all_articles_on_page_are_old and articulos_api:
                    print(f"-> Página completa de artículos antiguos [El Peruano]. Deteniendo búsqueda para '{query}'.")
                    break

                time.sleep(1)

            except requests.exceptions.RequestException as e:
                print(f"Error al conectar con la API de El Peruano para '{query}': {e}")
                # The loop continues to the next page_num, but nuevas_en_esta_pagina will be 0 (correct)
            except json.JSONDecodeError:
                print(f"Error: La respuesta de la API de El Peruano para '{query}' no fue JSON.")
                # The loop continues, nuevas_en_esta_pagina will be 0 (correct)
            # --- We no longer break here on error, just report and try next page ---

    print("\n--- Scraping de El Peruano completado ---")
    print(f"Total de noticias NUEVAS de El Peruano (de 2025) agregadas en esta ejecución: {nuevas_noticias_elperuano}")
    print(f"Total de noticias en la base de datos principal ahora: {len(noticias_guardadas)}")

    guardar_noticias(OUTPUT_FILE, noticias_guardadas)

if __name__ == "__main__":
    main()