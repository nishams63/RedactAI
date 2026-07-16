from services.legal_ai.tools.base import BaseTool
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from models.document_intelligence import DocumentEntity

class EntitySearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "entity_search"

    @property
    def description(self) -> str:
        return "Searches for specific detected PII or custom entities inside the document corpus matching name or type."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "description": "Type of entity, e.g. PERSON, ORGANIZATION, AADHAAR, PAN."},
                "search_query": {"type": "string", "description": "Specific text or regex query to match."}
            },
            "required": ["entity_type"]
        }

    def run(self, arguments: Dict[str, Any], context_metadata: Dict[str, Any]) -> Dict[str, Any]:
        db: Session = context_metadata.get("db")
        if not db:
            return {"error": "Database session not provided in context metadata."}
            
        entity_type = arguments.get("entity_type")
        search_query = arguments.get("search_query")
        
        current_user = context_metadata.get("current_user")
        if not current_user:
            return {"error": "Authenticated user not found in context metadata."}
            
        query = db.query(DocumentEntity).filter(
            DocumentEntity.entity_type == entity_type
        )
        
        if search_query:
            query = query.filter(DocumentEntity.text.like(f"%{search_query}%"))
            
        from models.document import Document
        results = query.join(Document, DocumentEntity.document_id == Document.id).filter(
            Document.organization_id == current_user.organization_id
        ).limit(10).all()
        
        entities_list = []
        for entity in results:
            entities_list.append({
                "id": str(entity.id),
                "text": entity.text,
                "entity_type": entity.entity_type,
                "confidence": entity.confidence,
                "document_id": str(entity.document_id),
                "page_number": entity.page_number
            })
            
        return {
            "entities": entities_list,
            "count": len(entities_list)
        }
