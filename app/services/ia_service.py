import os
import requests
import pickle
from dotenv import load_dotenv

load_dotenv()

# Config from .env with defaults
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
INDEX_FILE = os.getenv("VECTOR_DB_INDEX", "data/vector_db/index.faiss")
DOC_FILE = os.getenv("VECTOR_DB_DOCS", "data/vector_db/docs.pkl")

# Use external Ollama service or fallback
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "mistral")

# Fallback mode when dependencies are not available
FALLBACK_MODE = os.getenv("FALLBACK_MODE", "true").lower() == "true"

# Initialize model with error handling (optional dependency)
MODEL = None
try:
    from sentence_transformers import SentenceTransformer
    MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print(f"✅ Embedding model '{EMBEDDING_MODEL_NAME}' loaded successfully")
except ImportError:
    print("⚠️  sentence-transformers not available. Using fallback mode.")
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
        # Try to use vector search if available
        if MODEL and os.path.exists(INDEX_FILE) and os.path.exists(DOC_FILE):
            try:
                import faiss
                index = faiss.read_index(INDEX_FILE)
                with open(DOC_FILE, "rb") as f:
                    docs = pickle.load(f)

                query_vec = MODEL.encode([query])
                distances, indices = index.search(query_vec, top_k)

                # Si ninguna distancia es suficientemente baja, no hay contexto relevante
                if all(dist > MAX_DISTANCE_THRESHOLD for dist in distances[0]):
                    return None

                return [docs[i] for i in indices[0]]
            except ImportError:
                print("⚠️  FAISS not available, using fallback")
        
        # Fallback: búsqueda inteligente en docs de Mawell
        if os.path.exists(DOC_FILE):
            try:
                with open(DOC_FILE, "rb") as f:
                    docs = pickle.load(f)
                
                print(f"📚 Buscando en {len(docs)} fragmentos de documentos de Mawell...")
                
                # Búsqueda más inteligente por keywords relevantes
                query_lower = query.lower().strip()
                query_words = [word for word in query_lower.split() if len(word) > 2]
                
                # Mapeo de sinónimos para mejorar búsqueda
                synonyms = {
                    'sistemas': ['sistemas', 'system', 'informática', 'computación'],
                    'ingeniería': ['ingeniería', 'ingenieria', 'engineering', 'carrera'],
                    'carreras': ['carreras', 'carrera', 'programa', 'especialidad'],
                    'becas': ['becas', 'beca', 'descuento', 'ayuda']
                }
                
                # Expandir palabras de búsqueda con sinónimos
                expanded_words = set(query_words)
                for word in query_words:
                    for key, syns in synonyms.items():
                        if word in syns:
                            expanded_words.update(syns)
                
                relevant_docs = []
                for doc in docs:
                    # Manejar formato dict o string
                    doc_text = doc.get('text', str(doc)) if isinstance(doc, dict) else str(doc)
                    doc_lower = doc_text.lower()
                    score = 0
                    
                    # Puntuar por coincidencias exactas de frases
                    if query_lower in doc_lower:
                        score += 20
                    
                    # Puntuar por palabras individuales
                    for word in expanded_words:
                        count = doc_lower.count(word)
                        score += count * 2
                    
                    # Bonus especial para títulos/encabezados
                    if any(word in doc_text[:100] for word in expanded_words):
                        score += 5
                    
                    if score > 0:
                        relevant_docs.append((doc_text, score))
                
                # Ordenar por relevancia y tomar los mejores
                if relevant_docs:
                    relevant_docs.sort(key=lambda x: x[1], reverse=True)
                    best_docs = [doc for doc, score in relevant_docs[:top_k]]
                    print(f"✅ Encontrados {len(best_docs)} fragmentos relevantes")
                    return best_docs
                
                print("⚠️ No se encontraron fragmentos relevantes")
                return None
            except Exception as e:
                print(f"❌ Error leyendo documentos: {e}")
                pass
        
        print("❌ No vector database or docs available")
        return None
        
    except Exception as e:
        print(f"❌ Error getting relevant chunks: {e}")
        return None


def ask_mistral_with_context(query: str) -> dict:
    chunks = get_relevant_chunks(query)

    if not chunks:
        # Respuesta básica cuando no hay contexto específico
        basic_response = (
            "Hola, soy el asistente virtual de Mawell. "
            "No encontré información específica sobre tu consulta en los documentos disponibles. "
            "¿Podrías ser más específico sobre qué información de Mawell necesitas? "
            "Tengo acceso a información sobre carreras, reglamentos académicos y becas."
        )
        return {
            "question": query,
            "answer": basic_response
        }

    # Si hay contexto, crear respuesta basada en los documentos
    context = "\n".join(chunks)
    
    # Intentar usar Ollama, pero si no está disponible, usar fallback inteligente
    try:
        response = requests.post(
            OLLAMA_API_URL, 
            json={
                "model": OLLAMA_MODEL_NAME,
                "prompt": f"Responde como asistente de Mawell basándote en: {context}\nPregunta: {query}",
                "stream": False
            },
            timeout=10  # Timeout corto para fallar rápido
        )

        if response.status_code == 200:
            answer = response.json().get("response", "").strip()
        else:
            raise Exception(f"Ollama error: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Ollama no disponible, usando respuesta basada en contexto: {e}")
        
        # Fallback: respuesta inteligente basada en el contexto encontrado
        context_preview = context[:500] + "..." if len(context) > 500 else context
        answer = (
            f"Basándome en la información de Mawell que encontré:\n\n"
            f"{context_preview}\n\n"
            f"Esta información debería ayudarte con tu consulta sobre: {query}. "
            f"¿Necesitas más detalles específicos sobre algún punto?"
        )

    return {
        "question": query,
        "answer": answer
    }
