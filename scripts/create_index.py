import os
from dotenv import load_dotenv
from app.services.embedding_service import build_vector_index

load_dotenv()
pdf_path = os.getenv("PDF_SOURCE_PATH", "data/pdfs/piensa_como_programador.pdf")
build_vector_index(pdf_path)