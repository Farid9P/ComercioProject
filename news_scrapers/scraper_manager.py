import time
import traceback
import sys
import os

# --- Importar scrapers estatales ---
# Usamos un bloque try/except robusto para identificar cuál falla al importar
try:
    # Scrapers de texto plano / requests
    from news_scrapers.larepublica_scraper import main as run_larepublica_scraper
    from news_scrapers.elperuano_scraper import main as run_elperuano_scraper
    
    # Scrapers nuevos (Requests + BeautifulSoup)
    from news_scrapers.tvperu_scrapper import main as run_tvperu_scraper
    
    # Scrapers pesados (Selenium)
    from news_scrapers.canaln_scrapper import main as run_canaln_scraper
    from news_scrapers.rpp_scrapper import main as run_rpp_scraper

except ImportError as e:
    print(f"⚠️ ALERTA DE IMPORTACIÓN: {e}")
    print("Asegúrate de que los archivos .py existan en la carpeta 'news_scrapers' y tengan los nombres correctos.")
    
    # Definimos funciones dummy para que el script no se rompa si falta alguno
    def dummy_func(path=None): print("❌ Scraper no disponible.")
    if 'run_larepublica_scraper' not in locals(): run_larepublica_scraper = dummy_func
    if 'run_elperuano_scraper' not in locals(): run_elperuano_scraper = dummy_func
    if 'run_tvperu_scraper' not in locals(): run_tvperu_scraper = dummy_func
    if 'run_canaln_scraper' not in locals(): run_canaln_scraper = dummy_func
    if 'run_rpp_scraper' not in locals(): run_rpp_scraper = dummy_func

def get_all_news():
    """
    Orquestador principal: Ejecuta todos los scrapers configurados.
    Los scrapers ya tienen el filtro de fecha (2025) interno.
    """
    start_time_global = time.time()
    OUTPUT_FILE = "news_scrapers/noticias_partidos.json"

    # --- LISTA MAESTRA DE SCRAPERS ---
    # Formato: ("Nombre Legible", función_a_ejecutar, ruta_archivo)
    scrapers_estatales = [
        ("La República", run_larepublica_scraper, OUTPUT_FILE),
        ("El Peruano", run_elperuano_scraper, OUTPUT_FILE),
        ("TV Perú", run_tvperu_scraper, OUTPUT_FILE),
        ("Canal N", run_canaln_scraper, OUTPUT_FILE),
        ("RPP Noticias", run_rpp_scraper, OUTPUT_FILE),
    ]

    print(f"\n🚀 INICIANDO ACTUALIZACIÓN MASIVA DE NOTICIAS")
    print(f"📅 Filtro interno: Solo noticias de 2025 en adelante.")
    print(f"📂 Archivo objetivo: {OUTPUT_FILE}\n")

    conteo_exitos = 0

    for item in scrapers_estatales:
        nombre = item[0]
        scraper_func = item[1]
        ruta_archivo = item[2]

        print(f"{'-'*40}")
        print(f"⚡ Ejecutando: {nombre}...")
        start_time_scraper = time.time()

        try:
            # Ejecutamos pasando la ruta del JSON
            scraper_func(ruta_archivo)
            
            duration = time.time() - start_time_scraper
            print(f"✅ {nombre} finalizado correctamente en {duration:.2f}s")
            conteo_exitos += 1

        except Exception as e:
            print(f"❌ ERROR FATAL en {nombre}")
            print(f"   Detalle: {str(e)}")
            traceback.print_exc()
        
        # Pequeña pausa para no saturar la CPU/Red entre scrapers pesados
        time.sleep(2)

    end_time_global = time.time()
    total_time = end_time_global - start_time_global
    
    print("\n" + "="*60)
    print(f"🏁 PROCESO COMPLETADO")
    print(f"📊 Scrapers exitosos: {conteo_exitos} / {len(scrapers_estatales)}")
    print(f"⏱️  Tiempo total: {total_time:.2f} segundos")
    print("="*60)
    
    return []

if __name__ == "__main__":
    get_all_news()