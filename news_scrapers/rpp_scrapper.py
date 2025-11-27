# news_scrapers/rpp_scrapper.py
# -*- coding: utf-8 -*-

import os
import json
import time
import datetime
import sys  # <--- Para forzar el cierre
from urllib.parse import quote
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN ---
BASE_SITE = "https://rpp.pe"
DEFAULT_OUTPUT = "news_scrapers/noticias_partidos.json"
START_DATE_LIMIT = datetime.datetime(2025, 1, 1)

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
    'elecciones Perú', 'Jurado Nacional de Elecciones', 'Datum', 'IPSOS', 'ONPE'
]

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

def save_data(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main(json_path=DEFAULT_OUTPUT):
    print(f"\n📻 [RPP - DEEP SCROLL] Iniciando. Filtro > {START_DATE_LIMIT.strftime('%d/%m/%Y')}")

    data_store = load_data(json_path)
    nuevas_count = 0

    # Configuración Selenium
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Timeout más corto para no colgarse en cargas infinitas
    driver.set_page_load_timeout(25)

    barra = tqdm(KEYWORDS, unit="term")

    try:
        for term in barra:
            barra.set_description(f"🔎 {term[:15]:<15}")
            
            url = f"https://rpp.pe/buscar?q={quote(term)}"
            
            try:
                driver.get(url)

                # Esperar carga inicial
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "news"))
                    )
                except:
                    continue 

                # --- SCROLL AUTOMÁTICO (La clave para más noticias) ---
                # Bajamos 4 veces. Cada bajada carga ~10 noticias más.
                for _ in range(4):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1.2) # Esperar a que RPP cargue el contenido dinámico

                # Ahora leemos todo lo que apareció
                articles = driver.find_elements(By.CLASS_NAME, "news")
                
                # DEBUG: Saber cuántas ve antes de filtrar
                # tqdm.write(f"   -> {len(articles)} items vistos para '{term}'") 

                for art in articles:
                    try:
                        # 1. Título y Link
                        title_elem = art.find_element(By.CSS_SELECTOR, "h2.news__title a")
                        title = title_elem.text.strip()
                        url_full = title_elem.get_attribute("href")

                        if not title or not url_full: continue

                        # 2. Fecha (data-x)
                        date_str = ""
                        date_obj = None
                        
                        try:
                            time_elem = art.find_element(By.CSS_SELECTOR, "time.news__date")
                            iso_date = time_elem.get_attribute("data-x") 
                            if iso_date:
                                date_obj = datetime.datetime.fromisoformat(iso_date).replace(tzinfo=None)
                        except:
                            pass

                        # --- FILTRO 2025 ---
                        es_reciente = False
                        
                        if date_obj:
                            date_str = date_obj.strftime("%Y-%m-%d")
                            if date_obj >= START_DATE_LIMIT:
                                es_reciente = True
                        else:
                            # Si falla la fecha, miramos la URL
                            if "/2025/" in url_full:
                                es_reciente = True
                                date_str = "2025-01-01 (URL)"

                        if not es_reciente:
                            continue

                        # 3. Guardar
                        unique_id = f"rpp_{hash(url_full)}"
                        
                        if unique_id not in data_store:
                            data_store[unique_id] = {
                                "_id": unique_id,
                                "title": title,
                                "slug": url_full,
                                "date": date_str,
                                "data": {"teaser": title},
                                "metadata": [
                                    {"key": "source", "value": "RPP Noticias"},
                                    {"key": "query", "value": term}
                                ]
                            }
                            nuevas_count += 1

                    except Exception:
                        continue
                
                barra.set_postfix(nuevas=nuevas_count)
                
            except Exception:
                continue

    except Exception as e:
        print(f"Error Driver RPP: {e}")
    finally:
        # --- CIERRE SEGURO ---
        try:
            driver.quit()
        except:
            pass

    print(f"\n✅ [RPP] Finalizado. {nuevas_count} noticias nuevas.")
    save_data(json_path, data_store)
    
    # Forzamos la salida para que no se quede colgado en la terminal
    sys.exit(0)

if __name__ == "__main__":
    main()