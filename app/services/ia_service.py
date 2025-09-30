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

# Distance threshold: umbral más estricto para evitar respuestas irrelevantes
MAX_DISTANCE_THRESHOLD = 0.65

# System prompt para generar respuestas naturales
SYSTEM_PROMPT = """
Eres un asistente virtual especializado de Mawell, una empresa de equipos y servicios industriales.

INSTRUCCIONES CRÍTICAS:
1. SOLO responde sobre temas relacionados con Mawell: equipos industriales, servicios técnicos, productos de la empresa
2. Si la pregunta NO está relacionada con Mawell, responde: "Lo siento, solo puedo ayudarte con información sobre los equipos y servicios de Mawell"
3. Usa ÚNICAMENTE la información proporcionada en el contexto
4. Reformula la información con tus propias palabras, NUNCA copies literalmente
5. Mantén un tono profesional y técnico apropiado
6. Estructura tu respuesta de manera clara y organizada
7. SIEMPRE termina con: "¿Puedo ayudarte con algo más?"

REGLA ABSOLUTA: Si el contexto no es relevante para la pregunta sobre Mawell, NO inventes información.
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
                
                # Mapeo de sinónimos específicos de Mawell
                synonyms = {
                    'equipos': ['equipos', 'equipo', 'maquinaria', 'dispositivos', 'aparatos'],
                    'servicios': ['servicios', 'servicio', 'mantenimiento', 'instalación', 'reparación'],
                    'bombas': ['bomba', 'bombas', 'bomba centrífuga', 'bomba dosificadora'],
                    'filtros': ['filtro', 'filtros', 'filtración', 'purificación'],
                    'agua': ['agua', 'ultrapura', 'purificación', 'tratamiento'],
                    'análisis': ['análisis', 'analizador', 'termográfico', 'detección'],
                    'industrial': ['industrial', 'industria', 'técnico', 'profesional'],
                    'mawell': ['mawell', 'empresa', 'compañía']
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
                    
                    # Verificar que el documento sea realmente sobre Mawell y no sea solo preguntas
                    mawell_indicators = ['mawell', 'equipo', 'servicio', 'industrial', 'bomba', 'filtro', 'sistema']
                    has_mawell_content = any(indicator in doc_lower for indicator in mawell_indicators)
                    
                    # Filtrar documentos que son principalmente preguntas
                    question_indicators = ['¿', '?']
                    question_count = sum(doc_text.count(indicator) for indicator in question_indicators)
                    total_sentences = max(doc_text.count('.') + doc_text.count('?') + doc_text.count('!'), 1)
                    question_ratio = question_count / total_sentences
                    
                    if not has_mawell_content or question_ratio > 0.7:  # Si más del 70% son preguntas, saltar
                        continue
                    
                    # Puntuar por coincidencias exactas de frases (más peso)
                    if query_lower in doc_lower:
                        score += 50
                    
                    # Puntuar por palabras clave importantes
                    important_matches = 0
                    for word in query_words:
                        if len(word) > 3 and word in doc_lower:  # Solo palabras importantes
                            count = doc_lower.count(word)
                            score += count * 10
                            important_matches += count
                    
                    # Puntuar por sinónimos expandidos (menos peso)
                    for word in expanded_words:
                        if word not in query_words:  # Solo sinónimos adicionales
                            count = doc_lower.count(word)
                            score += count * 3
                    
                    # Bonus para títulos/encabezados con palabras clave
                    header_text = doc_text[:150].lower()
                    for word in query_words:
                        if word in header_text:
                            score += 15
                    
                    # Requerir al menos 2 coincidencias importantes o una coincidencia exacta
                    if score >= 20 and (important_matches >= 2 or query_lower in doc_lower):
                        relevant_docs.append((doc_text, score))
                
                # Ordenar por relevancia y tomar solo los más relevantes
                if relevant_docs:
                    relevant_docs.sort(key=lambda x: x[1], reverse=True)
                    # Filtrar solo documentos con alta puntuación
                    high_score_docs = [(doc, score) for doc, score in relevant_docs if score >= 30]
                    
                    if high_score_docs:
                        best_docs = [doc for doc, score in high_score_docs[:top_k]]
                        print(f"✅ Encontrados {len(best_docs)} fragmentos altamente relevantes (scores: {[score for _, score in high_score_docs[:top_k]]})")
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
        # Verificar si la pregunta está relacionada con Mawell de forma más estricta
        query_lower = query.lower()
        
        # Términos específicos de Mawell
        mawell_specific_terms = [
            'mawell', 'bomba centrífuga', 'bomba dosificadora', 'analizador termográfico',
            'sistema de agua ultrapura', 'filtro autolimpiante', 'cabina de bioseguridad',
            'sistema de detección de gases', 'sistema de monitoreo vibracional',
            'sistema de filtración multicapa'
        ]
        
        # Términos generales industriales (requieren contexto adicional)
        industrial_terms = [
            'equipo', 'equipos', 'servicio', 'servicios', 'bomba', 'bombas',
            'filtro', 'filtros', 'sistema', 'sistemas', 'industrial', 'analizador',
            'termográfico', 'agua', 'ultrapura', 'dosificadora', 'centrífuga',
            'bioseguridad', 'detección', 'gases', 'vibracional', 'autolimpiante'
        ]
        
        # Términos claramente irrelevantes
        irrelevant_terms = [
            'clima', 'tiempo', 'cocinar', 'receta', 'capital', 'país', 'ciudad',
            'política', 'deportes', 'música', 'película', 'entretenimiento',
            'salud personal', 'medicina', 'educación general'
        ]
        
        # Verificar si es claramente irrelevante
        is_clearly_irrelevant = any(term in query_lower for term in irrelevant_terms)
        
        # Verificar si menciona específicamente Mawell
        has_mawell_specific = any(term in query_lower for term in mawell_specific_terms)
        
        # Verificar si tiene términos industriales generales
        has_industrial_terms = any(term in query_lower for term in industrial_terms)
        
        # Determinar si está relacionado con Mawell
        is_mawell_related = has_mawell_specific or (has_industrial_terms and not is_clearly_irrelevant and len(query.strip()) > 10)
        
        if not is_mawell_related:
            # Pregunta no relacionada con Mawell
            basic_response = (
                "Lo siento, solo puedo ayudarte con información sobre los equipos y servicios de Mawell. "
                "Puedo proporcionarte información sobre nuestros equipos industriales, servicios técnicos, "
                "sistemas de filtración, bombas, analizadores y más. "
                "¿Puedo ayudarte con algo más?"
            )
        else:
            # Pregunta relacionada con Mawell pero sin contexto específico
            basic_response = (
                "Hola, soy el asistente virtual de Mawell. "
                "No encontré información específica sobre tu consulta en los documentos disponibles. "
                "¿Podrías ser más específico sobre qué equipo o servicio de Mawell te interesa? "
                "Tengo información sobre equipos industriales, servicios técnicos y más. "
                "¿Puedo ayudarte con algo más?"
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
            timeout=100 # Timeout un poco más largo para respuestas elaboradas
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


def _is_mostly_copied_text(response: str, context: str, threshold: float = 0.8) -> bool:
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
    # Limpiar y preparar el contexto, filtrando preguntas
    context_lines = []
    for line in context.split('\n'):
        line_clean = line.strip()
        if (len(line_clean) > 20 and 
            not line_clean.startswith('¿') and 
            not line_clean.endswith('?') and
            not 'cómo puedo' in line_clean.lower() and
            not 'cuánto cuesta' in line_clean.lower() and
            not 'dónde están' in line_clean.lower() and
            not 'qué pasos' in line_clean.lower()):
            context_lines.append(line_clean)
    
    # Si no hay contenido útil después del filtrado
    if not context_lines:
        return _create_fallback_response(query)
    
    # Detectar el tipo de pregunta
    query_lower = query.lower()
    
    # Generar respuesta según el tipo de pregunta
    if any(word in query_lower for word in ['misión', 'visión', 'empresa', 'mawell']):
        return _create_company_response(context_lines)
    elif any(word in query_lower for word in ['equipos', 'equipo', 'maquinas', 'dispositivos']):
        return _create_equipment_response(query, context_lines)
    elif any(word in query_lower for word in ['servicios', 'servicio', 'ofrecen', 'proporcionan']):
        return _create_services_response(context_lines)
    elif any(word in query_lower for word in ['funciona', 'funcionamiento', 'proceso', 'cómo']):
        return _create_process_response(query, context_lines)
    elif any(word in query_lower for word in ['precio', 'costo', 'cotización', 'cuánto']):
        return _create_pricing_response(context_lines)
    else:
        return _create_general_response(context_lines)


def _create_company_response(context_lines: list) -> str:
    """Crea respuesta sobre información de la empresa"""
    # Buscar información sobre la empresa
    company_info = []
    for line in context_lines:
        if any(word in line.lower() for word in ['mawell', 'empresa', 'bolivia', 'líder', 'soluciones']):
            company_info.append(line)
    
    if company_info:
        response = "Sobre Mawell:\n\n"
        response += f"{company_info[0]}"
        if len(company_info) > 1:
            response += f" {company_info[1]}"
    else:
        response = "Mawell es una empresa especializada en equipos y servicios industriales en Bolivia."
    
    response += "\n\n¿Puedo ayudarte con algo más?"
    return response


def _create_equipment_response(query: str, context_lines: list) -> str:
    """Crea respuesta sobre equipos"""
    # Buscar información sobre equipos
    equipment_info = []
    for line in context_lines:
        if any(word in line.lower() for word in ['bomba', 'filtro', 'sistema', 'analizador', 'equipo']):
            equipment_info.append(line)
    
    response = "Sobre nuestros equipos:\n\n"
    
    if equipment_info:
        # Tomar información relevante
        main_info = equipment_info[0]
        response += f"Mawell cuenta con {main_info.lower()}"
        
        if len(equipment_info) > 1:
            additional_info = equipment_info[1]
            response += f" También disponemos de {additional_info.lower()}"
    else:
        response += "Mawell ofrece una amplia gama de equipos industriales especializados."
    
    response += "\n\n¿Puedo ayudarte con algo más?"
    return response


def _create_services_response(context_lines: list) -> str:
    """Crea respuesta sobre servicios"""
    # Buscar información sobre servicios
    services_info = []
    for line in context_lines:
        if any(word in line.lower() for word in ['servicio', 'tratamiento', 'mantenimiento', 'instalación']):
            services_info.append(line)
    
    response = "Nuestros servicios incluyen:\n\n"
    
    if services_info:
        for i, service in enumerate(services_info[:3]):
            response += f"• {service}\n"
    else:
        response += "• Servicios de mantenimiento técnico\n"
        response += "• Tratamiento de agua\n"
        response += "• Instalación de equipos industriales\n"
    
    response += "\n¿Puedo ayudarte con algo más?"
    return response


def _create_process_response(query: str, context_lines: list) -> str:
    """Crea respuesta sobre procesos o funcionamiento"""
    # Buscar información sobre procesos
    process_info = []
    for line in context_lines:
        if any(word in line.lower() for word in ['proceso', 'funciona', 'opera', 'método', 'técnica']):
            process_info.append(line)
    
    response = "Sobre el funcionamiento:\n\n"
    
    if process_info:
        response += f"{process_info[0]}"
        if len(process_info) > 1:
            response += f" {process_info[1]}"
    else:
        response += "Para información específica sobre el funcionamiento, te recomiendo contactar directamente con nuestro equipo técnico."
    
    response += "\n\n¿Puedo ayudarte con algo más?"
    return response


def _create_pricing_response(context_lines: list) -> str:
    """Crea respuesta sobre precios"""
    response = "Sobre precios y cotizaciones:\n\n"
    response += "Para obtener información específica de precios, te recomiendo contactar directamente con nuestro equipo comercial. "
    response += "Ellos podrán proporcionarte una cotización personalizada según tus necesidades específicas."
    response += "\n\n¿Puedo ayudarte con algo más?"
    return response


def _create_general_response(context_lines: list) -> str:
    """Crea respuesta general"""
    if context_lines:
        response = "Basándome en la información disponible:\n\n"
        response += f"{context_lines[0]}"
        if len(context_lines) > 1:
            response += f" {context_lines[1]}"
    else:
        response = "He encontrado información relevante sobre tu consulta en nuestros documentos de Mawell."
    
    response += "\n\n¿Puedo ayudarte con algo más?"
    return response


def _create_fallback_response(query: str) -> str:
    """Crea respuesta de respaldo cuando no hay contexto útil"""
    return ("Lo siento, no encontré información específica sobre tu consulta. "
            "¿Podrías ser más específico sobre qué equipo o servicio de Mawell te interesa? "
            "¿Puedo ayudarte con algo más?")


