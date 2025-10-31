# -*- coding: utf-8 -*-
"""
Scraping de TV Perú por TÉRMINOS DE BÚSQUEDA (MODO DICCIONARIO CORREGIDO v6)
Carga noticias_partidos.json, busca términos en TV Perú, añade noticias nuevas,
y guarda el diccionario principal actualizado.
Selectores de contenido mejorados.
"""

import os
import json
import time
import re
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, quote
import datetime
import random

import requests
from bs4 import BeautifulSoup

# ========== CONFIGURACIÓN ==========
BASE_SITE = "https://www.tvperu.gob.pe"
BASE_SEARCH_URL = "https://www.tvperu.gob.pe/search/node/{slug}"

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

REQUEST_TIMEOUT = 20
OUTPUT_FILE = "news_scrapers/noticias_partidos.json"
MAX_PAGINAS_POR_BUSQUEDA = 5

SESSION_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://www.tvperu.gob.pe/'
}

# ========== UTILIDADES ==========

def sleep_jitter(a=0.8, b=1.5):
    time.sleep(random.uniform(a, b))

def limpiar_texto(texto):
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.strip()
    return texto

# ========== LÓGICA DE CARGA/GUARDADO ==========

def load_existing_data(filepath: str) -> Dict[str, Dict]:
    # (Sin cambios respecto a la versión anterior)
    if not os.path.exists(filepath):
        print(f"[Info Main] No se encontró {filepath}. Creando.")
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
    # (Sin cambios respecto a la versión anterior)
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

# ========== SCRAPER TV PERÚ ==========

class TVPeruScraper:
    def __init__(self, keywords: List[str], output_file: str, max_paginas: int):
        self.base_url = BASE_SITE
        self.search_url_template = BASE_SEARCH_URL
        self.keywords = keywords
        self.output_file = output_file
        self.max_paginas_por_busqueda = max_paginas
        self.session = requests.Session()
        self.session.headers.update(SESSION_HEADERS)
        self.existing_data_by_url = {}

    def _extraer_numero_paginas(self, soup):
        # (Sin cambios)
        try:
            paginacion = soup.find('ul', class_='pager')
            if not paginacion: return 1
            items_pagina = paginacion.find_all('li', class_='pager-item')
            numeros_pagina = [int(item.find('a').get_text(strip=True)) for item in items_pagina if item.find('a') and item.find('a').get_text(strip=True).isdigit()]
            return max(numeros_pagina) if numeros_pagina else 1
        except Exception: return 1

    def _construir_url_pagina(self, url_base, numero_pagina):
        # (Sin cambios)
        return f"{url_base}?page={numero_pagina}" if numero_pagina > 0 else url_base

    def _extraer_enlaces_de_pagina(self, url_pagina, numero_pagina, termino_busqueda):
        # (Sin cambios respecto a la versión anterior)
        print(f"\n--- [TV Perú] Pag.{numero_pagina + 1} ({termino_busqueda}) ---")
        print(f"🔗 {url_pagina}")
        try:
            response = self.session.get(url_pagina, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            enlaces = []
            contenedor_resultados = soup.find('ul', class_='search-results') or soup.find('div', class_='view-content')
            if not contenedor_resultados:
                print("   ⚠️ No se encontró contenedor de resultados.")
                return []

            resultados = contenedor_resultados.find_all(['li', 'div'], class_=re.compile('search-result|views-row'))
            print(f"   🔍 Encontrados {len(resultados)} items en la página.")
            for idx, resultado in enumerate(resultados, 1):
                enlace = resultado.find('a')
                if enlace and enlace.get('href'):
                    href = enlace['href']
                    titulo = limpiar_texto(enlace.get_text())

                    if href.startswith('/'): url_completa = urljoin(self.base_url, href)
                    elif href.startswith('http'): url_completa = href
                    else: continue

                    extensiones_invalidas = ['.jpg', '.png', '.pdf', '.gif', '.jpeg', '/user/']
                    if not any(url_completa.lower().endswith(ext) for ext in extensiones_invalidas):
                        if url_completa not in [e['url'] for e in enlaces]:
                             enlaces.append({
                                 'url': url_completa,
                                 'titulo_busqueda': titulo,
                                 'termino_busqueda': termino_busqueda
                             })

            print(f"   ✅ Enlaces de noticias válidos extraídos: {len(enlaces)}")
            return enlaces

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error red: {e}")
            return []
        except Exception as e:
            print(f"   ❌ Error pág {numero_pagina + 1}: {e}")
            return []

    def _extraer_contenido_noticia(self, url, titulo_busqueda, termino_busqueda):
        print(f"   -> 📰 Procesando: {url}")
        if url in self.existing_data_by_url:
            print("      ⚠️ Ya existe. Saltando.")
            return None

        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            title_el = soup.select_one("h1.title, h1[property='dc:title'], h1#page-title")
            title = limpiar_texto(title_el.get_text()) if title_el else titulo_busqueda

            fecha_str = None
            fecha_el = soup.select_one("span.date-display-single, time[datetime], div.fecha-detalle")
            if fecha_el:
                fecha_str = limpiar_texto(fecha_el.get('datetime') or fecha_el.get_text())

            teaser = ""
            teaser_el = soup.select_one("div.field-name-field-entradilla .field-item, p.lead, h2.article__subtitle")
            if teaser_el:
                teaser = limpiar_texto(teaser_el.get_text())

            # --- ¡INICIO DE LA CORRECCIÓN DE CONTENIDO! ---
            content = ""
            content_el = None

            # Lista de selectores a probar, del más específico al más general
            content_selectors = [
                "div.field-name-body .field-items .field-item", # Estructura común en Drupal
                "div.field-name-body .field-item",
                "div.field-name-body",
                "div.cuerpo-detalle",
                "div.node-content .content",
                "div[class*='article-body']",
                "div[class*='content-body']",
                "div[itemprop='articleBody']",
                "article", # Como último recurso, buscar dentro de <article>
                "main"     # O dentro de <main>
            ]

            for selector in content_selectors:
                content_el = soup.select_one(selector)
                if content_el:
                    # Intentar extraer párrafos de este contenedor
                    parrafos = content_el.find_all('p', recursive=True) # Buscar en todos los niveles
                    if len(parrafos) > 1: # Si encontramos al menos 2 párrafos, asumimos que es el correcto
                        print(f"      [Debug Content] Contenido encontrado con selector: '{selector}'")
                        break # Salir del bucle de selectores
                    else:
                        content_el = None # No era el contenedor correcto, seguir probando
                # else: print(f"[Debug Content] Selector no encontrado: {selector}") # Verboso

            if not content_el:
                print(f"      ⚠️ No se encontró un contenedor de contenido principal claro.")
                content_el = soup.find('body') # Usar body como último recurso absoluto

            # Extraer párrafos del contenedor encontrado
            if content_el:
                parrafos = content_el.find_all('p')
                parrafos_validos = []
                palabras_excluir = ['suscríbete', 'síguenos', 'newsletter', 'publicidad', 'compartir', 'tags:', 'etiquetas:', 'lee también', 'foto:', 'crédito:']
                for p in parrafos:
                    texto = limpiar_texto(p.get_text())
                    # Validar párrafo (ajustar longitud mínima si es necesario)
                    if len(texto) > 30 and not any(palabra in texto.lower() for palabra in palabras_excluir):
                         if texto != title and texto != teaser:
                             parrafos_validos.append(texto)
                content = '\n\n'.join(parrafos_validos)
            # --- ¡FIN DE LA CORRECCIÓN DE CONTENIDO! ---

            if not title or len(content) < 50: # Reducir ligeramente el mínimo de contenido
                print(f"      ⚠️ Contenido insuficiente (T:{bool(title)}, C:{len(content)} chars)")
                return None

            try:
                match = re.search(r'/node/(\d+)', url)
                article_id = f"tvperu_{match.group(1)}" if match else f"tvperu_hash_{hash(url)}"
            except Exception:
                article_id = f"tvperu_hash_{hash(url)}"

            fecha_dt = datetime.datetime.now(datetime.timezone.utc)
            date_iso = fecha_dt.strftime('%Y-%m-%d %H:%M:%S')

            noticia_formateada = {
                 "_id": article_id, "title": title, "type": "article", "date": date_iso, "update_date": date_iso,
                 "created_at": date_iso, "slug": url.replace(self.base_url, "").lstrip('/'), "url": url,
                 "data": { "__typename": "ArticleDataType", "teaser": teaser, "authors": [],
                           "tags": [{'__typename':'TagType', 'name': termino_busqueda, 'slug': f'/tag/{termino_busqueda.lower()}'}],
                           "categories": [], "multimedia": [] },
                 "metadata_seo": {"keywords": termino_busqueda},
                 "metadata": [{"key": "source", "value": "TV Peru"}],
                 "has_video": False, "contenido_full": content
            }
            print(f"      ✅ OK: {title[:60]}...")
            return noticia_formateada

        except requests.exceptions.RequestException as e:
            print(f"      ❌ Error red: {e}")
            return None
        except Exception as e:
            print(f"      ❌ Error extrayendo: {e}")
            # import traceback # Descomentar para debug detallado
            # traceback.print_exc() # Descomentar para debug detallado
            return None

    def scrape_keyword(self, keyword):
        # (Sin cambios respecto a la versión anterior)
        print("\n" + "="*70); print(f"🔍 [TV Perú] - Keyword: {keyword.upper()}"); print("="*70 + "\n")
        slug = quote(keyword); url_semilla = self.search_url_template.format(slug=slug)
        print(f"📍 URL: {url_semilla}"); print(f"📄 Máx Pág: {self.max_paginas_por_busqueda}\n")
        total_paginas = 1
        try:
            response = self.session.get(url_semilla, timeout=REQUEST_TIMEOUT); response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser'); total_paginas_disponibles = self._extraer_numero_paginas(soup)
            total_paginas = min(total_paginas_disponibles, self.max_paginas_por_busqueda)
            print(f"   📊 Págs disp: {total_paginas_disponibles} | A procesar: {total_paginas}\n")
        except Exception as e: print(f"   ❌ Error pág inicial '{keyword}': {e}. Asumiendo 1 pág.\n")
        todos_enlaces_info = []
        for num_pagina in range(total_paginas):
            url_pagina = self._construir_url_pagina(url_semilla, num_pagina)
            enlaces_pagina = self._extraer_enlaces_de_pagina(url_pagina, num_pagina, keyword)
            todos_enlaces_info.extend(enlaces_pagina)
            if num_pagina < total_paginas - 1: sleep_jitter()
        print(f"\n   🔗 Total enlaces únicos para '{keyword}': {len(todos_enlaces_info)}")
        nuevas_noticias_keyword = 0
        for i, enlace_info in enumerate(todos_enlaces_info, 1):
            url = enlace_info['url']
            if url not in self.existing_data_by_url:
                noticia_dict = self._extraer_contenido_noticia(url, enlace_info['titulo_busqueda'], keyword)
                if noticia_dict: self.existing_data_by_url[url] = noticia_dict; nuevas_noticias_keyword += 1
                if i < len(todos_enlaces_info): sleep_jitter(0.5, 1.0)
        print(f"\n   ✅ Nuevas noticias añadidas para '{keyword}': {nuevas_noticias_keyword}\n")
        return nuevas_noticias_keyword

    def run(self):
        # (Sin cambios respecto a la versión anterior)
        print("\n" + "🌟"*35); print(" "*10 + "TV PERÚ - MODO ACTUALIZACIÓN"); print("🌟"*35 + "\n")
        self.existing_data_by_url = load_existing_data(self.output_file)
        total_nuevas_agregadas = 0
        for keyword in self.keywords:
            nuevas = self.scrape_keyword(keyword)
            total_nuevas_agregadas += nuevas
            if nuevas > 0:
                 print(f"\n💾 Guardando progreso ({len(self.existing_data_by_url)} noticias)...")
                 save_updated_data(self.output_file, self.existing_data_by_url)
                 print("-" * 70)
            if keyword != self.keywords[-1]:
                print(f"\n⏳ Pausa antes de '{self.keywords[self.keywords.index(keyword) + 1]}'... (5s)")
                time.sleep(5); print("-" * 70)
        print(f"\n{'='*70}"); print(f"✅ SCRAPING TV PERÚ COMPLETADO"); print(f"{'='*70}")
        print(f"Noticias NUEVAS totales añadidas: {total_nuevas_agregadas}")
        save_updated_data(self.output_file, self.existing_data_by_url)

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
def main():
    scraper = TVPeruScraper(keywords=KEYWORDS, output_file=OUTPUT_FILE, max_paginas=MAX_PAGINAS_POR_BUSQUEDA)
    scraper.run()

if __name__ == "__main__":
    main()