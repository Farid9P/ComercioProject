# news_scrapers/larepublica_scraper.py
# -*- coding: utf-8 -*-

import requests
import json
import os
import time
import datetime
from urllib.parse import quote
from tqdm import tqdm  # <--- IMPORTANTE: Barra de progreso

# --- CONFIGURACIÓN ---
API_URL = "https://larepublica.pe/api/search/articles"
DEFAULT_OUTPUT = "news_scrapers/noticias_partidos.json"
START_DATE_LIMIT = datetime.datetime(2025, 1, 1)

PER_PAGE = 50
MAX_PAGES = 10 

# --- LISTA DE KEYWORDS ---
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
    'Alberto Otárola', 'Aníbal Torres', 'Defensoría del Pueblo', 'JNJ', 'Carlos Alvarez', 'elecciones Perú', 'Jurado Nacional de Elecciones',
    'Datum', 'IPSOS','Jose Jerí', 'Presidencia de la República', 'encuestas perú'
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

def main(json_path=DEFAULT_OUTPUT):
    print(f"\n📰 [La República - API] Iniciando actualización...")
    print(f"📅 Filtro: Noticias posteriores al {START_DATE_LIMIT.strftime('%d/%m/%Y')}")
    
    db = load_db(json_path)
    nuevas_totales = 0
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://larepublica.pe/'
    }

    # --- BARRA DE PROGRESO ---
    # tqdm envuelve la lista KEYWORDS y muestra el avance
    barra_progreso = tqdm(KEYWORDS, unit="term")

    for term in barra_progreso:
        # Actualizamos la descripción de la barra para saber qué busca
        barra_progreso.set_description(f"🔎 {term[:15]:<15}")
        
        count_term_total = 0

        for page in range(1, MAX_PAGES + 1):
            params = {
                "search": term,
                "limit": PER_PAGE,
                "page": page,
                "order_by": "update_date"
            }
            
            try:
                response = requests.get(API_URL, params=params, headers=headers, timeout=8)
                
                if response.status_code != 200:
                    break
                
                data_json = response.json()
                
                # Ruta correcta basada en tu archivo JSON: articles -> data
                articles_data = data_json.get('articles', {}).get('data', [])
                
                if not articles_data:
                    break 
                
                count_page = 0
                
                for item in articles_data:
                    try:
                        title = item.get('title', '').strip()
                        slug = item.get('slug', '')
                        date_str = item.get('date', '') 
                        
                        if slug.startswith('http'):
                            url_full = slug
                        else:
                            clean_slug = slug if slug.startswith('/') else '/' + slug
                            url_full = f"https://larepublica.pe{clean_slug}"
                        
                        # Validar fecha
                        es_reciente = False
                        if date_str:
                            try:
                                article_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                                if article_date >= START_DATE_LIMIT:
                                    es_reciente = True
                            except ValueError:
                                pass 
                        
                        if not es_reciente:
                            continue

                        unique_id = f"lr_{item.get('_id', hash(url_full))}"
                        
                        if unique_id not in db:
                            teaser = item.get('data', {}).get('teaser', '')
                            
                            db[unique_id] = {
                                "_id": unique_id,
                                "title": title,
                                "slug": url_full,
                                "date": date_str,
                                "data": {"teaser": teaser},
                                "metadata": [
                                    {"key": "source", "value": "La República"},
                                    {"key": "query", "value": term}
                                ]
                            }
                            nuevas_totales += 1
                            count_page += 1
                            count_term_total += 1
                            
                    except Exception:
                        continue
                
                # Si en esta página no encontramos nada nuevo, probablemente ya llegamos al pasado
                if count_page == 0:
                    break
                    
                time.sleep(0.1) 

            except Exception:
                break
        
        # Actualizar el contador en la barra lateral
        barra_progreso.set_postfix(nuevas=nuevas_totales)

    print(f"\n✅ [La República] Finalizado. {nuevas_totales} noticias nuevas agregadas.")
    save_db(json_path, db)

if __name__ == "__main__":
    main()