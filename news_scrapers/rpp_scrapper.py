# -*- coding: utf-8 -*-
"""
Scraping de RPP por TÉRMINOS DE BÚSQUEDA (MODO DICCIONARIO CORREGIDO v3)
Carga noticias_partidos.json, busca términos en RPP, añade noticias nuevas, y guarda el diccionario.
Adaptado para la estructura de la página /buscar/
"""

import os
import json
import time
import random
from typing import List, Dict, Set
from urllib.parse import urljoin, quote
import datetime

import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    NoSuchElementException
)

# ========== CONFIGURACIÓN ==========
BASE_SITE = "https://rpp.pe"
BASE_SEARCH_URL = "https://rpp.pe/buscar/{slug}" # Apunta a la búsqueda

KEYWORDS = [
    # Partidos (y siglas comunes)
    'Acción Popular', 'Ahora Nación', 'Alianza para el Progreso', 'APP', 'Avanza País',
    'Batalla Perú', 'Fe en el Perú', 'Frente Popular Agrícola', 'FREPAP', 'Fuerza Popular',
    'Juntos por el Perú', 'Libertad Popular', 'Nuevo Perú', 'Partido Aprista Peruano', 'APRA',
    'Ciudadanos por el Perú', 'Partido Cívico Obras', 'Partido de los Trabajadores y Emprendedores', 'PTE-Perú',
    'Partido del Buen Gobierno', 'Partido Demócrata Unido Perú', 'Partido Demócrata Verde',
    'Partido Democrático Federal', 'Somos Perú', 'Partido Frente de la Esperanza 2021',
    'Partido Morado', 'Partido País para Todos', 'Partido Patriótico del Perú',
    'Partido Político Cooperación Popular', 'Partido Político Fuerza Moderna',
    'Partido Político Integridad Democrática', 'Partido Político Nacional Perú Libre', 'Perú Libre',
    'Partido Político Perú Acción', 'Partido Político Perú Primero',
    'Partido Político Peruanos Unidos: ¡Somos Libres!', 'Somos Libres',
    'Partido Político Popular Voces del Pueblo', 'Partido Político PRIN',
    'Partido Popular Cristiano', 'PPC', 'Partido SiCreo', 'Partido Unidad y Paz',
    'Perú Moderno', 'Podemos Perú', 'Primero la Gente', 'Progresemos',
    'Renovación Popular', 'Salvemos al Perú', 'Un Camino Diferente',
    # Involucrados clave
    'Keiko Fujimori', 'Vladimir Cerrón', 'Rafael López Aliaga', 'César Acuña',
    'Dina Boluarte', 'Pedro Castillo',
    # Términos generales
    'elecciones perú', 'ONPE', 'JNE', 'encuestas'
]

HEADLESS = True
WAIT_SEC = 15
MAX_VIEWMORE_CLICKS = 4
REQUEST_TIMEOUT = 20
OUTPUT_FILE = "news_scrapers/noticias_partidos.json"

SESSION_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/141.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
}

# ========== UTILIDADES ==========

def sleep_jitter(a=0.5, b=1.4):
    time.sleep(random.uniform(a, b))

def make_driver(headless: bool = True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu"); opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage"); opts.add_argument("--window-size=1280,2000")
    opts.add_argument("--lang=es-PE"); opts.add_argument(f"user-agent={SESSION_HEADERS['User-Agent']}")
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    except ImportError:
        print("[Info] webdriver_manager no encontrado. Asumiendo chromedriver en PATH.")
        driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    return driver

def is_full_url(href: str) -> bool:
    return href.startswith("http://") or href.startswith("https://")

def uniq_preserve_order(seq):
    seen=set(); out=[]
    for x in seq:
        if x not in seen: out.append(x); seen.add(x)
    return out

# ========== LÓGICA DE CARGA/GUARDADO (MODO DICCIONARIO CORREGIDO) ==========

def load_existing_data(filepath: str) -> Dict[str, Dict]:
    if not os.path.exists(filepath):
        print(f"[Info Main] No se encontró {filepath}. Se creará uno nuevo.")
        return {}
    url_to_news = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f: data = json.load(f)
        if isinstance(data, dict):
            # print("[Info Main] JSON principal cargado (Formato Diccionario).") # Verboso
            for key, item in data.items():
                if isinstance(item, dict):
                    url = item.get("url")
                    if url: url_to_news[url] = item
        elif isinstance(data, list):
            print("[Info Main] JSON principal cargado (Formato Lista Antiguo). Convirtiendo...")
            for item in data:
                if isinstance(item, dict):
                    url = item.get("url")
                    if url: url_to_news[url] = item
        else:
            print(f"[Warn Main] {filepath} contiene tipo inesperado. Empezando vacío.")
            return {}
        print(f"[Info Main] Cargadas {len(url_to_news)} noticias existentes (por URL) de {filepath}")
        return url_to_news
    except json.JSONDecodeError: print(f"[Warn Main] {filepath} corrupto. Empezando vacío."); return {}
    except Exception as e: print(f"[Error Main] Cargando {filepath}: {e}"); return {}

def save_updated_data(filepath: str, data_dict_by_url: Dict[str, Dict]):
    try:
        final_data_dict_by_id = {}
        for url, item in data_dict_by_url.items():
             item_id = str(item.get("_id", url))
             final_data_dict_by_id[item_id] = item
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_data_dict_by_id, f, ensure_ascii=False, indent=2)
        print(f"\n[Info Main] JSON principal guardado: {filepath} | Total: {len(final_data_dict_by_id)}")
    except Exception as e: print(f"\n[Error Main] Guardando {filepath}: {e}")

# ========== 1) EXTRAER URLS DE UNA PÁGINA DE BÚSQUEDA (CORREGIDO) ==========

def collect_article_urls_for_search(driver, term: str, max_clicks: int = 4) -> List[str]:
    """
    Entra a https://rpp.pe/buscar/{term}
    Hace click en "Ver más" max_clicks veces
    Devuelve todas las URLs de los artículos encontrados.
    """
    slug = quote(term)
    url = BASE_SEARCH_URL.format(slug=slug)
    print(f"[BUSCAR] Abriendo búsqueda: {url}")
    try:
        driver.get(url)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar la URL de búsqueda: {url}. Error: {e}")
        return []

    # --- ¡SELECTORES CORREGIDOS! ---
    # El contenedor de artículos en /buscar/ es 'div.container article'
    # El enlace está en 'h2.news__title a'
    ARTICLES_SELECTOR = "div.container article" # Selector para un artículo individual
    LINK_SELECTOR_IN_ARTICLE = "h2.news__title a" # Selector para el enlace dentro del artículo
    NO_RESULTS_XPATH = "//*[contains(text(), 'No se encontraron resultados') or contains(text(), 'no arrojó resultados')]"
    VIEW_MORE_BUTTON_SELECTOR = "button.button.button__viewmore"
    # --- FIN DE SELECTORES CORREGIDOS ---

    try:
        WebDriverWait(driver, WAIT_SEC).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ARTICLES_SELECTOR)),
                EC.presence_of_element_located((By.XPATH, NO_RESULTS_XPATH))
            )
        )
        print(f"[BUSCAR] Página '{term}' cargada (elementos detectados).")
    except TimeoutException:
         print(f"[WARN] No cargó ningún artículo ni mensaje 'sin resultados' para '{term}'.")
         return []

    try:
        no_results_el = driver.find_element(By.XPATH, NO_RESULTS_XPATH)
        if no_results_el.is_displayed():
             print(f"[INFO] Búsqueda '{term}' no arrojó resultados.")
             return []
    except Exception:
        pass

    def read_urls_now() -> List[str]:
        hrefs = []
        try:
            # Buscar todos los artículos
            articles = driver.find_elements(By.CSS_SELECTOR, ARTICLES_SELECTOR)
            
            for art in articles:
                try:
                    # Buscar el enlace del título dentro de cada artículo
                    a = art.find_element(By.CSS_SELECTOR, LINK_SELECTOR_IN_ARTICLE)
                    href = a.get_attribute("href")
                    if href and "-noticia-" in href: # Asegurarse de que es un enlace de noticia
                        hrefs.append(href.strip())
                except Exception:
                    continue # Saltar si este <article> no tiene el enlace esperado
        except Exception as e:
            print(f"[Debug read_urls] Error buscando artículos: {e}")
        
        return hrefs

    urls = read_urls_now()
    initial_count = len(urls)
    print(f"[BUSCAR] {term}: {initial_count} URLs iniciales encontradas.")
    if initial_count == 0:
        print(f"[WARN] {term}: La página cargó pero no se parsearon URLs. Revisar selectores.")

    # Clics controlados
    for i in range(max_clicks):
        sleep_jitter()
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, VIEW_MORE_BUTTON_SELECTOR))
            )
        except TimeoutException:
            print(f"[INFO] No hay más botón 'Ver más' para '{term}' después de {i} clics.")
            break

        before_count = len(read_urls_now())

        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            sleep_jitter(0.3, 0.6)
            driver.execute_script("arguments[0].click();", btn)
            print(f"[BUSCAR] Clic {i+1} en 'Ver más' para '{term}'.")
        except Exception as e:
             print(f"[WARN] Falló el clic en 'Ver más' para '{term}'. Deteniendo. Error: {e}")
             break

        grew = False
        t0 = time.time()
        while time.time() - t0 < 10: # Esperar 10s
            sleep_jitter(0.3, 0.7)
            current_urls = read_urls_now()
            if len(current_urls) > before_count:
                print(f"[BUSCAR] {term}: URLs aumentaron a {len(current_urls)}.")
                urls = current_urls
                grew = True
                break
            driver.execute_script("window.scrollBy(0, 150);")

        if not grew:
            print(f"[INFO] Clic {i+1} en 'Ver más' no cargó nuevos artículos para '{term}'. Deteniendo.")
            break

    urls = uniq_preserve_order(urls)
    urls = [u if is_full_url(u) else urljoin(BASE_SITE, u) for u in urls]
    print(f"[BUSCAR] {term}: {len(urls)} URLs únicas finales encontradas tras {max_clicks} clic(s).")
    return urls


# ========== 2) PARSEAR CADA ARTÍCULO ==========

def fetch_article(url: str, search_term: str) -> Dict:
    """ Parsea el artículo y lo devuelve en el formato de diccionario unificado. """
    try:
        r = requests.get(url, headers=SESSION_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e: print(f"[Fetch Error] {url}: {e}"); return None

    soup = BeautifulSoup(r.text, "html.parser")
    title_el = soup.select_one("h1.article__title, h1.title"); title = title_el.get_text(strip=True) if title_el else None
    body_el = soup.select_one("div.body, div.article-content"); paragraphs = []
    if body_el:
        for node in body_el.select("p, li"):
            txt = node.get_text(" ", strip=True)
            if txt and len(txt) > 20 and "function(" not in txt and "{" not in txt: paragraphs.append(txt)
    content = "\n".join(paragraphs) if paragraphs else None
    teaser_el = soup.select_one("h2.article__subtitle, p.article__subtitle"); teaser = teaser_el.get_text(strip=True) if teaser_el else ""
    if not teaser and paragraphs: teaser = paragraphs[0]
    date_el = soup.select_one("time[datetime]"); date_str = date_el['datetime'] if date_el else None

    if not title or not content: print(f"[Parse Error] {url}: Título o contenido vacíos."); return None

    try: id_part = url.split('-noticia-')[-1].split('?')[0]; article_id = f"rpp_{id_part}" if id_part.isdigit() else f"rpp_{url.split('/')[-1].split('?')[0]}"
    except Exception: article_id = f"rpp_{hash(url)}"
    fecha_dt = datetime.datetime.now(datetime.timezone.utc); date_iso = fecha_dt.strftime('%Y-%m-%d %H:%M:%S') # Placeholder

    return { "_id": article_id, "title": title, "type": "article", "date": date_iso, "update_date": date_iso,
             "created_at": date_iso, "slug": url.replace(BASE_SITE, "").lstrip('/'), "url": url,
             "data": { "__typename": "ArticleDataType", "teaser": teaser, "authors": [],
                       "tags": [{'__typename':'TagType', 'name': search_term, 'slug': f'/tag/{search_term.lower()}'}],
                       "categories": [], "multimedia": [] },
             "metadata_seo": {"keywords": search_term}, "metadata": [{"key": "source", "value": "RPP"}],
             "has_video": False, "contenido_full": content }


# ========== 3) PIPELINE PRINCIPAL ==========

def main():
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir and not os.path.exists(output_dir): os.makedirs(output_dir)

    existing_data_by_url = load_existing_data(OUTPUT_FILE)
    initial_count = len(existing_data_by_url)
    driver = None

    try:
        driver = make_driver(headless=HEADLESS)
        all_urls: List[tuple] = []
        for term in KEYWORDS:
            urls_term = collect_article_urls_for_search(
                driver, term, max_clicks=MAX_VIEWMORE_CLICKS,
            )
            for u in urls_term: all_urls.append((term, u))

        final_urls = []
        seen_tmp = set()
        for term, u in all_urls:
            if u in seen_tmp: continue
            seen_tmp.add(u); final_urls.append((term, u))

        print(f"[INFO] URLs únicas encontradas: {len(final_urls)}")
        urls_to_fetch = [(term, url) for term, url in final_urls if url not in existing_data_by_url]
        print(f"[INFO] URLs nuevas a procesar: {len(urls_to_fetch)}")

        new_articles_count = 0
        for term, url in urls_to_fetch:
            if url in existing_data_by_url: continue
            art_dict = fetch_article(url, term)
            if art_dict:
                existing_data_by_url[url] = art_dict; new_articles_count += 1
            if new_articles_count > 0 and new_articles_count % 25 == 0:
                save_updated_data(OUTPUT_FILE, existing_data_by_url)
                print(f"[SAVE] {len(existing_data_by_url)} artículos (parcial). {new_articles_count} nuevos.")
            sleep_jitter(0.1, 0.4)

        save_updated_data(OUTPUT_FILE, existing_data_by_url)
        print(f"[OK] Terminado. {new_articles_count} nuevos añadidos.")
        print(f"Total artículos en {OUTPUT_FILE}: {len(existing_data_by_url)}")

    finally:
        if driver:
            try: driver.quit()
            except Exception as e: print(f"[WARN] Error al cerrar driver: {e}")


if __name__ == "__main__":
    main()