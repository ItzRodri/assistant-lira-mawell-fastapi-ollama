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
# Database (Railway proveerá automáticamente PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname

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

### 4. Añadir PostgreSQL
1. En tu proyecto de Railway, haz clic en "New Service"
2. Selecciona "Database" → "PostgreSQL"
3. Railway automáticamente configurará `DATABASE_URL`

### 5. Configurar el dominio
1. Ve a la pestaña "Settings" de tu servicio
2. En "Domains", genera un dominio público
3. Tu API estará disponible en: `https://tu-app.railway.app`

## ⚠️ Consideraciones importantes

### Recursos y límites
- **Railway Free Plan**: 500 horas/mes, $5 de crédito
- **Ollama + Mistral**: Requiere ~2-4GB RAM
- **Startup time**: ~2-3 minutos (descarga de Mistral)

### Base de datos vectorial
Los archivos en `data/vector_db/` se incluyen en el despliegue para que la funcionalidad RAG funcione inmediatamente.

### Monitoreo
- Logs disponibles en Railway dashboard
- Health check en: `https://tu-app.railway.app/health`
- Status en: `https://tu-app.railway.app/`

## 🔧 Troubleshooting

### Error: "Ollama not responding"
- Espera 2-3 minutos para que Mistral se descargue
- Verifica logs en Railway dashboard

### Error: "Vector database not found"
- Asegúrate que `data/vector_db/` esté en el repositorio
- Ejecuta localmente: `python -m scripts.create_index`

### Error: "Database connection failed"
- Verifica que PostgreSQL esté añadido al proyecto
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

1. **Startup optimizado**: Script `start.sh` maneja Ollama
2. **Error handling**: Manejo robusto de errores de conexión
3. **Database**: Soporte PostgreSQL + SQLite fallback
4. **Timeouts**: Configurados para Railway
5. **Health checks**: Endpoints de monitoreo
6. **CORS**: Configurado para producción

¡Tu asistente virtual estará listo en unos minutos! 🎉
