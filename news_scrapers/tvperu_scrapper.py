# news_scrapers/tvperu_scrapper.py
# -*- coding: utf-8 -*-

import os
import json
import time
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# --- CONFIGURACIÓN ---
BASE_SITE = "https://www.tvperu.gob.pe"
DEFAULT_OUTPUT = "news_scrapers/noticias_partidos.json"
START_DATE_LIMIT = datetime.datetime(2025, 1, 1)

KEYWORDS = [
    'Acción Popular', 'Alianza para el Progreso', 'Fuerza Popular', 'Perú Libre',
    'Renovación Popular', 'Podemos Perú', 'Juntos por el Perú', 'Somos Perú',
    'Dina Boluarte', 'Congreso', 'Presidencia'
]

def load_db(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_db(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def parse_tvperu_date(date_text):
    # Formato usual: "10/02/2025" o "10 Febrero 2025"
    try:
        # Intentar formato simple DD/MM/YYYY
        return datetime.datetime.strptime(date_text.strip(), "%d/%m/%Y")
    except:
        return None

def main(json_path=DEFAULT_OUTPUT): # <--- Integración con Manager
    print(f"📺 [TV Perú] Iniciando scraper. Destino: {json_path}")
    print(f"📅 Filtro: Noticias posteriores a {START_DATE_LIMIT.strftime('%d/%m/%Y')}")

    db = load_db(json_path)
    nuevas = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for term in KEYWORDS:
        print(f"🔍 Buscando: '{term}'...")
        # URL de búsqueda (ajusta según la web actual de TV Perú)
        url = f"{BASE_SITE}/buscar?search_api_fulltext={quote(term)}"
        
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200: continue
            
            soup = BeautifulSoup(res.text, 'html.parser')
            # Selectores aproximados para TV Perú
            articles = soup.find_all("div", class_="views-row") # Ajustar clase si cambia
            
            for art in articles:
                try:
                    title_elem = art.find("span", class_="field-content").find("a")
                    if not title_elem: continue
                    
                    title = title_elem.text.strip()
                    rel_link = title_elem['href']
                    full_link = f"{BASE_SITE}{rel_link}"
                    
                    # Fecha
                    date_obj = None
                    date_elem = art.find("span", class_="views-field-created")
                    if date_elem:
                        date_obj = parse_tvperu_date(date_elem.text.strip())
                    
                    # --- FILTRO 2025 ---
                    if date_obj:
                        if date_obj < START_DATE_LIMIT:
                            continue # Muy antigua
                    
                    unique_id = f"tvperu_{hash(rel_link)}"
                    
                    if unique_id not in db:
                        db[unique_id] = {
                            "_id": unique_id,
                            "title": title,
                            "slug": full_link,
                            "date": date_obj.strftime("%Y-%m-%d") if date_obj else "2025-01-01",
                            "data": {"teaser": title},
                            "metadata": [
                                {"key": "source", "value": "TV Perú"}, # Nombre para el detector
                                {"key": "query", "value": term}
                            ]
                        }
                        nuevas += 1
                        
                except Exception:
                    continue
                    
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error TVPerú '{term}': {e}")

    print(f"✅ [TV Perú] Finalizado. {nuevas} noticias nuevas.")
    save_db(json_path, db)

if __name__ == "__main__":
    main()