import os
import fitz
from sentence_transformers import SentenceTransformer
import faiss
import pickle

MODEL = SentenceTransformer("distiluse-base-multilingual-cased-v1")
INDEX_FILE = "data/vector_db/index.faiss"
DOC_FILE = "data/vector_db/docs.pkl"

def extract_text_from_pdf(pdf_path: str):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

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

def build_vector_index(pdf_path: str):
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)
    embeddings = MODEL.encode(chunks)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    os.makedirs("data/vector_db", exist_ok=True)
    faiss.write_index(index, INDEX_FILE)
    with open(DOC_FILE, "wb") as f:
        pickle.dump(chunks, f)

    print(f"✅ Vector DB creada con {len(chunks)} fragmentos.")
