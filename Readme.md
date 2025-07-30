# 🧠 Asistente Virtual con Memoria (RAG + FastAPI)

Este backend implementa un asistente virtual inteligente con memoria de conversaciones. Utiliza RAG (Retrieval-Augmented Generation) con documentos PDF, Ollama con el modelo Mistral y FastAPI como framework principal.

---

## ✅ Requisitos técnicos

### 📦 `requirements.txt`
```txt
fastapi
uvicorn
sqlalchemy
psycopg2-binary
python-jose[cryptography]
passlib[bcrypt]
sentence-transformers
pymupdf
faiss-cpu
requests
email-validator
```

### ⚙️ Entorno virtual
```bash
python -m venv env
.\env\Scriptsctivate
pip install -r requirements.txt
```

---

## 🧠 IA y vectorización (RAG)

### 🦙 Ollama
- Instalar desde: https://ollama.com
- Iniciar modelo:
```bash
ollama run mistral
```

### 🧱 FAISS Vector Store
- Cargar y trocear texto de PDFs
- Generar embeddings con `sentence-transformers`
- Guardar vector DB con FAISS (`index.faiss` y `docs.pkl`)

---

## 📁 Estructura del Proyecto

```
backend-mawell/
├── app/
│   ├── api/           ← Endpoints FastAPI
│   ├── models/        ← Modelos SQLAlchemy
│   ├── schemas/       ← Esquemas Pydantic
│   ├── services/      ← JWT, IA, Embeddings
│   ├── config.py      ← Conexión a PostgreSQL
│   └── main.py        ← Entry point
├── data/
│   ├── pdfs/          ← PDFs cargados
│   └── vector_db/     ← FAISS + chunks serializados
├── scripts/
│   └── create_index.py ← Script para vectorizar PDF
├── media/             ← Recursos multimedia
├── requirements.txt
└── .env (opcional)
```

---

## 📄 Modelos SQLAlchemy

### 🔐 `User`
```python
id: int
email: str
hashed_password: str
created_at: datetime
```
Usuarios registrados con autenticación JWT.

### 💬 `Conversation`
```python
id: int
user_id: int (FK → User)
title: str
created_at: datetime
```
Representa un hilo de conversación del usuario.

### 📨 `Message`
```python
id: int
conversation_id: int (FK → Conversation)
user_id: int (FK → User)
question: str
answer: str
timestamp: datetime
```
Mensaje individual enviado por un usuario y su respuesta generada.

---

## 📦 Esquemas Pydantic

### `UserCreate`, `UserLogin`, `UserResponse`
- Entrada y salida para `/auth/register` y `/auth/login`

### `ConversationCreate`, `ConversationResponse`
- Crear conversaciones y devolver metadatos del hilo

### `ChatRequest`
```python
conversation_id: int
question: str
```

### `MessageResponse`
```python
id: int
question: str
answer: str
timestamp: datetime
```

---

## 🔐 Servicios

### `auth_service.py`
- `hash_password()`, `verify_password()`
- `create_access_token()`, `get_current_user()`

### `embedding_service.py`
- `extract_text_from_pdf()`, `chunk_text()`, `build_vector_index()`

### `ia_service.py`
- `ask_mistral_with_context()` – construye el prompt con historial y consulta a Ollama

---

## 📌 Endpoints implementados

### 🔑 Auth
- `POST /auth/register` → Registro de usuario
- `POST /auth/login` → Login con JWT

### 💬 Chat
- `POST /chat/start` → Crear conversación
- `POST /chat/send` → Enviar pregunta y guardar respuesta
- `GET /chat/{conversation_id}/messages` → Ver historial

---

## 🛠️ Comandos útiles

```bash
# Iniciar servidor FastAPI
uvicorn app.main:app --reload --port 8000

# Ejecutar script para cargar y vectorizar PDF
python -m scripts.create_index
```

---

## ✨ Estado actual
Sistema funcional que permite:
- Autenticación JWT
- Carga y recuperación de documentos PDF
- Consulta a IA con historial por conversación
- Persistencia de conversaciones y mensajes