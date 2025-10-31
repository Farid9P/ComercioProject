"""
main.py — Punto de entrada principal de 'Dime la Verdad'
Inicia el servidor web Flask y conecta los módulos de IA.
"""

import os
import sys
from ai_engine.context_manager import ContextManager

# --- Modificación para importar desde carpetas hermanas ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- Fin de la modificación ---

# 🔹 Importamos la aplicación web (Flask)
from web_app.app import app, init_app

# --- ¡NUEVAS IMPORTACIONES! ---
from ai_engine.model_loader import load_vectorizer
# --- FIN DE IMPORTACIONES ---


# ==============================
# 🧠 Configuración inicial
# ==============================
print("🧠 Inicializando ContextManager global...")
context_manager = ContextManager("gonzalo")

# ==============================
# 🚀 Ejecución principal
# ==============================
if __name__ == "__main__":
    print("🌐 Iniciando interfaz web de 'Dime la Verdad'...\n")

    # Asegurar carpeta de modelos
    if not os.path.exists("models"):
        os.makedirs("models")

    # --- ¡MODIFICACIÓN! "Pre-calentar" el modelo de IA ---
    # Esto creará 'vectorizer_es.joblib' si no existe.
    print("🧠 Pre-cargando y/o entrenando modelo de IA...")
    try:
        load_vectorizer()
        print("✅ Modelo de IA listo.")
    except Exception as e:
        print(f"🚨 ERROR FATAL: No se pudo entrenar el modelo de IA.")
        print(f"Asegúrate de que 'news_scrapers/noticias_partidos.json' exista y no esté vacío.")
        print(f"Error: {e}")
        sys.exit(1) # Detener el programa si la IA no puede entrenar
    # --- FIN DE MODIFICACIÓN ---

    print(f"✅ Contexto '{context_manager.username}' cargado.")

    # Inyectamos el contexto en la app web
    init_app(context_manager)

    # Obtenemos el puerto y ejecutamos
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 Servidor 'Dime la Verdad' en marcha — http://127.0.0.1:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)