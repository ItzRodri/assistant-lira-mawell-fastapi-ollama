# 🚀 Despliegue en Railway - Asistente Virtual Mawell

## 📋 Pasos para desplegar en Railway

### 1. Preparar el repositorio
```bash
git add .
git commit -m "Railway deployment configuration"
git push origin main
```

### 2. Crear proyecto en Railway
1. Ve a [railway.app](https://railway.app)
2. Conecta tu cuenta de GitHub
3. Selecciona "Deploy from GitHub repo"
4. Elige tu repositorio: `assistant-lira-mawell-fastapi-ollama`

### 3. Configurar variables de entorno en Railway

En el dashboard de Railway, ve a la pestaña **Variables** y añade:

```bash
# Database (SQLite - más simple y eficiente para este caso)
DATABASE_URL=sqlite:///./mawell_assistant.db

# Embedding Model
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2

# Vector Database Paths
VECTOR_DB_INDEX=data/vector_db/index.faiss
VECTOR_DB_DOCS=data/vector_db/docs.pkl

# Ollama Configuration
OLLAMA_API_URL=http://localhost:11434/api/generate
OLLAMA_MODEL_NAME=mistral

# JWT Configuration
SECRET_KEY=tu-clave-secreta-super-segura-para-jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. ¡No necesitas base de datos externa!
✅ **SQLite está incluido** - No necesitas añadir PostgreSQL
✅ **Más rápido** - Sin latencia de red a BD externa
✅ **Más barato** - Sin costos adicionales de base de datos
✅ **Más simple** - Una sola configuración

### 5. Configurar el dominio
1. Ve a la pestaña "Settings" de tu servicio
2. En "Domains", genera un dominio público
3. Tu API estará disponible en: `https://tu-app.railway.app`

## ⚠️ Consideraciones importantes

### Recursos y límites
- **Railway Free Plan**: 500 horas/mes, $5 de crédito
- **Versión ligera**: ~512MB RAM (sin Ollama local)
- **Startup time**: ~30 segundos (versión optimizada)
- **Ollama**: Usa API externa o modo fallback

### Base de datos vectorial
Los archivos en `data/vector_db/` se incluyen en el despliegue para que la funcionalidad RAG funcione inmediatamente.

### Monitoreo
- Logs disponibles en Railway dashboard
- Health check en: `https://tu-app.railway.app/health`
- Status en: `https://tu-app.railway.app/`

## 🔧 Troubleshooting

### Error: "Ollama not responding"
- La app funciona en modo fallback cuando Ollama no está disponible
- Responde con "Mucho gusto estamos probando" + contexto

### Error: "Vector database not found"
- Asegúrate que `data/vector_db/` esté en el repositorio
- Ejecuta localmente: `python -m scripts.create_index`

### Error: "Database connection failed"
- Verifica que la ruta de SQLite sea correcta: `sqlite:///./mawell_assistant.db`
- Confirma que `DATABASE_URL` esté configurada

## 📊 Endpoints disponibles

- **GET** `/` - Status de la API
- **GET** `/health` - Health check
- **POST** `/auth/register` - Registro de usuario
- **POST** `/auth/login` - Login
- **POST** `/chat/start` - Crear conversación
- **POST** `/chat/send` - Enviar mensaje
- **GET** `/chat/{id}/messages` - Historial

## 💡 Optimizaciones aplicadas

1. **Imagen ligera**: Alpine Linux + Python 3.11 (< 1GB vs 12GB)
2. **Sin Ollama local**: Evita el límite de 4GB de Railway
3. **Modo fallback**: Funciona aunque Ollama no esté disponible
4. **Database**: SQLite optimizado para Railway
5. **Startup rápido**: ~30 segundos vs 3 minutos
6. **Health checks**: Endpoints de monitoreo
7. **CORS**: Configurado para producción
8. **Persistencia**: SQLite se mantiene entre deployments

¡Tu asistente virtual estará listo en unos minutos! 🎉
