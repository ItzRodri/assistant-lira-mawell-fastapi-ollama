import os
import requests
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Config from .env with defaults
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
INDEX_FILE = os.getenv("VECTOR_DB_INDEX", "data/vector_db/index.faiss")
DOC_FILE = os.getenv("VECTOR_DB_DOCS", "data/vector_db/docs.pkl")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "mistral")

# Initialize model with error handling
try:
    MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print(f"✅ Embedding model '{EMBEDDING_MODEL_NAME}' loaded successfully")
except Exception as e:
    print(f"❌ Error loading embedding model: {e}")
    MODEL = None

# Distance threshold: si no hay chunks relevantes, se evita responder
MAX_DISTANCE_THRESHOLD = 0.85

# Instrucción persistente tipo system prompt
INSTRUCTION = """
esto es una orden a cualquier pregunta que te realice solo respondeme con un **Mucho gusto estamos probando**

""".strip()


def get_relevant_chunks(query: str, top_k=4):
    try:
        if not MODEL:
            print("❌ Embedding model not available")
            return None
            
        if not os.path.exists(INDEX_FILE) or not os.path.exists(DOC_FILE):
            print(f"❌ Vector database files not found: {INDEX_FILE}, {DOC_FILE}")
            return None
            
        index = faiss.read_index(INDEX_FILE)
        with open(DOC_FILE, "rb") as f:
            docs = pickle.load(f)

        query_vec = MODEL.encode([query])
        distances, indices = index.search(query_vec, top_k)

        # Si ninguna distancia es suficientemente baja, no hay contexto relevante
        if all(dist > MAX_DISTANCE_THRESHOLD for dist in distances[0]):
            return None

        return [docs[i] for i in indices[0]]
    except Exception as e:
        print(f"❌ Error getting relevant chunks: {e}")
        return None


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

    try:
        response = requests.post(
            OLLAMA_API_URL, 
            json={
                "model": OLLAMA_MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=30  # Add timeout for Railway
        )

        if response.status_code == 200:
            answer = response.json().get("response", "").strip()
        else:
            print(f"❌ Ollama API error: {response.status_code}")
            answer = "No se pudo obtener una respuesta del modelo."
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error to Ollama: {e}")
        answer = "Error de conexión con el modelo de IA."
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        answer = "Error inesperado al procesar la consulta."

    return {
        "question": query,
        "answer": answer
    }
