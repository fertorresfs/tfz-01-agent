import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("--- LISTA OFICIAL DE MODELOS DISPONÍVEIS ---")
try:
    # Vamos listar tudo sem filtrar para garantir que veremos o que existe
    for model in client.models.list():
        # Imprime apenas o nome, que é o ID que precisamos copiar
        print(f"ID: {model.name}")
        
except Exception as e:
    print(f"Erro ao listar: {e}")