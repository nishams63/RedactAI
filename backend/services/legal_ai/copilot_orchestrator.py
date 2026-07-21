import os
import sys

# Ensure parent backend directory is in sys.path for direct debugger execution
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import uuid
import time
import json
from typing import Dict, Any, List, Generator
from sqlalchemy.orm import Session
from models.copilot import CopilotConversation, CopilotMessage, CopilotWorkspaceItem
from models.document import Document
from services.legal_ai.memory import CopilotMemoryManager
from services.legal_ai.prompt_manager import PromptManager
from services.legal_ai.agents.coordinator import AgentCoordinator

class CopilotOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_manager = PromptManager()
        self.coordinator = AgentCoordinator()

    def chat(
        self,
        user_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None = None,
        document_ids: List[uuid.UUID] | None = None,
        filters: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Synchronous chat endpoint (returns standard REST JSON)."""
        start_time = time.time()
        
        # 1. Prompt Injection check
        if self.prompt_manager.scan_for_prompt_injection(message):
            return {
                "answer": "Safety block: The request contains potential system prompt override instructions. Execution refused.",
                "confidence_score": 0.0,
                "citations": [],
                "explainability": {"reasoning_summary": "Prompt injection detected."}
            }

        # 2. Get or Create Conversation Session
        if not conversation_id:
            conversation = CopilotConversation(
                user_id=user_id,
                title="New Consultation",
                document_ids=[str(d) for d in document_ids] if document_ids else []
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            conversation_id = conversation.id
        else:
            conversation = self.db.query(CopilotConversation).filter(
                CopilotConversation.id == conversation_id,
                CopilotConversation.user_id == user_id
            ).first()
            if not conversation:
                raise ValueError("Conversation not found or unauthorized.")
                
            # If doc ids passed, update document set
            if document_ids:
                conversation.document_ids = list(set((conversation.document_ids or []) + [str(d) for d in document_ids]))
                self.db.commit()

        # 3. Retrieve memory state
        memory = CopilotMemoryManager.get_or_create_memory(user_id, self.db)
        history = CopilotMemoryManager.get_conversation_history(conversation_id, self.db)
        
        # 4. Save User Message
        CopilotMemoryManager.add_message(conversation_id, "user", message, None, None, self.db)

        # 5. Execute Coordinator
        doc_strings = conversation.document_ids or []
        
        from models.user import User
        current_user = self.db.query(User).filter(User.id == user_id).first()
        metadata_ctx = {"db": self.db, "current_user": current_user}

        events_generator = self.coordinator.route_and_execute(
            query=message,
            history=history,
            document_ids=doc_strings,
            preferences=memory.preferences or {},
            context_metadata=metadata_ctx
        )
        
        final_data = {}
        for event in events_generator:
            if event["event"] == "completed":
                final_data = event["data"]

        # 6. Save Assistant Response
        total_latency = (time.time() - start_time) * 1000.0
        explainability = final_data.get("explainability", {})
        explainability["total_latency_ms"] = round(total_latency, 2)
        
        CopilotMemoryManager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_data.get("answer", "I cannot process your request."),
            citations=final_data.get("citations"),
            explainability=explainability,
            db=self.db
        )

        # 7. Update short term context entities
        CopilotMemoryManager.update_short_term_context(user_id, {"last_query": message}, self.db)

        # 8. Background summarize titling if history is small
        if len(history) <= 2:
            self._trigger_background_summarize(conversation_id)

        return {
            "conversation_id": str(conversation_id),
            "answer": final_data.get("answer"),
            "citations": final_data.get("citations"),
            "explainability": explainability,
            "needs_review": final_data.get("needs_review", False)
        }

    def stream_chat(
        self,
        user_id: uuid.UUID,
        message: str,
        conversation_id: uuid.UUID | None = None,
        document_ids: List[uuid.UUID] | None = None,
        filters: Dict[str, Any] | None = None
    ) -> Generator[str, None, None]:
        """Asynchronous stream endpoint (SSE generator yielding JSON chunks)."""
        start_time = time.time()
        
        # 1. Prompt Injection check
        if self.prompt_manager.scan_for_prompt_injection(message):
            yield f"event: error\ndata: {json.dumps({'detail': 'Safety block: Prompt injection detected.'})}\n\n"
            return

        # 2. Get or Create Session
        if not conversation_id:
            conversation = CopilotConversation(
                user_id=user_id,
                title="New Consultation",
                document_ids=[str(d) for d in document_ids] if document_ids else []
            )
            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)
            conversation_id = conversation.id
        else:
            conversation = self.db.query(CopilotConversation).filter(
                CopilotConversation.id == conversation_id,
                CopilotConversation.user_id == user_id
            ).first()
            if not conversation:
                yield f"event: error\ndata: {json.dumps({'detail': 'Conversation not found or unauthorized.'})}\n\n"
                return

        # 3. Retrieve memory state
        memory = CopilotMemoryManager.get_or_create_memory(user_id, self.db)
        history = CopilotMemoryManager.get_conversation_history(conversation_id, self.db)

        # 4. Save User Message
        CopilotMemoryManager.add_message(conversation_id, "user", message, None, None, self.db)

        # 5. Execute Coordinator Stream
        doc_strings = conversation.document_ids or []
        
        from models.user import User
        current_user = self.db.query(User).filter(User.id == user_id).first()
        metadata_ctx = {"db": self.db, "current_user": current_user}

        events_generator = self.coordinator.route_and_execute(
            query=message,
            history=history,
            document_ids=doc_strings,
            preferences=memory.preferences or {},
            context_metadata=metadata_ctx
        )
        
        final_data = {}
        for event in events_generator:
            event_name = event["event"]
            event_data = event["data"]
            
            if event_name == "completed":
                final_data = event_data
            
            yield f"event: {event_name}\ndata: {json.dumps(event_data)}\n\n"

        # 6. Save Assistant Response
        total_latency = (time.time() - start_time) * 1000.0
        explainability = final_data.get("explainability", {})
        explainability["total_latency_ms"] = round(total_latency, 2)
        
        CopilotMemoryManager.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_data.get("answer", "I cannot process your request."),
            citations=final_data.get("citations"),
            explainability=explainability,
            db=self.db
        )

        # 7. Update short term context entities
        CopilotMemoryManager.update_short_term_context(user_id, {"last_query": message}, self.db)

        # 8. Background summarize
        if len(history) <= 2:
            self._trigger_background_summarize(conversation_id)

        yield f"event: end\ndata: {json.dumps({'conversation_id': str(conversation_id)})}\n\n"

    def _trigger_background_summarize(self, conversation_id: uuid.UUID):
        """Generates dynamic titling and brief summary using conversation history."""
        try:
            history = CopilotMemoryManager.get_conversation_history(conversation_id, self.db)
            if not history:
                return
                
            summary_prompt = self.prompt_manager.render("summary.jinja", {"history": history})
            
            from services.legal_ai.slm import LocalSLMInferenceEngine
            slm = LocalSLMInferenceEngine()
            slm_res = slm.generate_response(summary_prompt, "Generate title and summary JSON.")
            text = slm_res["text"]
            
            import re
            json_match = re.search(r"\{.*?\}", text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                title = data.get("title", "Legal Consultation")
                summary = data.get("summary", "")
            else:
                first_query = history[0]["content"] if history else "Legal Consultation"
                title = first_query[:30] + "..." if len(first_query) > 30 else first_query
                summary = "Conversation about: " + first_query
                
            conversation = self.db.query(CopilotConversation).filter(CopilotConversation.id == conversation_id).first()
            if conversation:
                conversation.title = title
                conversation.summary = summary
                self.db.commit()
        except Exception as e:
            print(f"Failed to auto-generate conversation title/summary: {e}")
