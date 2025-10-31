import json
import os
from ai_engine.model_loader import load_vectorizer
from ai_engine.ai_utils import limpiar_texto, similitud_coseno, formatear_respuesta

def generar_respuesta(texto_usuario: str, db_news: list):
    """
    Genera una respuesta comparando la afirmación del usuario contra la base de datos
    de noticias (CACHEADA) de TODAS las fuentes.
    """
    print("🧠 Iniciando motor de IA (MODO JSON COMPLETO)...")

    # --- 1. Cargar herramientas ---
    vectorizer = load_vectorizer()
    if vectorizer is None:
        # Devolver un diccionario de error, no un string
        return {"veredicto_texto": "Error crítico: El motor de IA no pudo iniciarse.", "veredicto_color_class": "alert-danger", "similitud_porcentaje": 0, "similitud_texto": "0%", "mensaje_explicativo": ""}, []

    # --- 2. Cargar y unificar todas las noticias ---
    
    if db_news is None:
        db_news = []
        
    print(f"Recibidas {len(db_news)} noticias de DB (cacheadas).")

    corpus_noticias = []

    # Normalizar noticias de la DB (todas las fuentes)
    for n in db_news:
        if not isinstance(n, dict):
            continue # Omitir items corruptos
            
        # --- ¡INICIO DE LA CORRECCIÓN DE NoneType y FUENTE! ---
        
        # 1. Forzar que 'titulo' y 'teaser' sean strings, no None.
        titulo = n.get('title') or '' 
        
        data = n.get('data', {})
        if data is None: # Comprobar si 'data' es null
            data = {}
        teaser = data.get('teaser') or ''
        
        # 2. Incluir el contenido completo de los otros scrapers (RPP, TV Peru, etc.)
        contenido_full = n.get('contenido_full', '') or ''
        
        # 3. Combinar todo el texto disponible
        texto_a_limpiar = titulo + " " + teaser + " " + contenido_full
        
        # 4. Asignar la fuente correctamente desde los metadatos
        if 'metadata' in n and isinstance(n['metadata'], list):
            for meta in n['metadata']:
                if meta.get('key') == 'source':
                    n['fuente'] = meta.get('value', 'Desconocida')
                    break
        if 'fuente' not in n:
             # Fallback para artículos que no tengan metadata (ej. La República v1)
             if 'larepublica.pe' in n.get('url', ''):
                 n['fuente'] = 'La República'
             elif 'rpp.pe' in n.get('url', ''):
                 n['fuente'] = 'RPP'
             elif 'canaln.pe' in n.get('url', ''):
                 n['fuente'] = 'Canal N'
             elif 'elperuano.pe' in n.get('url', ''):
                 n['fuente'] = 'El Peruano'
             elif 'tvperu.gob.pe' in n.get('url', ''):
                 n['fuente'] = 'TV Perú'
             else:
                 n['fuente'] = 'Desconocida'
        
        # --- FIN DE LA CORRECCIÓN ---

        if texto_a_limpiar.strip():
            # (Lógica específica de URL de La República)
            if n['fuente'] == 'La República' and n.get('slug') and not n.get('url'):
                 n['url'] = f"https://larepublica.pe/{n.get('slug')}"
                 
            corpus_noticias.append({
                'texto_limpio': limpiar_texto(texto_a_limpiar),
                'articulo_original': n
            })

    if not corpus_noticias:
        return {"veredicto_texto": "La base de datos de noticias está vacía. Ejecuta los scrapers.", "veredicto_color_class": "alert-danger", "similitud_porcentaje": 0, "similitud_texto": "0%", "mensaje_explicativo": ""}, []

    print(f"Total de noticias en corpus para análisis: {len(corpus_noticias)}")

    # --- 3. Procesar texto del usuario ---
    texto_usuario_limpio = limpiar_texto(texto_usuario)
    if not texto_usuario_limpio:
        return {"veredicto_texto": "Tu consulta estaba vacía.", "veredicto_color_class": "alert-warning", "similitud_porcentaje": 0, "similitud_texto": "0%", "mensaje_explicativo": ""}, []
        
    try:
        vector_usuario = vectorizer.transform([texto_usuario_limpio])
    except Exception as e:
        return {"veredicto_texto": f"Error al procesar tu solicitud: {e}", "veredicto_color_class": "alert-danger", "similitud_porcentaje": 0, "similitud_texto": "0%", "mensaje_explicativo": ""}, []

    # --- 4. Encontrar la mejor coincidencia (Similitud de Coseno) ---
    mejor_similitud = 0.0
    mejor_articulo = None

    for noticia in corpus_noticias:
        if not noticia['texto_limpio']:
            continue
        
        try:
            vector_noticia = vectorizer.transform([noticia['texto_limpio']])
            sim = similitud_coseno(vector_usuario, vector_noticia)
            
            if sim > mejor_similitud:
                mejor_similitud = sim
                mejor_articulo = noticia['articulo_original']
                
        except Exception as e:
            pass # Ignorar artículos que no se puedan vectorizar

    print(f"Análisis completo. Mejor similitud encontrada: {mejor_similitud:.4f}")

    # --- 5. Formar la respuesta ---
    
    resultado_dict = formatear_respuesta(texto_usuario, mejor_articulo, mejor_similitud)

    EVIDENCE_THRESHOLD = 0.4 # 40%

    evidencias_relevantes = []
    if mejor_articulo and mejor_similitud >= EVIDENCE_THRESHOLD:
        evidencias_relevantes = [mejor_articulo]
    
    return resultado_dict, evidencias_relevantes