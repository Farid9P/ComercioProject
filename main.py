# main.py
import os
import sys
from ai_engine.context_manager import ContextManager
from web_app.app import app, init_app

# Configuración inicial
context_manager = ContextManager("usuario_demo")

if __name__ == "__main__":
    print("🌐 Iniciando 'Dime la Verdad' (Modo GPT Puro)...")
    
    # Inicializar la app con el contexto
    init_app(context_manager)

    # Iniciar servidor
    app.run(debug=True, port=5000)