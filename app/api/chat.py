# app/api/chat.py

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from app.models import Conversation, Message
from app.schemas.chat import ChatRequest
from app.schemas.message import MessageResponse
from app.schemas.conversation import ConversationSummary, ConversationCreate, ConversationResponse
from sqlalchemy.orm import Session
from app.config import SessionLocal
import requests

router = APIRouter(prefix="/chat", tags=["chat"])

# Dependency para DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/start", response_model=ConversationResponse)
def start_conversation(data: ConversationCreate, db: Session = Depends(get_db)):
    new_convo = Conversation(title=data.title)
    db.add(new_convo)
    db.commit()
    db.refresh(new_convo)
    return new_convo

@router.post("/send", response_model=MessageResponse)
def send_question(data: ChatRequest, db: Session = Depends(get_db)):
    # Recuperar historial para el modelo
    messages = db.query(Message).filter(Message.conversation_id == data.conversation_id).order_by(Message.timestamp).all()

    # Construir historial como prompt
    history = ""
    for msg in messages:
        history += f"Usuario: {msg.question}\nAsistente: {msg.answer}\n"
    history += f"Usuario: {data.question}\n"

    # Generar respuesta usando IA (con historial)
    full_prompt = f"Responde en español usando este historial:\n\n{history}"
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "mistral",
        "prompt": full_prompt,
        "stream": False
    })
    answer = response.json().get("response", "No se pudo generar respuesta.")

    # Guardar el mensaje
    new_msg = Message(
        conversation_id=data.conversation_id,
        question=data.question,
        answer=answer
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    return new_msg

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.timestamp).all()

    return messages

@router.get("/my-conversations", response_model=list[ConversationSummary])
def list_user_conversations(db: Session = Depends(get_db)):
    conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    return conversations

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    db.delete(conversation)
    db.commit()
