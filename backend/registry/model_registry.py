import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from models.ai_models import AIModel

class ModelRegistryManager:
    """
    Manages dynamic model registration, deployment status toggles, and rollbacks.
    """
    def __init__(self, db: Session):
        self.db = db

    def register_model(
        self,
        name: str,
        version: str,
        model_type: str = "REDACTION",
        parameters: dict = None,
        status: str = "Active"
    ) -> AIModel:
        """Registers a new model version in the database registry."""
        if status == "Active":
            # Set other active models of the same type/name to Deprecated
            self.db.query(AIModel).filter(
                AIModel.name == name,
                AIModel.type == model_type,
                AIModel.status == "Active"
            ).update({"status": "Deprecated"})
        
        new_model = AIModel(
            name=name,
            version=version,
            type=model_type,
            status=status,
            parameters=parameters or {}
        )
        self.db.add(new_model)
        self.db.commit()
        return new_model

    def deploy_model(self, model_id: uuid.UUID) -> bool:
        """Deploys a specific model version by setting it to Active and others to Deprecated."""
        target = self.db.query(AIModel).filter(AIModel.id == model_id).first()
        if not target:
            return False
            
        # Transition target status to Deploying first
        target.status = "Deploying"
        self.db.commit()
        
        # Set all active models of the same type/name to Deprecated
        self.db.query(AIModel).filter(
            AIModel.type == target.type,
            AIModel.name == target.name,
            AIModel.id != model_id,
            AIModel.status == "Active"
        ).update({"status": "Deprecated"})
        
        target.status = "Active"
        self.db.commit()
        return True

    def rollback_model(self, name: str, fallback_version: str) -> bool:
        """Rolls back to a specific version of a model by name."""
        target = self.db.query(AIModel).filter(
            AIModel.name == name,
            AIModel.version == fallback_version
        ).first()
        
        if not target:
            return False
            
        # Set all active models of the same name to Deprecated
        self.db.query(AIModel).filter(
            AIModel.name == name,
            AIModel.status == "Active"
        ).update({"status": "Deprecated"})
        
        target.status = "Active"
        self.db.commit()
        return True

    def get_active_model(self, name: str) -> Optional[AIModel]:
        """Gets the currently active model version of a given name."""
        return self.db.query(AIModel).filter(
            AIModel.name == name,
            AIModel.status == "Active"
        ).first()
        
    def list_models(self) -> List[AIModel]:
        """Lists all registered models in the registry."""
        return self.db.query(AIModel).order_by(AIModel.created_at.desc()).all()
