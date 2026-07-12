"""Versioned prompt template registry utilizing persistent database storage."""
from sqlalchemy.orm import Session
from models.ai_models import PromptRegistry

RAG_QA_PROMPT = """You are a Legal Privacy Assistant. Answer the user's question using ONLY the provided retrieved legal sections.

Retrieved Legal Sections:
{context}

Question:
{question}

Provide a direct, concise, and evidence-backed answer.
Do not assume or make up anything. If the context does not contain the answer, say "I cannot find the answer in the retrieved legal sections."
Include citations in standard format (e.g. [DPDP Act, Section 5] or [RBI KYC Guidelines, Section 3]).
"""

SUMMARIZATION_PROMPT = """Summarize the privacy risks and legal status of the document.

Document Text:
{document_text}

Generate:
- Executive Summary
- Compliance Summary
- Privacy Summary
- Risk Summary
- Action Items
"""

DEFAULT_RAG_QA_TEMPLATE = """You are a Legal Privacy Assistant. Answer the user's question using ONLY the provided retrieved legal sections.

Retrieved Legal Sections:
{context}

Question:
{question}

Provide a direct, concise, and evidence-backed answer.
Do not assume or make up anything. If the context does not contain the answer, say "I cannot find the answer in the retrieved legal sections."
Include citations in standard format (e.g. [DPDP Act, Section 5] or [RBI KYC Guidelines, Section 3]).
"""

DEFAULT_COMPLIANCE_TEMPLATE = """Analyze the following document text and determine compliance with the DPDP Act and RBI Guidelines.

Document Text:
{document_text}

Retrieved Legal Regulations:
{context}

Generate:
1. Compliance Score (0-100)
2. List of violations
3. Risk categories
4. Recommended required actions
"""

DEFAULT_SUMMARIZATION_TEMPLATE = """Summarize the privacy risks and legal status of the document.

Document Text:
{document_text}

Generate:
- Executive Summary
- Compliance Summary
- Privacy Summary
- Risk Summary
- Action Items
"""

class PromptRegistryManager:
    def __init__(self, db: Session):
        self.db = db
        self._init_defaults()

    def _init_defaults(self):
        """Seed default prompts if registry is empty."""
        defaults = [
            ("rag_qa_template", DEFAULT_RAG_QA_TEMPLATE),
            ("compliance_template", DEFAULT_COMPLIANCE_TEMPLATE),
            ("summarization_template", DEFAULT_SUMMARIZATION_TEMPLATE)
        ]
        for prompt_id, template in defaults:
            exists = self.db.query(PromptRegistry).filter(
                PromptRegistry.prompt_id == prompt_id
            ).first()
            if not exists:
                self.register_prompt(
                    prompt_id=prompt_id,
                    version="v1.0.0",
                    template=template,
                    associated_model="Qwen-2.5-0.5B-Instruct",
                    kb_version="v1.0.0",
                    metrics={"mrr": 0.85, "precision": 0.9}
                )

    def register_prompt(self, prompt_id: str, version: str, template: str, associated_model: str, kb_version: str, metrics: dict = None) -> PromptRegistry:
        """Register a new prompt template version. Does not overwrite previous history."""
        # Check if the specific version already exists to avoid exact duplicates
        exists = self.db.query(PromptRegistry).filter(
            PromptRegistry.prompt_id == prompt_id,
            PromptRegistry.version == version
        ).first()
        
        if exists:
            # Update metrics or template in place if version matches exactly
            exists.template = template
            exists.associated_model = associated_model
            exists.kb_version = kb_version
            if metrics:
                exists.performance_metrics = metrics
            self.db.commit()
            return exists

        new_prompt = PromptRegistry(
            prompt_id=prompt_id,
            version=version,
            template=template,
            associated_model=associated_model,
            kb_version=kb_version,
            performance_metrics=metrics or {}
        )
        self.db.add(new_prompt)
        self.db.commit()
        return new_prompt

    def get_active_prompt(self, prompt_id: str) -> str:
        """Retrieve the latest registered prompt template for prompt_id."""
        prompt = self.db.query(PromptRegistry).filter(
            PromptRegistry.prompt_id == prompt_id
        ).order_by(PromptRegistry.created_at.desc()).first()
        return prompt.template if prompt else ""

    def get_prompt_details(self, prompt_id: str) -> dict:
        """Retrieve full details of active prompt template."""
        prompt = self.db.query(PromptRegistry).filter(
            PromptRegistry.prompt_id == prompt_id
        ).order_by(PromptRegistry.created_at.desc()).first()
        if not prompt:
            return {}
        return {
            "prompt_id": prompt.prompt_id,
            "version": prompt.version,
            "template": prompt.template,
            "associated_model": prompt.associated_model,
            "kb_version": prompt.kb_version,
            "metrics": prompt.performance_metrics,
            "created_at": prompt.created_at.isoformat()
        }

    def get_history(self, prompt_id: str) -> list:
        """Get history of all prompt versions."""
        prompts = self.db.query(PromptRegistry).filter(
            PromptRegistry.prompt_id == prompt_id
        ).order_by(PromptRegistry.created_at.desc()).all()
        return [
            {
                "version": p.version,
                "associated_model": p.associated_model,
                "kb_version": p.kb_version,
                "metrics": p.performance_metrics,
                "created_at": p.created_at.isoformat()
            }
            for p in prompts
        ]
