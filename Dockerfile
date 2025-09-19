# Super minimal Dockerfile for Railway - NO ML dependencies
FROM python:3.11-slim

WORKDIR /app

# Copy and install minimal requirements (NO sentence-transformers, NO faiss)
COPY requirements-minimal.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only essential files
COPY app/ ./app/
COPY data/ ./data/
COPY mawell_assistant.db ./
COPY start-light.sh ./

# Environment and permissions
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
RUN chmod +x start-light.sh

# Start the app
CMD ["./start-light.sh"]
