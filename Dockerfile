# Use Python 3.11 alpine for smaller size
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    curl \
    bash

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with minimal cache
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/vector_db data/pdfs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE $PORT

# Make start script executable
RUN chmod +x start-light.sh

# Use lightweight start without Ollama
CMD ["./start-light.sh"]
