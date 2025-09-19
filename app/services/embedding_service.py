# /services/embedding_service.py

import os
from sentence_transformers import SentenceTransformer
import faiss
import pickle

MODEL = SentenceTransformer("distiluse-base-multilingual-cased-v1")  # Español incluido
INDEX_FILE = "data/vector_db/index.faiss"
DOC_FILE = "data/vector_db/docs.pkl"

# Función para extraer el texto del PDF (fallback sin PyMuPDF)
def extract_text_from_pdf(pdf_path: str):
    """
    Extrae texto de PDF. En la versión ligera, los PDFs ya están procesados
    y guardados en la base de datos vectorial.
    """
    try:
        # Try to import PyMuPDF if available
        import fitz
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    except ImportError:
        print("⚠️  PyMuPDF no disponible. Los PDFs deben estar pre-procesados.")
        return ""

# Función para dividir el texto en fragmentos (chunks)
def chunk_text(text: str, max_length=500):
    sentences = text.split(". ")
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

# Cargar el índice FAISS existente o crear uno nuevo
def load_or_create_index(embedding_dim):
    if os.path.exists(INDEX_FILE):
        print("Cargando índice FAISS existente...")
        index = faiss.read_index(INDEX_FILE)
        # Verificar si la dimensión del índice es la misma
        if index.d != embedding_dim:
            raise ValueError(f"Dimensiones del índice no coinciden. Esperado {embedding_dim}, pero encontrado {index.d}.")
    else:
        print("Creando un nuevo índice FAISS...")
        index = faiss.IndexFlatL2(embedding_dim)  # Usa la dimensión correcta
    return index

# Función para actualizar el índice con nuevos PDFs
def build_vector_index(pdf_path: str):
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)
    embeddings = MODEL.encode(chunks)

    # Obtén la dimensión de los embeddings
    embedding_dim = embeddings.shape[1]

    # Cargar el índice existente o crear uno nuevo
    index = load_or_create_index(embedding_dim)

    # Añadir los nuevos embeddings al índice
    index.add(embeddings)

    # Guardar el índice actualizado
    os.makedirs("data/vector_db", exist_ok=True)
    faiss.write_index(index, INDEX_FILE)

    # Guardar los chunks en un archivo
    if os.path.exists(DOC_FILE):
        with open(DOC_FILE, "rb") as f:
            existing_chunks = pickle.load(f)
    else:
        existing_chunks = []

    existing_chunks.extend(chunks)

    with open(DOC_FILE, "wb") as f:
        pickle.dump(existing_chunks, f)

    print(f"✅ Vector DB actualizada con {len(chunks)} fragmentos. Total de fragmentos: {len(existing_chunks)}")
