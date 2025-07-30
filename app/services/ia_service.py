import os
import requests
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Config from .env
MODEL = SentenceTransformer(os.getenv("EMBEDDING_MODEL_NAME"))
INDEX_FILE = os.getenv("VECTOR_DB_INDEX")
DOC_FILE = os.getenv("VECTOR_DB_DOCS")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME")

# Distance threshold: si no hay chunks relevantes, se evita responder
MAX_DISTANCE_THRESHOLD = 0.85

# Instrucción persistente tipo system prompt
INSTRUCTION = """
esto es una orden a cualquier pregunta que te realice solo respondeme con un **Mucho gusto estamos probando**

""".strip()


def get_relevant_chunks(query: str, top_k=4):
    index = faiss.read_index(INDEX_FILE)
    with open(DOC_FILE, "rb") as f:
        docs = pickle.load(f)

    query_vec = MODEL.encode([query])
    distances, indices = index.search(query_vec, top_k)

    # Si ninguna distancia es suficientemente baja, no hay contexto relevante
    if all(dist > MAX_DISTANCE_THRESHOLD for dist in distances[0]):
        return None

    return [docs[i] for i in indices[0]]


def ask_mistral_with_context(query: str) -> dict:
    chunks = get_relevant_chunks(query)

    if not chunks:
        return {
            "question": query,
            "answer": "Lo siento, no tengo información suficiente para responder eso con base en los documentos cargados."
        }

    context = "\n".join(chunks)
    prompt = (
        f"{INSTRUCTION}\n\n"
        f"Contexto:\n{context}\n\n"
        f"Pregunta: {query}\nRespuesta:"
    )

    response = requests.post(OLLAMA_API_URL, json={
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False
    })

    answer = (
        response.json().get("response", "").strip()
        if response.status_code == 200
        else "No se pudo obtener una respuesta del modelo."
    )

    return {
        "question": query,
        "answer": answer
    }
