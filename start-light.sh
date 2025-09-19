#!/bin/bash

echo "🚀 Starting Mawell Assistant on Railway (Light Version)..."

# Check if vector database exists
if [ ! -f "data/vector_db/index.faiss" ] || [ ! -f "data/vector_db/docs.pkl" ]; then
    echo "⚠️  Vector database not found. The app will work but without PDF context."
fi

# Check SQLite database
if [ -f "mawell_assistant.db" ]; then
    echo "✅ SQLite database found"
else
    echo "📝 SQLite database will be created automatically"
fi

# Note: Ollama will be used via external API
echo "🤖 Using external Ollama API for AI processing..."

# Start FastAPI with proper port handling
echo "🌐 Starting FastAPI server..."
PORT=${PORT:-8000}
echo "Using port: $PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
