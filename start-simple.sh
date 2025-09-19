#!/bin/bash
echo "🚀 Starting Mawell Assistant..."
echo "Port: ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
