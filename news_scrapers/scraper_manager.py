# news_scrapers/scraper_manager.py

import time
import traceback # Para un log de errores más detallado

# --- Importar TODOS los scrapers estatales ---
# Importamos sus funciones 'main' con alias claros
from news_scrapers.larepublica_scraper import main as run_larepublica_scraper
from news_scrapers.elperuano_scraper import main as run_elperuano_scraper
from news_scrapers.canaln_scrapper import main as run_canaln_scraper
from news_scrapers.rpp_scrapper import main as run_rpp_scraper
from news_scrapers.tvperu_scrapper import main as run_tvperu_scraper
# (Se omite peru21_scrapper como solicitaste)

def get_all_news(limit=10): # El 'limit' ya no se usa, pero se mantiene por compatibilidad
    """
    Ejecuta TODOS los scrapers estatales (La República, El Peruano, Canal N, RPP, TV Perú)
    uno por uno, para que actualicen el archivo JSON principal 'noticias_partidos.json'.

    Devuelve una lista vacía, ya que las noticias se gestionan en el JSON.
    """
    OUTPUT_FILE="news_scrapers/noticias_partidos.json" 
    # Lista de todos los scrapers a ejecutar en orden
    scrapers_estatales = [
        ("La República", run_larepublica_scraper),
        ("El Peruano", run_elperuano_scraper),
        ("Canal N", run_canaln_scraper),
        ("RPP", run_rpp_scraper),
        ("TV Perú", run_tvperu_scraper),
    ]
    
    print("\n" + "="*70)
    print("--- INICIANDO ACTUALIZACIÓN GLOBAL DE BASE DE DATOS ---")
    print(f"Se ejecutarán {len(scrapers_estatales)} scrapers en serie...")
    print(f"Todas las noticias se guardarán en '{OUTPUT_FILE}'") # Asegúrate de que OUTPUT_FILE esté definido si usas esto, o usa el path directo
    print("="*70)
    
    start_time_global = time.time()

    for nombre, scraper_func in scrapers_estatales:
        print(f"\n--- 📡 Ejecutando scraper: {nombre} ---")
        
        start_time_scraper = time.time()
        try:
            # Ejecutamos la función 'main' de cada scraper
            scraper_func() 
            end_time_scraper = time.time()
            print(f"--- ✅ Scraper de {nombre} finalizado ---")
            print(f"--- ⏱️  Tiempo de {nombre}: {end_time_scraper - start_time_scraper:.2f} segundos ---")
            
        except Exception as e:
            end_time_scraper = time.time()
            print(f"\n{'!'*70}")
            print(f"⚠️ ERROR FATAL al ejecutar scraper de {nombre}: {e}")
            print(f"⏱️  Tiempo de {nombre} (fallido): {end_time_scraper - start_time_scraper:.2f} segundos.")
            print("Mostrando detalles del error:")
            traceback.print_exc() # Imprimir el traceback completo para debug
            print(f"{'!'*70}\n")
            # Continuar con el siguiente scraper
        
        # Pausa breve entre scrapers para evitar sobrecargas (opcional)
        # time.sleep(1) 

    end_time_global = time.time()
    print("\n" + "="*70)
    print("--- ACTUALIZACIÓN DE BASE DE DATOS COMPLETADA ---")
    print(f"⏱️  Tiempo total de ejecución: {end_time_global - start_time_global:.2f} segundos.")
    print(f"ℹ️  El archivo 'noticias_partidos.json' ha sido actualizado por todos los scrapers.")
    print("="*70)
    
    # Devolver lista vacía como se espera en el resto del proyecto (app.py)
    return []


if __name__ == "__main__":
    """
    Permite ejecutar el manager directamente para probar:
    python -m news_scrapers.scraper_manager
    """
    print("Ejecutando el manejador de scrapers (actualizando JSON principal)...\n")
    
    get_all_news() 
    
    print("\n--- Resumen de Ejecución (manager) ---")
    print("✅ Todos los scrapers han sido ejecutados.")
    print("ℹ️  Revisa el log de arriba para ver el resultado de cada uno.")