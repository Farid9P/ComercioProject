# news_scrapers/elperuano_scraper.py
# -*- coding: utf-8 -*-

import requests
import json
import os
import time
import datetime
import re
from tqdm import tqdm
import unicodedata

# --- CONFIGURACIÓN EXACTA DESCUBIERTA ---
# Endpoint descubierto: https://elperuano.pe/portal/_SearchNews
API_URL = "https://elperuano.pe/portal/_SearchNews"
DEFAULT_OUTPUT = "news_scrapers/noticias_partidos.json"
START_DATE_LIMIT = datetime.datetime(2025, 1, 1)

# Parámetros de la API
PAGE_SIZE = 50  # Pedimos 30 de golpe para ir rápido
MAX_PAGES = 10  # Buscar en las primeras 2 páginas (60 noticias por término)

# --- LISTA COMPLETA DE KEYWORDS ---
KEYWORDS = [
    'Acción Popular', 'Ahora Nación', 'Alianza para el Progreso', 'APP',
    'Avanza País', 'Batalla Perú', 'Fe en el Perú', 'Frente Popular Agrícola', 'FREPAP',
    'Fuerza Popular', 'Juntos por el Perú', 'Libertad Popular', 'Nuevo Perú',
    'Partido Aprista Peruano', 'APRA', 'Ciudadanos por el Perú', 'Partido Cívico Obras',
    'Partido de los Trabajadores y Emprendedores', 'PTE-Perú', 'Partido del Buen Gobierno',
    'Partido Demócrata Unido Perú', 'Partido Demócrata Verde', 'Partido Democrático Federal',
    'Somos Perú', 'Partido Frente de la Esperanza 2021', 'Partido Morado',
    'Partido Patriótico del Perú', 'Partido Político Perú Primero', 'Perú Libre',
    'Perú Moderno', 'Podemos Perú', 'Primero La Gente', 'Progresemos',
    'Renovación Popular', 'Salvemos al Perú', 'Sicuy', 'Voces del Pueblo', 
    'Agustin Lozano', 'Keiko Fujimori', 'Rafael López Aliaga', 'César Acuña', 
    'Dina Boluarte', 'Congreso de la República', 'Fiscalía de la Nación',
    'Juan José Santiváñez', 'Patricia Benavides', 'Junta Nacional de Justicia',
    'Antauro Humala', 'Guido Bellido', 'Vladimir Cerrón', 'Martín Vizcarra',
    'Hernando de Soto', 'Verónika Mendoza', 'Francisco Sagasti', 'Pedro Castillo',
    'Alberto Otárola', 'Aníbal Torres', 'Defensoría del Pueblo', 'JNJ', 'Carlos Alvarez', 
    'elecciones Perú', 'Jurado Nacional de Elecciones', 'Datum', 'IPSOS', 'ONPE', 'Jose Jerí', 'Presidencia de la República', 'encuestas perú'
]

def load_db(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_db(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def parse_microsoft_date(date_str):
    """
    Parsea la fecha del JSON: /Date(1763442000000)/
    """
    try:
        match = re.search(r'(\d+)', str(date_str))
        if match:
            timestamp_ms = int(match.group(1))
            return datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
    except Exception:
        pass
    return None

def clean_slug_text(text):
    """
    Genera un slug para la URL (ej: "Título de Noticia" -> "titulo-de-noticia")
    """
    if not text: return "noticia"
    # Normalizar tildes
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')
    # Quitar caracteres raros
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text).strip().lower()
    # Reemplazar espacios por guiones
    return re.sub(r'\s+', '-', text)

def main(json_path=DEFAULT_OUTPUT):
    print(f"\n📰 [El Peruano - API GET] Iniciando. Filtro > {START_DATE_LIMIT.strftime('%d/%m/%Y')}")
    
    db = load_db(json_path)
    nuevas_totales = 0
    
    # Headers normales de navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    barra = tqdm(KEYWORDS, unit="term")

    for query in barra:
        barra.set_description(f"🔎 {query[:15]:<15}")
        
        for page in range(1, MAX_PAGES + 1):
            # --- PARÁMETROS EXACTOS SEGÚN TU LINK ---
            # Link: https://elperuano.pe/portal/_SearchNews?pageIndex=1&pageSize=10&claves=onpe
            params = {
                "pageIndex": page,
                "pageSize": PAGE_SIZE,
                "claves": query
            }
            
            try:
                # Petición GET (No POST)
                response = requests.get(API_URL, params=params, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    break
                
                try:
                    lista_articulos = response.json()
                except:
                    break

                # La API devuelve la lista directamente, no anidada
                if not lista_articulos or not isinstance(lista_articulos, list):
                    break
                
                count_page = 0
                
                for item in lista_articulos:
                    try:
                        # 1. Extracción basada en tu archivo elperuano.json
                        art_id = str(item.get('intNoticiaId', ''))
                        titulo = item.get('vchTitulo', '').strip()
                        fecha_raw = item.get('dtmFecha', '')
                        
                        # 2. Fecha
                        date_obj = parse_microsoft_date(fecha_raw)
                        
                        es_reciente = False
                        date_str = ""
                        
                        if date_obj:
                            date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                            if date_obj >= START_DATE_LIMIT:
                                es_reciente = True
                        
                        if not es_reciente:
                            continue

                        # 3. Construir URL (Formato: elperuano.pe/noticia/ID-TITULO)
                        slug_txt = clean_slug_text(titulo)
                        url_full = f"https://elperuano.pe/noticia/{art_id}-{slug_txt}"
                        
                        # 4. Guardar
                        unique_id = f"ep_{art_id}"
                        
                        if unique_id not in db:
                            # 'vchBajada' suele ser el resumen corto, 'vchDescripcion' el largo
                            teaser = item.get('vchBajada', '') or item.get('vchDescripcion', '')
                            
                            db[unique_id] = {
                                "_id": unique_id,
                                "title": titulo,
                                "slug": url_full,
                                "date": date_str,
                                "data": {"teaser": teaser},
                                "metadata": [
                                    {"key": "source", "value": "El Peruano"},
                                    {"key": "query", "value": query}
                                ]
                            }
                            nuevas_totales += 1
                            count_page += 1
                            
                    except Exception:
                        continue
                
                # Si toda la página es antigua, paramos de buscar este término
                if count_page == 0:
                    break
                    
                time.sleep(0.2)

            except Exception:
                break
        
        barra.set_postfix(nuevas=nuevas_totales)

    print(f"\n✅ [El Peruano] Finalizado. {nuevas_totales} noticias nuevas agregadas.")
    save_db(json_path, db)

if __name__ == "__main__":
    main()