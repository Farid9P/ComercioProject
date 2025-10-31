"""
context_manager.py — Manejo de contexto conversacional multiusuario
Permite guardar y recuperar el historial de mensajes de cada usuario.
"""

import json
from datetime import datetime
from pathlib import Path

CONTEXT_DIR = Path("data/contexts")
CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


class ContextManager:
    def __init__(self, username: str):
        self.username = username
        self.context_path = CONTEXT_DIR / f"{username}_context.json"
        self.context = self._load_context()

    # -----------------------------
    # Cargar contexto existente
    # -----------------------------
    def _load_context(self):
        if self.context_path.exists():
            try:
                with open(self.context_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ Error al cargar contexto para '{self.username}', iniciando vacío.")
        print(f"🧩 No se encontró contexto previo para '{self.username}'. Iniciando limpio.")
        return {"messages": []}

    # -----------------------------
    # Guardar mensaje en contexto
    # -----------------------------
    def add_message(self, mensaje: str, role: str = "user"):
        entry = {
            "role": role,
            "content": mensaje,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.context["messages"].append(entry)
        self._save_context()

    # -----------------------------
    # Guardar archivo JSON
    # -----------------------------
    def _save_context(self):
        with open(self.context_path, "w", encoding="utf-8") as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)

    # -----------------------------
    # Mostrar contexto actual
    # -----------------------------
    def show_context(self):
        print(f"\n🧠 Contexto actual para usuario '{self.username}':")
        for m in self.context["messages"]:
            print(f"[{m['role'].upper()} @ {m['timestamp']}]: {m['content']}")
        print(f"\n🗂️ Total mensajes en memoria: {len(self.context['messages'])}")

    # -----------------------------
    # Limpiar contexto del usuario
    # -----------------------------
    def clear_context(self):
        self.context = {"messages": []}
        if self.context_path.exists():
            self.context_path.unlink()
        print(f"🗑️ Contexto limpiado para usuario '{self.username}'.")
