import os
import requests
import pickle
from dotenv import load_dotenv

load_dotenv()

# Config from .env with defaults
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
INDEX_FILE = os.getenv("VECTOR_DB_INDEX", "data/vector_db/index.faiss")
DOC_FILE = os.getenv("VECTOR_DB_DOCS", "data/vector_db/docs.pkl")

# Use external Ollama service or fallback
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "mistral")

# Fallback mode when dependencies are not available
FALLBACK_MODE = os.getenv("FALLBACK_MODE", "true").lower() == "true"

# Initialize model with error handling (optional dependency)
MODEL = None
try:
    from sentence_transformers import SentenceTransformer
    MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print(f"✅ Embedding model '{EMBEDDING_MODEL_NAME}' loaded successfully")
except ImportError:
    print("⚠️  sentence-transformers not available. Using fallback mode.")
except Exception as e:
    print(f"❌ Error loading embedding model: {e}")
    MODEL = None

# Distance threshold: si no hay chunks relevantes, se evita responder
MAX_DISTANCE_THRESHOLD = 0.85

# System prompt para generar respuestas naturales
SYSTEM_PROMPT = """
Eres un asistente virtual especializado de Mawell, una empresa de equipos y servicios industriales.

INSTRUCCIONES IMPORTANTES:
1. Responde de manera conversacional y natural, como un experto consultor
2. Usa la información proporcionada como base, pero reformúlala con tus propias palabras
3. Sé específico y técnico cuando sea apropiado, pero mantén un lenguaje claro
4. Si la información no está completa, menciona que puedes proporcionar más detalles
5. Mantén un tono profesional pero amigable
6. Nunca copies literalmente el texto de los documentos
7. Estructura tu respuesta de manera clara y organizada

NUNCA devuelvas texto literal de los documentos. Siempre reformula y explica con tus propias palabras.
""".strip()


def get_relevant_chunks(query: str, top_k=4):
    try:
        # Try to use vector search if available
        if MODEL and os.path.exists(INDEX_FILE) and os.path.exists(DOC_FILE):
            try:
                import faiss
                index = faiss.read_index(INDEX_FILE)
                with open(DOC_FILE, "rb") as f:
                    docs = pickle.load(f)

                query_vec = MODEL.encode([query])
                distances, indices = index.search(query_vec, top_k)

                # Si ninguna distancia es suficientemente baja, no hay contexto relevante
                if all(dist > MAX_DISTANCE_THRESHOLD for dist in distances[0]):
                    return None

                return [docs[i] for i in indices[0]]
            except ImportError:
                print("⚠️  FAISS not available, using fallback")
        
        # Fallback: búsqueda inteligente en docs de Mawell
        if os.path.exists(DOC_FILE):
            try:
                with open(DOC_FILE, "rb") as f:
                    docs = pickle.load(f)
                
                print(f"📚 Buscando en {len(docs)} fragmentos de documentos de Mawell...")
                
                # Búsqueda más inteligente por keywords relevantes
                query_lower = query.lower().strip()
                query_words = [word for word in query_lower.split() if len(word) > 2]
                
                # Mapeo de sinónimos para mejorar búsqueda
                synonyms = {
                    'sistemas': ['sistemas', 'system', 'informática', 'computación'],
                    'ingeniería': ['ingeniería', 'ingenieria', 'engineering', 'carrera'],
                    'carreras': ['carreras', 'carrera', 'programa', 'especialidad'],
                    'becas': ['becas', 'beca', 'descuento', 'ayuda']
                }
                
                # Expandir palabras de búsqueda con sinónimos
                expanded_words = set(query_words)
                for word in query_words:
                    for key, syns in synonyms.items():
                        if word in syns:
                            expanded_words.update(syns)
                
                relevant_docs = []
                for doc in docs:
                    # Manejar formato dict o string
                    doc_text = doc.get('text', str(doc)) if isinstance(doc, dict) else str(doc)
                    doc_lower = doc_text.lower()
                    score = 0
                    
                    # Puntuar por coincidencias exactas de frases
                    if query_lower in doc_lower:
                        score += 20
                    
                    # Puntuar por palabras individuales
                    for word in expanded_words:
                        count = doc_lower.count(word)
                        score += count * 2
                    
                    # Bonus especial para títulos/encabezados
                    if any(word in doc_text[:100] for word in expanded_words):
                        score += 5
                    
                    if score > 0:
                        relevant_docs.append((doc_text, score))
                
                # Ordenar por relevancia y tomar los mejores
                if relevant_docs:
                    relevant_docs.sort(key=lambda x: x[1], reverse=True)
                    best_docs = [doc for doc, score in relevant_docs[:top_k]]
                    print(f"✅ Encontrados {len(best_docs)} fragmentos relevantes")
                    return best_docs
                
                print("⚠️ No se encontraron fragmentos relevantes")
                return None
            except Exception as e:
                print(f"❌ Error leyendo documentos: {e}")
                pass
        
        print("❌ No vector database or docs available")
        return None
        
    except Exception as e:
        print(f"❌ Error getting relevant chunks: {e}")
        return None


def ask_mistral_with_context(query: str) -> dict:
    chunks = get_relevant_chunks(query)

    if not chunks:
        # Respuesta básica cuando no hay contexto específico
        basic_response = (
            "Hola, soy el asistente virtual de Mawell. "
            "No encontré información específica sobre tu consulta en los documentos disponibles. "
            "¿Podrías ser más específico sobre qué información de Mawell necesitas? "
            "Tengo acceso a información sobre Mawell"
        )
        return {
            "question": query,
            "answer": basic_response
        }

    # Si hay contexto, crear respuesta basada en los documentos
    context = "\n".join(chunks)
    
    # Intentar usar Ollama con prompt mejorado
    try:
        # Crear prompt estructurado para mejor respuesta
        full_prompt = f"""
{SYSTEM_PROMPT}

CONTEXTO DE MAWELL:
{context}

PREGUNTA DEL USUARIO: {query}

INSTRUCCIÓN: Basándote en el contexto proporcionado, responde la pregunta del usuario de manera natural y conversacional. Reformula la información con tus propias palabras, no copies literalmente el texto del contexto.

RESPUESTA:"""

        response = requests.post(
            OLLAMA_API_URL, 
            json={
                "model": OLLAMA_MODEL_NAME,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            },
            timeout=15  # Timeout un poco más largo para respuestas elaboradas
        )

        if response.status_code == 200:
            answer = response.json().get("response", "").strip()
            # Validar que la respuesta no sea solo el contexto copiado
            if len(answer) > 50 and not _is_mostly_copied_text(answer, context):
                return {
                    "question": query,
                    "answer": answer
                }
        else:
            raise Exception(f"Ollama error: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Ollama no disponible, usando generador de respuestas inteligente: {e}")
    
    # Fallback: generador de respuestas inteligente sin IA externa
    answer = _generate_intelligent_response(query, context)
    
    return {
        "question": query,
        "answer": answer
    }


def _is_mostly_copied_text(response: str, context: str, threshold: 0.8) -> bool:
    """Detecta si la respuesta es principalmente texto copiado del contexto"""
    if not response or not context:
        return False
    
    response_words = set(response.lower().split())
    context_words = set(context.lower().split())
    
    if len(response_words) == 0:
        return True
    
    overlap = len(response_words.intersection(context_words))
    similarity = overlap / len(response_words)
    
    return similarity > threshold


def _generate_intelligent_response(query: str, context: str) -> str:
    """
    Genera una respuesta inteligente basada en el contexto sin usar IA externa.
    Reformula y estructura la información de manera natural.
    """
    # Limpiar y preparar el contexto
    context_lines = [line.strip() for line in context.split('\n') if line.strip()]
    
    # Detectar el tipo de pregunta
    query_lower = query.lower()
    
    # Palabras clave para diferentes tipos de respuesta
    question_types = {
        'que_es': ['qué es', 'que es', 'define', 'definición', 'significa'],
        'como_funciona': ['cómo funciona', 'como funciona', 'funcionamiento', 'proceso'],
        'equipos': ['equipo', 'equipos', 'maquina', 'maquinas', 'dispositivo'],
        'servicios': ['servicio', 'servicios', 'ofrecen', 'proporcionan'],
        'especificaciones': ['especificaciones', 'características', 'detalles técnicos'],
        'precio': ['precio', 'costo', 'cotización', 'presupuesto']
    }
    
    # Identificar tipo de pregunta
    detected_type = 'general'
    for q_type, keywords in question_types.items():
        if any(keyword in query_lower for keyword in keywords):
            detected_type = q_type
            break
    
    # Generar respuesta según el tipo
    if detected_type == 'que_es':
        answer = _format_definition_response(query, context_lines)
    elif detected_type == 'como_funciona':
        answer = _format_process_response(query, context_lines)
    elif detected_type == 'equipos':
        answer = _format_equipment_response(query, context_lines)
    elif detected_type == 'servicios':
        answer = _format_services_response(query, context_lines)
    elif detected_type == 'especificaciones':
        answer = _format_specifications_response(query, context_lines)
    elif detected_type == 'precio':
        answer = _format_pricing_response(query, context_lines)
    else:
        answer = _format_general_response(query, context_lines)
    
    return answer


def _format_definition_response(query: str, context_lines: list) -> str:
    """Formatea respuesta para preguntas de definición"""
    intro = "Te explico sobre lo que consultas:\n\n"
    
    # Buscar información clave en las primeras líneas
    key_info = []
    for line in context_lines[:5]:
        if len(line) > 20:  # Evitar líneas muy cortas
            key_info.append(line)
    
    if key_info:
        main_content = "Según la información de Mawell, " + key_info[0].lower()
        if len(key_info) > 1:
            main_content += f"\n\nAdemás, {key_info[1]}"
    else:
        main_content = "Basándome en la documentación de Mawell, puedo proporcionarte información relevante sobre tu consulta."
    
    conclusion = "\n\n¿Te gustaría que profundice en algún aspecto específico?"
    
    return intro + main_content + conclusion


def _format_equipment_response(query: str, context_lines: list) -> str:
    """Formatea respuesta para preguntas sobre equipos"""
    intro = "Sobre el equipo que consultas:\n\n"
    
    # Buscar características y funciones
    features = []
    applications = []
    
    for line in context_lines:
        line_lower = line.lower()
        if any(word in line_lower for word in ['características', 'función', 'permite', 'capacidad']):
            features.append(line)
        elif any(word in line_lower for word in ['aplicación', 'uso', 'industria', 'sector']):
            applications.append(line)
    
    response = intro
    
    if features:
        response += "**Características principales:**\n"
        for feature in features[:3]:  # Limitar a 3 características
            response += f"• {feature}\n"
        response += "\n"
    
    if applications:
        response += "**Aplicaciones:**\n"
        for app in applications[:2]:  # Limitar a 2 aplicaciones
            response += f"• {app}\n"
        response += "\n"
    
    if not features and not applications:
        # Fallback con información general
        if context_lines:
            response += f"Este equipo {context_lines[0].lower()}\n\n"
    
    response += "¿Necesitas información más específica sobre alguna característica en particular?"
    
    return response


def _format_services_response(query: str, context_lines: list) -> str:
    """Formatea respuesta para preguntas sobre servicios"""
    intro = "Respecto a los servicios de Mawell:\n\n"
    
    services = []
    benefits = []
    
    for line in context_lines:
        line_lower = line.lower()
        if any(word in line_lower for word in ['servicio', 'ofrecemos', 'proporcionamos', 'brindamos']):
            services.append(line)
        elif any(word in line_lower for word in ['beneficio', 'ventaja', 'garantía']):
            benefits.append(line)
    
    response = intro
    
    if services:
        response += "**Servicios disponibles:**\n"
        for service in services[:4]:
            response += f"• {service}\n"
        response += "\n"
    
    if benefits:
        response += "**Beneficios:**\n"
        for benefit in benefits[:2]:
            response += f"• {benefit}\n"
        response += "\n"
    
    response += "¿Te interesa conocer más detalles sobre algún servicio en particular?"
    
    return response


def _format_general_response(query: str, context_lines: list) -> str:
    """Formatea respuesta general"""
    intro = "Basándome en la información de Mawell:\n\n"
    
    # Tomar las líneas más informativas
    informative_lines = [line for line in context_lines if len(line) > 30]
    
    response = intro
    
    if informative_lines:
        # Estructurar la información
        for i, line in enumerate(informative_lines[:3]):
            if i == 0:
                response += f"{line}\n\n"
            else:
                response += f"Adicionalmente, {line.lower()}\n\n"
    else:
        response += "He encontrado información relevante en nuestros documentos que puede ayudarte.\n\n"
    
    response += "¿Hay algún aspecto específico sobre el que te gustaría que profundice?"
    
    return response


def _format_process_response(query: str, context_lines: list) -> str:
    """Formatea respuesta para preguntas sobre procesos"""
    intro = "Te explico el funcionamiento:\n\n"
    
    steps = []
    for line in context_lines:
        if any(word in line.lower() for word in ['proceso', 'funciona', 'opera', 'paso', 'etapa']):
            steps.append(line)
    
    response = intro
    if steps:
        response += "**Proceso:**\n"
        for i, step in enumerate(steps[:4], 1):
            response += f"{i}. {step}\n"
        response += "\n"
    else:
        if context_lines:
            response += f"{context_lines[0]}\n\n"
    
    response += "¿Necesitas más detalles sobre algún paso específico?"
    return response


def _format_specifications_response(query: str, context_lines: list) -> str:
    """Formatea respuesta para especificaciones técnicas"""
    intro = "Especificaciones técnicas:\n\n"
    
    specs = []
    for line in context_lines:
        if any(word in line.lower() for word in ['especificación', 'técnico', 'capacidad', 'dimensión', 'potencia']):
            specs.append(line)
    
    response = intro
    if specs:
        for spec in specs[:5]:
            response += f"• {spec}\n"
        response += "\n"
    else:
        if context_lines:
            response += f"Según la documentación: {context_lines[0]}\n\n"
    
    response += "¿Requieres información técnica más específica?"
    return response


def _format_pricing_response(query: str, context_lines: list) -> str:
    """Formatea respuesta para consultas de precios"""
    intro = "Sobre precios y cotizaciones:\n\n"
    
    pricing_info = []
    for line in context_lines:
        if any(word in line.lower() for word in ['precio', 'costo', 'cotización', 'presupuesto']):
            pricing_info.append(line)
    
    response = intro
    if pricing_info:
        for info in pricing_info[:3]:
            response += f"• {info}\n"
        response += "\n"
    else:
        response += "Para obtener información específica de precios y cotizaciones, te recomiendo contactar directamente con nuestro equipo comercial.\n\n"
    
    response += "¿Te gustaría que te proporcione información de contacto para una cotización personalizada?"
    return response
