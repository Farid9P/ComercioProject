from flask import Flask, render_template, request, redirect, url_for
from flask_caching import Cache
import os
import sys
import json

# --- Modificación para importar desde carpetas hermanas ---
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- Fin de la modificación ---

from ai_engine.text_generation import generar_respuesta
from ai_engine.context_manager import ContextManager
# Ya no importamos 'get_all_news' directamente aquí

# --- Configuración del servidor Flask ---
app = Flask(__name__, template_folder="templates", static_folder="static")
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
context_manager = None
DATABASE_PATH = "news_scrapers/noticias_partidos.json" # Un solo lugar para la ruta

def init_app(ctx_manager: ContextManager):
    global context_manager
    context_manager = ctx_manager

# --- LÓGICA DE CACHÉ DE LA BASE DE DATOS ---

def _load_json_database(archivo=DATABASE_PATH):
    """ Carga la base de datos JSON principal (ahora es 'dict'). """
    if not os.path.exists(archivo):
        print(f"Advertencia: No se encontró el archivo de base de datos {archivo}")
        return [] # Devolver lista vacía
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
        
        # Asegurarse de que los datos sean una lista de artículos (los valores del dict)
        if isinstance(data_dict, dict):
            return list(data_dict.values())
        elif isinstance(data_dict, list):
             # Si por alguna razón se guardó como lista, usarla
            return data_dict
        else:
            print(f"Error: {archivo} tiene un formato desconocido.")
            return []
            
    except json.JSONDecodeError:
        print(f"Error: El archivo {archivo} está corrupto o vacío.")
        return []
    except Exception as e:
        print(f"Error cargando {archivo}: {e}")
        return []

@cache.cached(timeout=3600, key_prefix='db_news') # Cache por 1 hora
def get_cached_db_news():
    """
    Carga el archivo JSON gigante de todas las fuentes y lo guarda en
    caché por 1 hora.
    """
    print("--- ¡CACHE MISS! Recargando base de datos JSON (Todas las fuentes) ---")
    try:
        noticias_db = _load_json_database()
        return noticias_db if noticias_db is not None else []
    except Exception as e:
        print(f"Error al cargar la base de datos JSON: {e}")
        return []

# --- Rutas principales ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analizar", methods=["POST"])
def analizar_afirmacion():
    afirmacion = request.form.get("texto", "").strip()
    if not afirmacion:
        return render_template("index.html", error="Por favor, ingresa una afirmación para analizar.")
    
    return redirect(url_for("resultado", afirmacion=afirmacion))

@app.route("/resultado")
def resultado():
    afirmacion = request.args.get("afirmacion", "")
    if not afirmacion:
        return redirect(url_for("index"))

    if not context_manager:
        return "Error: El ContextManager no se ha inicializado.", 500
    
    context_manager.add_message(afirmacion, role="user")

    # Ejecutar pipeline de IA
    try:
        # 1. Obtener noticias cacheadas
        db_news = get_cached_db_news()
        
        # 2. Generar respuesta
        # (Asumiendo que text_generation.py devuelve (dict, list))
        resultado_dict, evidencias = generar_respuesta(afirmacion, db_news)
        
        # 3. Guardar en contexto
        context_manager.add_message(resultado_dict.get('veredicto_texto', 'Error'), role="system")

    except Exception as e:
        # Manejo de error si la IA falla
        resultado_dict = {
            'veredicto_texto': 'ERROR EN EL SERVIDOR ❌',
            'veredicto_color_class': 'alert-danger',
            'similitud_porcentaje': 0,
            'similitud_texto': '0.00%',
            'mensaje_explicativo': f'Ocurrió un error grave durante el análisis: {e}'
        }
        evidencias = []
        import traceback
        traceback.print_exc() # Imprimir el error en la terminal

    # --- ¡CORRECCIÓN! ---
    # Pasar el diccionario como 'resultado', no 'respuesta'.
    return render_template("result.html", 
                           afirmacion=afirmacion, 
                           resultado=resultado_dict, # Nombre de variable corregido
                           evidencias=evidencias)
    # --- FIN DE LA CORRECCIÓN ---


@app.route("/recargar_noticias")
def recargar_noticias():
    """
    Esta ruta ahora solo limpia el caché del JSON.
    El scraper_manager debe ejecutarse por separado.
    """
    try:
        cache.delete('db_news')
        mensaje = "✅ Caché de la base de datos JSON limpiado. La próxima consulta recargará el JSON."
    except Exception as e:
        mensaje = f"⚠️ Error al limpiar caché: {str(e)}"
    return render_template("index.html", mensaje=mensaje)


@app.route("/limpiar_contexto")
def limpiar_contexto():
    if not context_manager:
        return "Error: El ContextManager no se ha inicializado.", 500
    context_manager.clear_context()
    return render_template("index.html", mensaje="🧹 Contexto limpiado correctamente.")