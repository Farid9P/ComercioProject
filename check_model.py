import joblib
import os

MODEL_PATH = "models/vectorizer_es.joblib"

if not os.path.exists(MODEL_PATH):
    print(f"❌ ERROR: No se encontró el archivo del modelo en {MODEL_PATH}")
    print("Asegúrate de ejecutar 'python main.py' primero para crearlo.")
else:
    print(f"✅ Modelo encontrado. Cargando {MODEL_PATH}...")
    try:
        vectorizer = joblib.load(MODEL_PATH)
        vocab = vectorizer.get_feature_names_out()

        print("\n--- VOCABULARIO DEL MODELO ACTUAL ---")
        print(f"Total de palabras conocidas: {len(vocab)}")

        print("\n--- Muestra del vocabulario ---")
        if len(vocab) < 100:
            print("¡Este es el modelo 'tonto' de emergencia!")
            print(list(vocab))
        else:
            print("¡Este es el modelo 'inteligente'!")
            # Imprime 20 palabras aleatorias del vocabulario
            import random
            sample = random.sample(list(vocab), 20)
            print(sample)

    except Exception as e:
        print(f"Error al cargar el modelo: {e}")