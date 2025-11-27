from flask import Flask, render_template, request, jsonify
from flask_caching import Cache
import os
import sys

# Configuración de rutas
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ai_engine.text_generation import generar_respuesta
from ai_engine.context_manager import ContextManager

app = Flask(__name__, template_folder="templates", static_folder="static")
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})
context_manager = None

def init_app(ctx_manager: ContextManager):
    global context_manager
    context_manager = ctx_manager

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    # 1. Recibir datos JSON desde JavaScript
    data = request.get_json()
    afirmacion = data.get("afirmacion", "")
    
    if not afirmacion.strip():
        return jsonify({'error': 'El texto no puede estar vacío.'}), 400

    if context_manager:
        context_manager.add_message(f"Usuario pregunta: {afirmacion}")

    try:
        # 2. Consultar a la IA
        resultado = generar_respuesta(afirmacion)
        
        # 3. Preparar respuesta JSON
        # (Fusionamos evidencias y resultado en un solo objeto para facilitar el JS)
        respuesta_json = {
            'veredicto_texto': resultado.get('veredicto_texto'),
            'veredicto_color_class': resultado.get('veredicto_color_class'),
            'mensaje_explicativo': resultado.get('mensaje_explicativo'),
            'evidencias': resultado.get('debug_contexto', [])
        }
        return jsonify(respuesta_json)

    except Exception as e:
        print(f"🚨 Error en /analyze: {e}")
        return jsonify({
            'veredicto_texto': 'ERROR TÉCNICO',
            'veredicto_color_class': 'alert-dark',
            'mensaje_explicativo': f'Ocurrió un error interno: {str(e)}',
            'evidencias': []
        })

@app.route("/limpiar_contexto")
def limpiar_contexto():
    if context_manager:
        context_manager.clear_context()
    return jsonify({'status': 'ok', 'msg': 'Memoria borrada'})