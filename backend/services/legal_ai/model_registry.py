"""AIModel registry wrapper for Level 3 RAG & SLM operations."""
import time
from sqlalchemy.orm import Session
from models.ai_models import AIModel

class LegalModelRegistry:
    def __init__(self, db: Session):
        self.db = db

    def register_model(self, name: str, framework: str, embedding_model: str, vector_store: str, kb_version: str):
        """Register or update an AIModel entry in the database."""
        model = self.db.query(AIModel).filter(AIModel.name == name, AIModel.type == "LEGAL_AI").first()
        params = {
            "framework": framework,
            "embedding_model": embedding_model,
            "vector_store": vector_store,
            "knowledge_base_version": kb_version,
            "last_inference_time_ms": 0.0
        }
        if not model:
            model = AIModel(
                name=name,
                version="1.0.0",
                type="LEGAL_AI",
                status="ACTIVE",
                parameters=params
            )
            self.db.add(model)
        else:
            model.parameters = params
        self.db.commit()
        return model

    def log_inference(self, name: str, start_time: float):
        """Update inference time metadata for a registered model."""
        model = self.db.query(AIModel).filter(AIModel.name == name, AIModel.type == "LEGAL_AI").first()
        if model:
            duration_ms = (time.time() - start_time) * 1000.0
            params = dict(model.parameters or {})
            params["last_inference_time_ms"] = round(duration_ms, 2)
            model.parameters = params
            self.db.commit()

    def get_active_models(self):
        """Retrieve registered legal models."""
        models = self.db.query(AIModel).filter(AIModel.type == "LEGAL_AI", AIModel.status == "ACTIVE").all()
        return [
            {
                "id": str(m.id),
                "name": m.name,
                "version": m.version,
                "framework": m.parameters.get("framework") if m.parameters else "Transformers",
                "embedding_model": m.parameters.get("embedding_model") if m.parameters else "all-MiniLM-L6-v2",
                "vector_store": m.parameters.get("vector_store") if m.parameters else "ChromaDB",
                "knowledge_base_version": m.parameters.get("knowledge_base_version") if m.parameters else "v1.0.0",
                "last_inference_time_ms": m.parameters.get("last_inference_time_ms") if m.parameters else 0.0
            }
            for m in models
        ]
