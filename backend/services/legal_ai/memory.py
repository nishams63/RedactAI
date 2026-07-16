from sqlalchemy.orm import Session
from models.copilot import CopilotMemory, CopilotConversation, CopilotMessage
import uuid
from typing import Dict, Any, List

class CopilotMemoryManager:
    """Manages short-term context, user preferences, and message history storage."""
    
    @staticmethod
    def get_or_create_memory(user_id: uuid.UUID, db: Session) -> CopilotMemory:
        memory = db.query(CopilotMemory).filter(CopilotMemory.user_id == user_id).first()
        if not memory:
            memory = CopilotMemory(
                user_id=user_id,
                short_term_context={},
                preferences={"regulations": "DPDP Act 2023", "tone": "professional"}
            )
            db.add(memory)
            db.commit()
            db.refresh(memory)
        return memory

    @staticmethod
    def update_preferences(user_id: uuid.UUID, preferences: Dict[str, Any], db: Session) -> CopilotMemory:
        memory = CopilotMemoryManager.get_or_create_memory(user_id, db)
        current_prefs = dict(memory.preferences or {})
        current_prefs.update(preferences)
        memory.preferences = current_prefs
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def update_short_term_context(user_id: uuid.UUID, context_updates: Dict[str, Any], db: Session) -> CopilotMemory:
        memory = CopilotMemoryManager.get_or_create_memory(user_id, db)
        current_context = dict(memory.short_term_context or {})
        current_context.update(context_updates)
        memory.short_term_context = current_context
        db.commit()
        db.refresh(memory)
        return memory

    @staticmethod
    def get_conversation_history(conversation_id: uuid.UUID, db: Session) -> List[Dict[str, Any]]:
        messages = db.query(CopilotMessage).filter(
            CopilotMessage.conversation_id == conversation_id
        ).order_by(CopilotMessage.created_at.asc()).all()
        
        return [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "explainability": m.explainability,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ]

    @staticmethod
    def add_message(
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: List[Dict[str, Any]] | None,
        explainability: Dict[str, Any] | None,
        db: Session
    ) -> CopilotMessage:
        message = CopilotMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
            explainability=explainability
        )
        db.add(message)
        
        conversation = db.query(CopilotConversation).filter(CopilotConversation.id == conversation_id).first()
        if conversation:
            from sqlalchemy.sql import func
            conversation.updated_at = func.now()
            
        db.commit()
        db.refresh(message)
        return message
