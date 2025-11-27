# ai_engine/model_loader.py
import os
import json

# Ruta a tu base de datos de noticias
DATABASE_PATH = "news_scrapers/noticias_partidos.json"

def load_news_database():
    """
    Carga la base de datos de noticias desde el archivo JSON.
    Retorna una lista de diccionarios (las noticias).
    """
    if not os.path.exists(DATABASE_PATH):
        print(f"🚨 Advertencia: No se encontró {DATABASE_PATH}")
        return []
    
    try:
        with open(DATABASE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Manejo de estructura: Si es diccionario con claves ID, convertimos a lista de valores
        if isinstance(data, dict):
            return list(data.values())
        elif isinstance(data, list):
            return data
        else:
            return []
            
    except json.JSONDecodeError:
        print(f"🚨 Error: El archivo JSON {DATABASE_PATH} está corrupto.")
        return []
    except Exception as e:
        print(f"🚨 Error desconocido cargando noticias: {e}")
        return []