import re
import unicodedata
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def limpiar_texto(texto: str) -> str:
    """
    Limpia el texto de caracteres especiales, tildes y espacios innecesarios.
    Ideal para análisis semántico y TF-IDF.
    """
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8', 'ignore')
    texto = texto.lower()
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def similitud_coseno(v1, v2):
    """
    Calcula la similitud del coseno entre dos vectores TF-IDF.
    """
    # Si alguno de los vectores está vacío (suma de elementos es 0), la similitud es 0
    if v1.sum() == 0 or v2.sum() == 0:
        return 0.0

    sim = cosine_similarity(v1, v2)
    
    if np.isnan(sim[0][0]):
        return 0.0
        
    return float(sim[0][0]) if sim.size > 0 else 0.0


def formatear_respuesta(texto_usuario, best_match_article, similitud):
    """
    Genera un diccionario estructurado con el resultado del análisis.
    """
    
    resultado = {}
    EVIDENCE_THRESHOLD = 0.4 # 40% (Umbral para mostrar evidencia)

    # --- 1. Definir Veredicto y Color (para Bootstrap) ---
    if similitud > 0.5: # Más del 50% es VERDADERO
        resultado['veredicto_texto'] = "PARECE SER VERDADERA ✅"
        resultado['veredicto_color_class'] = "alert-success" # Verde
    elif similitud >= EVIDENCE_THRESHOLD: # Entre 40% y 50% es DUDOSO
        resultado['veredicto_texto'] = "ES DUDOSA ⚠️"
        resultado['veredicto_color_class'] = "alert-warning" # Amarillo
    else: # Menos de 40% es FALSO
        resultado['veredicto_texto'] = "PODRÍA SER FALSA O SACADA DE CONTEXTO ❌"
        resultado['veredicto_color_class'] = "alert-danger" # Rojo

    # --- 2. Similitud ---
    resultado['similitud_porcentaje'] = similitud * 100
    resultado['similitud_texto'] = f"{similitud*100:.2f}%"

    # --- 3. Mensaje Explicativo (¡CORREGIDO!) ---
    if best_match_article and similitud >= EVIDENCE_THRESHOLD:
        
        fuente = best_match_article.get('fuente', 'Fuente Desconocida')
        titulo = best_match_article.get('title', best_match_article.get('titulo', 'Sin Título'))
        url = best_match_article.get('url', '#') # Usar '#' como fallback

        # --- ¡CAMBIO! Generar HTML en lugar de Markdown/texto plano ---
        respuesta_evidencia = (
            f"<strong>Evidencia encontrada ({fuente}):</strong><br>"
            f"📰 <strong>Titular:</strong> {titulo}<br>"
            f"🔗 <strong>Enlace:</strong> <a href='{url}' target='_blank'>{url}</a>"
        )
        # --- FIN DEL CAMBIO ---
        
        resultado['mensaje_explicativo'] = respuesta_evidencia
    else:
         # Limpiar el texto de 'else'
         resultado['mensaje_explicativo'] = "No he encontrado ninguna noticia en nuestra base de datos que coincida lo suficiente como para ser considerada una evidencia relevante."

    return resultado