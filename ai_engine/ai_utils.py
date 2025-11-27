# ai_engine/ai_utils.py
import re
import unicodedata

def limpiar_texto(texto: str) -> str:
    """
    Limpia el texto de caracteres especiales para facilitar la lectura
    o búsquedas simples.
    """
    if not isinstance(texto, str):
        return ""
    # Normalizar tildes (á -> a)
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8', 'ignore')
    texto = texto.lower()
    # Quitar caracteres no alfanuméricos
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    # Quitar espacios extra
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto