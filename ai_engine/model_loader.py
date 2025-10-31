# ai_engine/model_loader.py
import os
import joblib
import json
from sklearn.feature_extraction.text import TfidfVectorizer

# ¡Importante! Necesitamos la misma función de limpieza para entrenar
# que la que usamos para las consultas.
from ai_engine.ai_utils import limpiar_texto 

MODEL_PATH = "models/vectorizer_es.joblib"
# --- ¡CAMBIO! Apuntar al archivo JSON principal y correcto ---
DATABASE_PATH = "news_scrapers/noticias_partidos.json"


def _load_json_database(archivo=DATABASE_PATH):
    """
    Carga la base de datos de noticias desde el archivo JSON principal.
    """
    if not os.path.exists(archivo):
        print(f"Advertencia: No se encontró {archivo} para entrenar el vectorizador.")
        return []
    
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Asegurarse de que los datos sean una lista de artículos (los valores del dict)
        if isinstance(data, dict):
            return list(data.values())
        elif isinstance(data, list):
            # Si por alguna razón se guardó como lista, usarla directamente
            return data
        else:
            print(f"Error: {archivo} tiene un formato desconocido.")
            return []
            
    except json.JSONDecodeError:
        print(f"Error: El archivo {archivo} está corrupto o vacío.")
        return []
    except Exception as e:
        print(f"Error cargando {archivo}: {e}")
        return []

def _crear_corpus_entrenamiento():
    """
    Lee todas las noticias de la base de datos JSON y las convierte en
    un gran corpus de texto para entrenar el modelo TF-IDF.
    """
    print("⚙️  Creando corpus de entrenamiento desde la base de datos JSON...")
    noticias_db = _load_json_database()

    if not noticias_db:
        print("⚠️  El JSON está vacío. El vectorizador no puede ser entrenado.")
        # Devolver lista vacía. load_vectorizer manejará esto.
        return []

    corpus_base = []
    
    for n in noticias_db:
        if not isinstance(n, dict):
            continue # Omitir items que no sean diccionarios
            
        # --- ¡INICIO DE LA CORRECCIÓN! ---
        # Forzar que 'titulo', 'teaser' y 'contenido_full' sean strings, no None.
        
        titulo = n.get('title') or '' 
        
        data = n.get('data', {})
        if data is None: # Comprobar si 'data' es null
            data = {}
            
        teaser = data.get('teaser') or ''
        
        # Incluir el contenido completo de los otros scrapers (RPP, TV Peru, etc.)
        contenido_full = n.get('contenido_full', '') or ''
        
        # Combinar todo el texto disponible
        texto_a_limpiar = titulo + " " + teaser + " " + contenido_full
        # --- FIN DE LA CORRECCIÓN! ---

        if texto_a_limpiar.strip():
            corpus_base.append(limpiar_texto(texto_a_limpiar))
            
    print(f"✅ Corpus creado con {len(corpus_base)} artículos.")
    return corpus_base

def load_vectorizer():
    """
    Carga (o crea si no existe) un vectorizador TF-IDF entrenado con
    TODAS las noticias de la base de datos JSON.
    """
    os.makedirs("models", exist_ok=True)

    if os.path.exists(MODEL_PATH):
        try:
            vectorizer = joblib.load(MODEL_PATH)
            print("✅ Vectorizer cargado correctamente desde models/vectorizer_es.joblib")
            return vectorizer
        except Exception as e:
            print(f"Error cargando vectorizer: {e}")
            print("⚙️  Se creará uno nuevo desde cero.")

    # --- Creación del Nuevo Vectorizador ---
    
    # 1. Crear el corpus desde el JSON
    corpus_base = _crear_corpus_entrenamiento()
    
    # Si el corpus está vacío, no podemos entrenar.
    if not corpus_base:
        print("🚨 ERROR CRÍTICO: No hay datos en el corpus para entrenar el vectorizador.")
        # Lanzar una excepción que main.py pueda capturar
        raise ValueError("Corpus de entrenamiento vacío. Ejecuta los scrapers primero.")

    # 2. Vectorizador en español
    vectorizer = TfidfVectorizer(
        lowercase=True,     # Ya está en minúsculas por 'limpiar_texto'
        analyzer="word",
        stop_words=None,    # Podríamos añadir 'stop_words' en español en el futuro
        max_features=5000   # Limitar vocabulario
    )

    try:
        # 3. Entrenar el vectorizador
        print("🧠  Entrenando nuevo vectorizer TF-IDF... (Esto puede tardar un momento)")
        vectorizer.fit(corpus_base)
        
        # 4. Guardar el modelo entrenado
        joblib.dump(vectorizer, MODEL_PATH)
        print("✅ Nuevo vectorizer TF-IDF inteligente creado y guardado.")
    except Exception as e:
        print(f"Error fatal al entrenar el vectorizer: {e}")
        return None

    return vectorizer

if __name__ == "__main__":
    print("Demo model_loader — creando/asegurando vectorizer TF-IDF...")
    vectorizer = load_vectorizer()
    if vectorizer and hasattr(vectorizer, "get_feature_names_out"):
        print("Vectorizer listo ✅")
        vocab = vectorizer.get_feature_names_out()
        print("Ejemplo de palabras del vocabulario:", list(vocab)[100:110])
    else:
        print("No se pudo cargar o entrenar el vectorizador.")