# canaln_scraper_contenido_y_paginacion_robusta.py
# -*- coding: utf-8 -*-

import json
import time
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote
import datetime # Importado datetime directamente

import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, ElementClickInterceptedException, StaleElementReferenceException,
    NoSuchElementException
)
from webdriver_manager.chrome import ChromeDriverManager
import os

BASE = "https://canaln.pe"
UA = ("Mozilla5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA}

# ===== Ajustes =====
EXPECTED_PER_PAGE = 15
CARDS_TIMEOUT = 15
STABLE_CYCLES = 3
STABLE_SLEEP = 0.3
PAGE_RENDER_PAUSE = 1.0
PAGINATION_CLICK_TIMEOUT = 10
PAGINATION_LOAD_TIMEOUT = 20

# ===== Archivo JSON Principal =====
OUTPUT_FILE = "news_scrapers/noticias_partidos.json"

# =========================
# Driver
# =========================
def make_driver(headless=False):
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1400,2300")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--user-agent={UA}")
    try:
        service = Service(ChromeDriverManager().install())
    except ValueError as e:
        print(f"[Error WebDriver] Problema al instalar/encontrar ChromeDriver: {e}")
        raise
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    return driver

# =========================
# Helpers de Paginación (Mejorados)
# =========================
def close_cookies_if_any(driver):
    try:
        wait = WebDriverWait(driver, 5)
        cookie_button = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[contains(translate(., 'ACEPTAR', 'aceptar'), 'aceptar') or contains(@id, 'cookie') or contains(@aria-label, 'accept')]")))
        driver.execute_script("arguments[0].click();", cookie_button)
        print("[Info] Cerré banner de cookies.")
        time.sleep(0.5)
    except TimeoutException:
        pass
    except Exception as e:
        print(f"[Warn] Error intentando cerrar cookies: {e}")

def find_pagers(driver):
    # --- ¡CORRECCIÓN! Revertido a tu XPath original que funcionaba ---
    pagers = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'md:flex') and contains(@class,'px-2') and contains(@class,'md:gap-56')]"
    )
    # --- FIN DE LA CORRECCIÓN ---
    return pagers

def get_pager_2(driver):
    pagers = find_pagers(driver)
    # Usar el último paginador encontrado (suele ser el de abajo)
    return pagers[-1] if pagers else None

def read_current_page(pager) -> Optional[int]:
    try:
        inp = pager.find_element(By.XPATH, ".//input[@type='number']")
        val = inp.get_attribute("value")
        if val: return int(val.strip())
    except Exception: pass
    try:
        active_el = pager.find_element(By.XPATH, ".//button[(@aria-current='page' or contains(@class, 'active') or contains(@class, 'bg-primary')) and number(normalize-space())] | .//a[(@aria-current='page' or contains(@class, 'active') or contains(@class, 'bg-primary')) and number(normalize-space())]")
        val = active_el.text
        if val: return int(val.strip())
    except Exception: pass
    
    # Fallback: Leer el input readonly de tu script original
    try:
        inp_readonly = pager.find_element(By.XPATH, ".//input[@type='text' and @readonly]")
        val = inp_readonly.get_attribute("value") or inp_readonly.get_attribute("aria-valuenow") or "1"
        if val: return int(val.strip())
    except Exception: pass
    
    return 1 # Asumir página 1 si todo falla

def find_next_button_in_pager(pager):
    """ Busca el botón/enlace 'siguiente' de forma más robusta y priorizada. """
    
    # --- Intento 1: El XPath de tu script original (penúltimo botón) ---
    try:
        xpath_btns = (
            ".//div[contains(@class,'flex') and contains(@class,'gap-40')]"
            "//div[contains(@class,'flex') and contains(@class,'gap-2') "
            "and contains(@class,'items-center') and contains(@class,'px-2') and contains(@class,'pt-8')]//button"
        )
        btns = pager.find_elements(By.XPATH, xpath_btns)
        if len(btns) >= 2:
            # print("[Debug Pager] Botón 'siguiente' encontrado con XPath original (penúltimo).")
            return btns[-2] # penúltimo = siguiente
    except Exception: pass

    # --- Fallback a selectores más robustos ---
    # Prioridad 1: Enlaces con rel="next"
    try:
        btn = pager.find_element(By.XPATH, ".//a[@rel='next']")
        # print("[Debug Pager] Botón 'siguiente' encontrado con rel='next'.")
        if 'disabled' not in btn.get_attribute('class') and 'pointer-events-none' not in btn.get_attribute('class'):
            return btn
    except NoSuchElementException: pass

    # Prioridad 2: Botones/Enlaces con Aria-label o texto específico
    selectors_priority = [
        ".//button[contains(@aria-label, 'Siguiente') or contains(@aria-label, 'Next')]",
        ".//a[contains(@aria-label, 'Siguiente') or contains(@aria-label, 'Next')]",
        ".//button[normalize-space()='Siguiente' or normalize-space()='Next']",
        ".//a[normalize-space()='Siguiente' or normalize-space()='Next']",
    ]
    for xpath in selectors_priority:
        try:
            btn = pager.find_element(By.XPATH, xpath)
            if btn.is_enabled() and btn.is_displayed():
                # print(f"[Debug Pager] Botón 'siguiente' encontrado con: {xpath}")
                return btn
        except NoSuchElementException: continue

    # Prioridad 3: Iconos SVG
    svg_selectors = [ ".//button[.//svg[contains(@data-testid, 'ChevronRight')]]", ".//a[.//svg[contains(@data-testid, 'ChevronRight')]]" ]
    for xpath in svg_selectors:
        try:
            btn = pager.find_element(By.XPATH, xpath)
            if btn.is_enabled() and btn.is_displayed():
                 # print(f"[Debug Pager] Botón 'siguiente' (SVG) encontrado con: {xpath}")
                 return btn
        except NoSuchElementException: continue

    # Prioridad 4: Texto simple
    text_selectors = [ ".//button[normalize-space()='>']", ".//a[normalize-space()='>']" ]
    for xpath in text_selectors:
         try:
              btn = pager.find_element(By.XPATH, xpath)
              if btn.is_enabled() and btn.is_displayed():
                   # print(f"[Debug Pager] Botón 'siguiente' (Texto) encontrado con: {xpath}")
                   return btn
         except NoSuchElementException: continue

    print("[Warn Pager] No se encontró un botón 'siguiente' claro o habilitado tras varios intentos.")
    return None

def click_element(driver, el):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            wait = WebDriverWait(driver, PAGINATION_CLICK_TIMEOUT)
            clickable_el = wait.until(EC.element_to_be_clickable(el))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", clickable_el)
            time.sleep(0.5)
            ActionChains(driver).move_to_element(clickable_el).pause(0.2).click(clickable_el).perform()
            # print("[Debug] Clic (ActionChains) en intento {}.".format(attempt + 1))
            return True
        except (StaleElementReferenceException, ElementClickInterceptedException) as e:
            print(f"[Warn] Clic (ActionChains) falló en intento {attempt + 1}: {e}. Reintentando con JS...")
            try:
                driver.execute_script("arguments[0].click();", el)
                # print("[Debug] Clic (JS Fallback) en intento {}.".format(attempt + 1))
                return True
            except Exception as e2:
                 print(f"[Error] Clic (JS Fallback) falló en intento {attempt + 1}: {e2}")
                 if attempt == max_retries - 1: return False
                 time.sleep(0.5)
        except TimeoutException:
             print(f"[Error] Timeout esperando que el elemento sea clickeable en intento {attempt+1}.")
             return False
    return False

def wait_page_load(driver, prev_first_url: str, prev_page_num: int, pager_locator_func, timeout=PAGINATION_LOAD_TIMEOUT):
    start_time = time.time()
    print(f"[Wait Load] Esperando cambio desde URL='{prev_first_url[:60]}...' y/o Pag={prev_page_num}")
    detected_change = False
    while time.time() - start_time < timeout:
        try:
            current_first_url = get_first_card_url(driver)
            if current_first_url and current_first_url != prev_first_url:
                print(f"[Wait Load] ÉXITO: Primer card URL cambió a: {current_first_url[:60]}...")
                time.sleep(0.1)
                if get_first_card_url(driver) == current_first_url:
                     detected_change = True
                     break
                else:
                     print("[Wait Load] URL cambió pero fue inestable, continuando espera...")
                     prev_first_url = current_first_url
        except Exception: pass
        try:
            current_pager = pager_locator_func(driver)
            if current_pager:
                current_page_num = read_current_page(current_pager)
                if current_page_num is not None and current_page_num > prev_page_num:
                    print(f"[Wait Load] ÉXITO: Número de página aumentó a: {current_page_num}")
                    detected_change = True
                    break
        except Exception: pass
        time.sleep(0.6)
    if not detected_change:
        print(f"[Wait Load Timeout] No se detectó cambio de URL ni de página en {timeout}s.")
    return detected_change


# =========================
# Parsers del listado
# =========================
CARDS_XPATH = "//article[contains(@class,'md:flex') and contains(@class,'my-4')]"

def parse_cards_from_dom(driver) -> List[Dict]:
    items = []
    try:
        cards = driver.find_elements(By.XPATH, CARDS_XPATH)
    except Exception as e:
        print(f"[Warn Parse] Error buscando cards: {e}")
        return items

    for idx, c in enumerate(cards):
        try:
            categoria = fecha_hora = titulo = ""
            url = ""

            a_title = c.find_element(By.XPATH, ".//p[contains(@class,'font-bold') and contains(@class,'text-lg')]//a")
            href = a_title.get_attribute("href")
            if not href: continue
            url = urljoin(BASE, href.strip())
            if not url or url == BASE + "/": continue

            titulo = a_title.get_attribute("innerText").strip()
            if not titulo: continue

            try:
                info_ps = c.find_elements(By.XPATH, ".//p[contains(@class,'font-semibold') and contains(@class,'text-xs')]")
                categoria = info_ps[0].get_attribute("innerText").strip() if len(info_ps) > 0 else ""
                fecha_hora = info_ps[1].get_attribute("innerText").strip() if len(info_ps) > 1 else ""
            except Exception: pass

            try:
                slug_part = url.split('/')[-1].split('?')[0]
                if not slug_part: slug_part = f"hash_{hash(url)}"
                item_id = f"canaln_{slug_part}"
            except Exception:
                item_id = f"canaln_hash_{hash(url)}"

            items.append({
                "_id": item_id,
                "title": titulo, "url": url, "categoria": categoria,
                "fecha_hora": fecha_hora, "fuente": "Canal N"
             })
        except Exception as e:
            continue
    return items

def get_first_card_url(driver) -> str:
    try:
        wait = WebDriverWait(driver, 3)
        el = wait.until(EC.presence_of_element_located((
             By.XPATH, f"({CARDS_XPATH})[1]//p[contains(@class,'font-bold') and contains(@class,'text-lg')]//a"
        )))
        href = el.get_attribute("href")
        return urljoin(BASE, href or "")
    except Exception:
        return ""


# =========================
# Esperas para carga de tarjetas
# =========================
def count_cards(driver) -> int:
    try: return len(driver.find_elements(By.XPATH, CARDS_XPATH))
    except Exception: return 0

def wait_cards_count(driver, expected=EXPECTED_PER_PAGE, timeout=CARDS_TIMEOUT) -> int:
    t0 = time.time(); last = 0
    while time.time() - t0 <= timeout:
        n = count_cards(driver)
        if n > last: t0 = time.time()
        last = n
        if n >= expected: return n
        driver.execute_script("window.scrollBy(0, 350);"); time.sleep(0.3)
    return last

def wait_cards_stable(driver, stable_cycles=STABLE_CYCLES, sleep_s=STABLE_SLEEP, timeout=CARDS_TIMEOUT) -> int:
    t0 = time.time(); last = -1; stable = 0; max_count = 0
    while time.time() - t0 <= timeout:
        n = count_cards(driver); max_count = max(n, max_count)
        if n == last: stable += 1
        else: stable = 0; last = n
        if stable >= stable_cycles and n > 0: return n
        if n == 0 and stable >= stable_cycles: return 0
        driver.execute_script("window.scrollBy(0, 100);"); time.sleep(sleep_s)
    return max_count

def wait_results_ready(driver) -> int:
    n = wait_cards_count(driver, expected=EXPECTED_PER_PAGE, timeout=CARDS_TIMEOUT)
    if n < EXPECTED_PER_PAGE:
        n = wait_cards_stable(driver, stable_cycles=STABLE_CYCLES, timeout=CARDS_TIMEOUT)
    time.sleep(PAGE_RENDER_PAUSE)
    return n


# =========================
# EXTRACTOR DE CONTENIDO
# =========================
def fetch_html(url: str, timeout: int = 30) -> Optional[str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status(); resp.encoding = resp.apparent_encoding
        return resp.text
    except requests.exceptions.RequestException as e: print(f"[Error Fetch] {url}: {e}"); return None
    except Exception as e: print(f"[Error Fetch Inesperado] {url}: {e}"); return None

def get_first_paragraph(soup: BeautifulSoup) -> str:
    h2 = soup.find("h2", class_="leading-7 font-light text-xl")
    if not h2: return ""
    p = h2.find("p"); return p.get_text(" ", strip=True) if p else h2.get_text(" ", strip=True)

def get_body_text_excluding_last3(soup: BeautifulSoup) -> str:
    target_classes = {"px-4", "xl:px-0", "md:px-0"}
    def is_exact_div(tag):
        return tag.name == "div" and tag.has_attr("class") and set(tag.get("class", [])) == target_classes
    parent_div = soup.find(is_exact_div)
    if not parent_div: return ""
    child_divs = parent_div.find_all("div", recursive=False)
    if len(child_divs) > 3: child_divs = child_divs[:-3]
    texts = [div.get_text(" ", strip=True) for div in child_divs if div.get_text(strip=True)]
    return "\n\n".join(texts)

def extract_article_content(url: str) -> Dict[str, str]:
    html = fetch_html(url)
    if html is None: return { "contenido": "[ERROR AL OBTENER HTML]", "primer_parrafo": "", "texto_div": "" }
    soup = BeautifulSoup(html, "html.parser")
    first_paragraph = get_first_paragraph(soup)
    body_text = get_body_text_excluding_last3(soup)
    parts = [t for t in [first_paragraph, body_text] if t]
    texto_total = "\n\n".join(parts) if parts else ""
    return {"primer_parrafo": first_paragraph, "texto_div": body_text, "contenido": texto_total}


# =========================
# Scraper por término
# =========================
def scrape_term(term: str, existing_data: Dict, max_pages: Optional[int] = None, headless: bool = True) -> List[Dict]:
    encoded_term = quote(term)
    url = f"{BASE}/buscar/{encoded_term}"
    driver = None
    results_this_term: List[Dict] = []
    
    try:
        driver = make_driver(headless=headless)
        print(f"[{term}] Navegando a: {url}")
        driver.get(url)
        close_cookies_if_any(driver)

        try:
             wait = WebDriverWait(driver, 15)
             wait.until(EC.any_of(
                  EC.presence_of_element_located((By.XPATH, CARDS_XPATH)),
                  EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'No se encontraron resultados')]"))
             ))
             print(f"[{term}] Página inicial cargada.")
        except TimeoutException:
             print(f"[Error] Timeout inicial '{term}'. Saltando.")
             return results_this_term

        try:
             no_results_el = driver.find_element(By.XPATH, "//*[contains(text(), 'No se encontraron resultados')]")
             if no_results_el.is_displayed():
                  print(f"[{term}] No resultados.")
                  return results_this_term
        except NoSuchElementException:
            pass

        page_idx = 1
        pager = get_pager_2(driver)
        if pager:
            page_idx = read_current_page(pager) or 1
        print(f"[{term}] Página inicial: ~{page_idx}")

        pages_done = 0
        while True:
            current_page_num_for_debug = page_idx
            print(f"[{term}] Procesando pág ~{current_page_num_for_debug}...")
            
            cards_ready = wait_results_ready(driver)
            print(f"[{term}] Pag.{current_page_num_for_debug}: {cards_ready} cards listos.")
            
            if cards_ready == 0:
                print(f"[{term}] No más cards. Fin.")
                break
            
            items_on_page = parse_cards_from_dom(driver)
            
            if not items_on_page and cards_ready > 0:
                print(f"[Warn] {cards_ready} cards pero 0 parseados. Reintentando...")
                time.sleep(2)
                items_on_page = parse_cards_from_dom(driver)

            if not items_on_page:
                print(f"[{term}] Pag.{current_page_num_for_debug}: No items parseados. Fin.")
                break

            new_items_on_page = 0
            for r in items_on_page:
                item_url = r.get("url")
                if not item_url:
                    continue
                
                if item_url not in existing_data:
                    print(f"[{term}] Pag.{current_page_num_for_debug}: Nueva -> {r.get('title','?')[:50]}...")
                    content = extract_article_content(item_url)
                    r.update(content)
                    r["termino_busqueda"] = term
                    
                    fecha_dt = datetime.datetime.now(datetime.timezone.utc) if r.get("fecha_hora") else None
                    
                    noticia_formateada = {
                         "_id": r["_id"], "title": r.get("title", ""), "type": "article",
                         "date": fecha_dt.strftime('%Y-%m-%d %H:%M:%S') if fecha_dt else None,
                         "update_date": fecha_dt.strftime('%Y-%m-%d %H:%M:%S') if fecha_dt else None,
                         "created_at": fecha_dt.strftime('%Y-%m-%d %H:%M:%S') if fecha_dt else None,
                         "slug": item_url.replace(BASE, "").lstrip('/'),
                         "url": item_url,
                         "data": {
                              "__typename": "ArticleDataType",
                              "teaser": r.get("primer_parrafo", ""),
                              "authors": [],
                              "tags": [{'__typename':'TagType', 'name': t, 'slug': f'/tag/{t.lower()}'} for t in [r.get("categoria"), term] if t],
                              "categories": [{'__typename':'CategoryReferenceType', 'name': r.get("categoria"), 'slug': f'/{r.get("categoria","").lower()}'}] if r.get("categoria") else [],
                              "multimedia": []
                         },
                         "metadata_seo": {"keywords": term},
                         "metadata": [{"key": "source", "value": "Canal N"}],
                         "has_video": False,
                         "contenido_full": r.get("contenido", "")
                    }
                    results_this_term.append(noticia_formateada)
                    existing_data[item_url] = noticia_formateada
                    new_items_on_page += 1

            print(f"[{term}] Pag.{current_page_num_for_debug}: Añadidas {new_items_on_page} noticias NUEVAS.")
            
            pages_done += 1
            if max_pages is not None and pages_done >= max_pages:
                print(f"[{term}] Límite {max_pages} pág.")
                break
            
            pager = get_pager_2(driver)
            if not pager:
                print(f"[{term}] No paginador. Fin.")
                break
                
            before_val = read_current_page(pager) or page_idx
            prev_first = get_first_card_url(driver)
            if not prev_first and cards_ready > 0:
                time.sleep(0.5)
                prev_first = get_first_card_url(driver)
                
            btn_next = find_next_button_in_pager(pager)
            if not btn_next:
                print(f"[{term}] No botón 'siguiente'. Fin.")
                break
                
            print(f"[{term}] Clic 'siguiente'...")
            clicked = click_element(driver, btn_next)
            if not clicked:
                print(f"[Error] Falló clic. Abortando '{term}'.")
                break
                
            print(f"[{term}] Esperando pág {page_idx + 1}...")
            ok = wait_page_load(driver, prev_first, before_val, get_pager_2, timeout=PAGINATION_LOAD_TIMEOUT)
            if not ok:
                print(f"[{term}] No cambio detectado. Fin.")
                break
                
            current_pager = get_pager_2(driver)
            page_idx = (read_current_page(current_pager) or (page_idx + 1)) if current_pager else page_idx + 1
            print(f"[{term}] Avanzado a pág ~{page_idx}")
            time.sleep(PAGE_RENDER_PAUSE)
            
    except Exception as e:
        print(f"[Error Fatal] '{term}': {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
                
    return results_this_term


# =========================
# Main
# =========================
def load_existing_data(filepath: str) -> Dict[str, Dict]:
    if not os.path.exists(filepath):
        print(f"[Info Main] No {filepath}. Creando.")
        return {}
    url_to_news = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for key, item in data.items():
                if isinstance(item, dict):
                    url = item.get("url")
                    if url:
                        url_to_news[url] = item
        elif isinstance(data, list):
            print("[Info Main] JSON era lista. Convirtiendo...")
            for item in data:
                if isinstance(item, dict):
                    url = item.get("url")
                    if url:
                        url_to_news[url] = item
        else:
            print(f"[Warn Main] {filepath} tipo inesperado.")
            return {}
        print(f"[Info Main] Cargadas {len(url_to_news)} noticias (por URL) de {filepath}")
        return url_to_news
    except json.JSONDecodeError:
        print(f"[Warn Main] {filepath} corrupto.")
        return {}
    except Exception as e:
        print(f"[Error Main] Cargando {filepath}: {e}")
        return {}

def save_updated_data(filepath: str, data_dict_by_url: Dict[str, Dict]):
    try:
        final_data_dict_by_id = {}
        for url, item in data_dict_by_url.items():
            item_id = str(item.get("_id", url))
            final_data_dict_by_id[item_id] = item
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_data_dict_by_id, f, ensure_ascii=False, indent=2)
        print(f"\n[Info Main] JSON guardado: {filepath} | Total: {len(final_data_dict_by_id)}")
    except Exception as e:
        print(f"\n[Error Main] Guardando {filepath}: {e}")

# --- ¡INICIO DE LA CORRECCIÓN! ---
# Mover la lógica de ejecución a una función main()

def main():
    terms_to_scrape = [ # Partidos (y siglas comunes)
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
    headless = True
    max_pages_per_term = 3

    print("--- Iniciando Scraper de Canal N (Actualizando JSON Principal) ---")
    existing_data_by_url = load_existing_data(OUTPUT_FILE)
    initial_count = len(existing_data_by_url)
    added_count_total = 0

    for t in terms_to_scrape:
        print(f"\n=== [Canal N] Scrapeando término: {t} ===")
        new_data_list = scrape_term(t, existing_data=existing_data_by_url, max_pages=max_pages_per_term, headless=headless)
        added_count_total += len(new_data_list)

    final_count = len(existing_data_by_url)
    print("\n--- Scraping de Canal N Completado ---")
    print(f"Noticias NUEVAS de Canal N agregadas en esta ejecución: {added_count_total}")
    print(f"Total de noticias en la base de datos principal ahora: {final_count}")

    save_updated_data(OUTPUT_FILE, existing_data_by_url)

if __name__ == "__main__":
    main() # Llamar a la función main
# --- FIN DE LA CORRECCIÓN ---