import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import Base, engine
from app.api import chat_router

app = FastAPI(
    title="Asistente Virtual Mawell",
    description="Backend FastAPI para chatbot IA con integración a PDF",
    version="1.0.0",
)


# CORS para permitir peticiones del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, definir frontend exacto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {
        "message": "API Mawell IA activa 🚀",
        "status": "healthy",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "mawell-assistant"}


app.include_router(chat_router)