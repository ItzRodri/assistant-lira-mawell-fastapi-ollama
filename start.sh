#!/bin/bash

echo "🚀 Starting Mawell Assistant on Railway..."

# Start Ollama in background
echo "📦 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
sleep 10

# Pull Mistral model
echo "🤖 Pulling Mistral model..."
ollama pull mistral

# Check if vector database exists
if [ ! -f "data/vector_db/index.faiss" ] || [ ! -f "data/vector_db/docs.pkl" ]; then
    echo "⚠️  Vector database not found. The app will work but without PDF context."
fi

# Start FastAPI
echo "🌐 Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
