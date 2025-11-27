import os
import requests
import json
import re
from dotenv import load_dotenv
from ai_engine.model_loader import load_news_database
from ai_engine.ai_utils import limpiar_texto

# Cargar entorno
load_dotenv()
API_KEY = os.getenv("MI_API_KEY")
API_URL_CHAT = os.getenv("API_URL_CHAT")

# --- STOPWORDS ---
STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "a", "ante", "bajo", "cabe", "con", "contra",
    "de", "desde", "en", "entre", "hacia", "hasta", "para",
    "por", "segun", "sin", "so", "sobre", "tras",
    "y", "o", "u", "e", "ni", "que", "cual", "quien",
    "me", "te", "se", "nos", "os", "mi", "tu", "su",
    "es", "son", "fue", "fueron", "era", "eran", "haber", "hay",
    "mas", "menos", "pero", "aunque", "sino", "noticia", "peru", "foto"
}

# --- MAPA DE DOMINIOS ---
DOMINIOS_BASE = {
    "el peruano": "https://elperuano.pe",
    "la república": "https://larepublica.pe",
    "larepublica": "https://larepublica.pe",
    "rpp": "https://rpp.pe",
    "rpp noticias": "https://rpp.pe",
    "gestión": "https://gestion.pe",
    "canal n": "https://canaln.pe",
    "américa tv": "https://americatv.com.pe",
    "panamericana": "https://panamericana.pe",
    "exitosa": "https://exitosanoticias.pe",
    "peru21": "https://peru21.pe",
    "trome": "https://trome.com",
    "correo": "https://diariocorreo.pe",
    "tv perú": "https://www.tvperu.gob.pe",
    "tvperu": "https://www.tvperu.gob.pe"
}

def sanear_y_obtener_link(noticia):
    titulo = noticia.get('title') or ''
    slug = str(noticia.get('slug') or '').strip()
    url_existente = str(noticia.get('url') or '').strip()
    
    fuente = "Desconocida"
    if 'metadata' in noticia and isinstance(noticia['metadata'], list):
        for meta in noticia['metadata']:
            key = str(meta.get('key', '')).lower()
            if key in ['source', 'fuente', 'medio', 'diario']:
                fuente = meta.get('value', 'Desconocida')
                break
    
    base_url = ""
    fuente_lower = fuente.lower()
    for key, domain in DOMINIOS_BASE.items():
        if key in fuente_lower:
            base_url = domain
            break
            
    if not base_url:
        if 'elperuano' in slug: base_url = "https://elperuano.pe"
        elif 'larepublica' in slug: base_url = "https://larepublica.pe"
        elif 'rpp' in slug: base_url = "https://rpp.pe"
        elif 'canaln' in slug: base_url = "https://canaln.pe"
        elif 'tvperu' in slug: base_url = "https://www.tvperu.gob.pe"

    url_final = "#"
    if url_existente.startswith('http'): url_final = url_existente
    elif slug.startswith('http'): url_final = slug
    elif base_url and slug:
        clean_slug = slug
        if clean_slug.startswith(base_url): url_final = clean_slug
        else:
            if not clean_slug.startswith('/'): clean_slug = '/' + clean_slug
            url_final = f"{base_url}{clean_slug}"
    else:
        if base_url: url_final = base_url
        else: url_final = f"https://www.google.com/search?q={titulo}"

    return fuente, url_final, titulo

def filtrar_palabras_clave(texto):
    texto_limpio = limpiar_texto(texto)
    words = set(texto_limpio.split())
    palabras_utiles = {w for w in words if w not in STOPWORDS and len(w) > 2}
    return palabras_utiles

# --- NUEVA FUNCIÓN DE LIMPIEZA VISUAL ---
def limpiar_formato_respuesta(texto):
    """Convierte Markdown a HTML y limpia asteriscos"""
    if not texto: return ""
    
    # 1. Convertir **texto** en <b>texto</b>
    texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
    
    # 2. Convertir *texto* en <i>texto</i>
    texto = re.sub(r'\*(.*?)\*', r'<i>\1</i>', texto)
    
    # 3. Convertir saltos de línea en <br>
    texto = texto.replace('\n', '<br>')
    
    return texto

def generar_respuesta(consulta_usuario: str, **kwargs):
    if not API_KEY or not API_URL_CHAT:
        return {'veredicto_texto': 'ERROR CONFIG', 'veredicto_color_class': 'alert-dark', 'mensaje_explicativo': 'Falta API Key', 'evidencias': []}

    palabras_query = filtrar_palabras_clave(consulta_usuario)
    if len(palabras_query) < 2:
        palabras_query.add(limpiar_texto(consulta_usuario))

    todas_noticias = load_news_database()
    noticias_candidatas = []

    for noticia in todas_noticias:
        if not isinstance(noticia, dict): continue
        fuente_real, url_real, titulo_real = sanear_y_obtener_link(noticia)
        teaser = noticia.get('data', {}).get('teaser') or ''
        texto_analisis = limpiar_texto(f"{titulo_real} {teaser}")
        palabras_noticia = set(texto_analisis.split())

        score = 0
        for palabra in palabras_query:
            if palabra in palabras_noticia:
                score += 1
                if palabra in limpiar_texto(titulo_real): score += 2 

        MIN_SCORE = 3 if len(palabras_query) > 2 else 2
        if score >= MIN_SCORE:
            noticias_candidatas.append({
                'titulo': titulo_real,
                'fuente': fuente_real,
                'resumen': teaser,
                'url': url_real,
                'score': score
            })

    noticias_candidatas.sort(key=lambda x: x['score'], reverse=True)
    contexto_final = noticias_candidatas[:5]

    if not contexto_final:
        prompt_contexto = "AVISO: No encontré noticias similares en mi base de datos."
    else:
        prompt_contexto = "HE ENCONTRADO ESTAS NOTICIAS (ÚSALAS COMO VERDAD ABSOLUTA):\n"
        for i, n in enumerate(contexto_final):
            prompt_contexto += f"[{i+1}] Fuente: {n['fuente']} | Titular: {n['titulo']}\nResumen: {n['resumen']}\n\n"

    prompt_sistema = (
        "Eres 'Dime la Verdad', un asistente de IA amable pero RIGUROSO.\n"
        "REGLA DE ORO: Verifica NÚMEROS, FECHAS y NOMBRES.\n"
        "- Si el usuario dice '5' y la noticia dice '4' -> ES [FALSO].\n"
        "- Si el usuario dice 'Aprobado' y la noticia 'Rechazado' -> ES [FALSO].\n\n"
        "ESTRUCTURA DE RESPUESTA:\n"
        "1. Inicia OBLIGATORIAMENTE con: [VERDADERO], [FALSO], [IMPRECISO] o [SIN DATOS].\n"
        "2. Luego, explica con tono amable y periodístico.\n"
        "3. Usa **negritas** para resaltar correcciones."
    )

    mensaje_usuario = (
        f"{prompt_contexto}\n\n"
        f"PREGUNTA DEL USUARIO: '{consulta_usuario}'\n\n"
        "Analiza la exactitud y dame tu veredicto:"
    )

    payload = {
        "model": "gpt-4", 
        "messages": [{"role": "system", "content": prompt_sistema}, {"role": "user", "content": mensaje_usuario}],
        "temperature": 0.2, 
        "max_tokens": 100
    }

    try:
        response = requests.post(API_URL_CHAT, headers={"Authorization": f"Bearer {API_KEY}"}, json=payload, timeout=25)
        if response.status_code != 200:
             return {'veredicto_texto': 'ERROR API', 'veredicto_color_class': 'alert-warning', 'mensaje_explicativo': 'La IA está ocupada.', 'evidencias': []}
             
        contenido = response.json()['choices'][0]['message']['content']
        
        color = "alert-warning"
        titulo = "ANÁLISIS COMPLEJO ⚠️"
        
        if "[FALSO]" in contenido:
            color = "alert-danger"
            titulo = "FALSO / INCORRECTO ❌"
            contenido = contenido.replace("[FALSO]", "").strip()
        elif "[VERDADERO]" in contenido:
            color = "alert-success"
            titulo = "VERDADERO ✅"
            contenido = contenido.replace("[VERDADERO]", "").strip()
        elif "[IMPRECISO]" in contenido:
            color = "alert-warning"
            titulo = "IMPRECISO / ENGAÑOSO ⚠️"
            contenido = contenido.replace("[IMPRECISO]", "").strip()
        elif "[SIN DATOS]" in contenido:
            color = "alert-secondary"
            titulo = "SIN DATOS EN BD 🤷"
            contenido = contenido.replace("[SIN DATOS]", "").strip()
            contexto_final = [] 

        # --- APLICAMOS LA LIMPIEZA VISUAL AQUÍ ---
        contenido_html = limpiar_formato_respuesta(contenido)

        return {
            'veredicto_texto': titulo,
            'veredicto_color_class': color,
            'mensaje_explicativo': contenido_html, # Enviamos HTML limpio
            'debug_contexto': contexto_final
        }

    except Exception as e:
        print(f"Error IA: {e}")
        return {'veredicto_texto': 'ERROR TÉCNICO', 'veredicto_color_class': 'alert-dark', 'mensaje_explicativo': 'Error interno.', 'evidencias': []}