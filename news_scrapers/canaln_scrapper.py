# news_scrapers/canaln_scrapper.py
# -*- coding: utf-8 -*-

import json
import time
import re
import os
import datetime
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
BASE = "https://canaln.pe"
DEFAULT_OUTPUT = "news_scrapers/noticias_partidos.json"
# Filtro de fecha: Solo noticias desde 2025
START_DATE_LIMIT = datetime.datetime(2025, 1, 1)

KEYWORDS = [
    'Acción Popular', 'Alianza para el Progreso', 'APP', 'Avanza País',
    'Fuerza Popular', 'Juntos por el Perú', 'Partido Morado', 'Perú Libre',
    'Podemos Perú', 'Renovación Popular', 'Somos Perú', 'Partido Aprista',
    'Keiko Fujimori', 'Rafael López Aliaga', 'César Acuña', 'Dina Boluarte', 'Pedro Castillo',
    'Agustin Lozano'
]

def parse_canaln_date(date_text):
    """
    Intenta convertir fechas de Canal N: "10/02/2025", "Hace 2 horas", "Ayer".
    Devuelve un objeto datetime o None si falla.
    """
    try:
        now = datetime.datetime.now()
        txt = date_text.strip().lower()
        
        if "hace" in txt or "minuto" in txt or "segundo" in txt or "hora" in txt:
            return now # Es de hoy
        if "ayer" in txt:
            return now - datetime.timedelta(days=1)
        
        # Intentar formato DD/MM/YYYY
        return datetime.datetime.strptime(txt, "%d/%m/%Y")
    except:
        return None

def load_existing_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return {}
    return {}

def save_updated_data(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless") # Ejecutar sin ventana
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def main(json_path=DEFAULT_OUTPUT): # <--- Acepta ruta del manager
    print(f"📺 [Canal N] Iniciando scraper. Destino: {json_path}")
    print(f"📅 Filtro: Noticias posteriores a {START_DATE_LIMIT.strftime('%d/%m/%Y')}")

    existing_data = load_existing_data(json_path)
    nuevas_totales = 0
    
    driver = setup_driver()
    driver.set_page_load_timeout(30)

    try:
        for term in KEYWORDS:
            print(f"🔍 Buscando: '{term}'...")
            # URL de búsqueda de Canal N
            search_url = f"{BASE}/buscar/{term}"
            driver.get(search_url)
            
            try:
                # Esperar a que carguen las cards
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "card"))
                )
            except:
                # Si no hay resultados o tarda mucho, pasamos al siguiente
                continue

            # Recorrer las noticias encontradas (Solo la primera página para ser rápidos)
            cards = driver.find_elements(By.CLASS_NAME, "card")
            
            for card in cards:
                try:
                    # Título y Link
                    h2 = card.find_element(By.TAG_NAME, "h2")
                    link_elem = h2.find_element(By.TAG_NAME, "a")
                    title = link_elem.text.strip()
                    url_part = link_elem.get_attribute("href")
                    
                    # Fecha (Suele estar en un span o small)
                    # Canal N estructura variable, intentamos buscar texto de fecha
                    date_obj = None
                    try:
                        # Intento genérico de buscar fecha en la card
                        txt_content = card.text
                        # Buscamos patrón DD/MM/YYYY
                        match = re.search(r'\d{2}/\d{2}/\d{4}', txt_content)
                        if match:
                            date_obj = datetime.datetime.strptime(match.group(), "%d/%m/%Y")
                        elif "hace" in txt_content.lower():
                            date_obj = datetime.datetime.now()
                    except: pass
                    
                    # --- FILTRO DE FECHA ---
                    if date_obj:
                        if date_obj < START_DATE_LIMIT:
                            # Encontró noticia vieja, asumimos orden cronológico y paramos este término
                            # (O usamos continue si no confiamos en el orden)
                            continue 
                    
                    # ID Único
                    unique_id = f"canaln_{hash(url_part)}"
                    
                    if unique_id not in existing_data:
                        existing_data[unique_id] = {
                            "_id": unique_id,
                            "title": title,
                            "slug": url_part, # Selenium devuelve URL completa usualmente
                            "date": date_obj.strftime("%Y-%m-%d") if date_obj else "2025-01-01",
                            "data": {"teaser": title}, # Usamos título como teaser simple
                            "metadata": [
                                {"key": "source", "value": "Canal N"},
                                {"key": "query", "value": term}
                            ]
                        }
                        nuevas_totales += 1
                        
                except Exception as e:
                    continue

    except Exception as e:
        print(f"Error global Canal N: {e}")
    finally:
        driver.quit()

    print(f"✅ [Canal N] Finalizado. {nuevas_totales} noticias nuevas.")
    save_updated_data(json_path, existing_data)

if __name__ == "__main__":
    main()