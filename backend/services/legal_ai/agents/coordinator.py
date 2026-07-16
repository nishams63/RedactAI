from services.legal_ai.agents.retrieval import RetrievalAgent
from services.legal_ai.agents.compliance import ComplianceAgent
from services.legal_ai.agents.risk import RiskAgent
from services.legal_ai.agents.citation import CitationAgent
from services.legal_ai.agents.review import ReviewAgent
from services.legal_ai.agents.summary import SummaryAgent
from typing import List, Dict, Any, Generator

class AgentCoordinator:
    """Coordinates and routes queries dynamically across decentralized sub-agents."""
    
    def __init__(self):
        self.agents = {
            "retrieval": RetrievalAgent(),
            "compliance": ComplianceAgent(),
            "risk": RiskAgent(),
            "citation": CitationAgent(),
            "review": ReviewAgent(),
            "summary": SummaryAgent()
        }

    def route_and_execute(
        self,
        query: str,
        history: List[Dict[str, Any]],
        document_ids: List[str],
        preferences: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> Generator[Dict[str, Any], None, None]:
        """Routes task and executes agents sequentially/conditionally, yielding events."""
        db = context_metadata.get("db")
        
        # 1. Intent Classification
        query_lower = query.lower()
        target_agent = "general"
        if "comply" in query_lower or "compliance" in query_lower or "dpdp" in query_lower or "rbi" in query_lower:
            target_agent = "compliance"
        elif "risk" in query_lower or "liability" in query_lower or "exposure" in query_lower:
            target_agent = "risk"
        elif "summarize" in query_lower or "summary" in query_lower or "executive summary" in query_lower:
            target_agent = "summary"
            
        yield {"event": "progress", "data": {"step": "intent_resolved", "agent": target_agent}}

        # 2. Context Retrieval
        context_chunks = []
        if document_ids:
            for event in self.agents["retrieval"].process_task(query, history, document_ids, preferences, context_metadata):
                if event.get("event") == "retrieved_context":
                    context_chunks = event["data"]["context_chunks"]
                yield event
        
        context_metadata["context_chunks"] = context_chunks

        # 3. Target Task Execution
        agent_result = None
        if target_agent == "compliance":
            for event in self.agents["compliance"].process_task(query, history, document_ids, preferences, context_metadata):
                if event.get("event") == "compliance_report":
                    agent_result = {
                        "answer": event["data"]["audit_report"],
                        "confidence_score": 0.8,
                        "citations": [],
                        "explainability": {
                            "reasoning_summary": "Evaluated compliance mapping rules.",
                            "model_used": event["data"]["model_used"],
                            "inference_time_ms": event["data"]["inference_time_ms"],
                            "retrieved_chunk_ids": [c.get("chunk_id") for c in context_chunks if c.get("chunk_id")],
                            "retrieved_document_ids": list(set([str(c.get("metadata", {}).get("document_id")) for c in context_chunks if c.get("metadata", {}).get("document_id")]))
                        }
                    }
                yield event
        elif target_agent == "risk":
            for event in self.agents["risk"].process_task(query, history, document_ids, preferences, context_metadata):
                if event.get("event") == "risk_report":
                    agent_result = {
                        "answer": event["data"]["risk_analysis"],
                        "confidence_score": 0.8,
                        "citations": [],
                        "explainability": {
                            "reasoning_summary": "Extracted contract exposure details.",
                            "model_used": event["data"]["model_used"],
                            "inference_time_ms": event["data"]["inference_time_ms"],
                            "retrieved_chunk_ids": [c.get("chunk_id") for c in context_chunks if c.get("chunk_id")],
                            "retrieved_document_ids": list(set([str(c.get("metadata", {}).get("document_id")) for c in context_chunks if c.get("metadata", {}).get("document_id")]))
                        }
                    }
                yield event
        elif target_agent == "summary":
            for event in self.agents["summary"].process_task(query, history, document_ids, preferences, context_metadata):
                if event.get("event") == "summary_report":
                    agent_result = {
                        "answer": event["data"]["summary"],
                        "confidence_score": 0.9,
                        "citations": [],
                        "explainability": {
                            "reasoning_summary": "Generated document summary points.",
                            "model_used": event["data"]["model_used"],
                            "inference_time_ms": event["data"]["inference_time_ms"],
                            "retrieved_chunk_ids": [c.get("chunk_id") for c in context_chunks if c.get("chunk_id")],
                            "retrieved_document_ids": list(set([str(c.get("metadata", {}).get("document_id")) for c in context_chunks if c.get("metadata", {}).get("document_id")]))
                        }
                    }
                yield event
        
        # 4. Generate grounded answer if not resolved by a specific tool
        if not agent_result:
            from services.legal_ai.answer_generator import LegalAnswerGenerator
            generator = LegalAnswerGenerator(db)
            
            yield {"event": "progress", "data": {"step": "generation_started"}}
            gen_res = generator.generate_grounded_answer(query, context_chunks)
            agent_result = {
                "answer": gen_res["answer"],
                "confidence_score": gen_res["confidence_score"],
                "citations": gen_res["citations"],
                "explainability": {
                    "reasoning_summary": gen_res.get("confidence_reason"),
                    "model_used": gen_res.get("reasoning_engine"),
                    "inference_time_ms": gen_res.get("inference_time_ms"),
                    "retrieved_chunk_ids": [str(c.get("chunk_id")) for c in context_chunks if c.get("chunk_id")],
                    "retrieved_document_ids": list(set([str(c.get("metadata", {}).get("document_id")) for c in context_chunks if c.get("metadata", {}).get("document_id")]))
                }
            }
            yield {"event": "progress", "data": {"step": "generation_completed"}}

        if agent_result and "explainability" in agent_result:
            agent_result["explainability"]["graph_traversal_paths"] = context_metadata.get("graph_traversal_paths", [])

        # 5. Citation Verification
        context_metadata["answer_text"] = agent_result.get("answer", "")
        citations_verified = None
        for event in self.agents["citation"].process_task(query, history, document_ids, preferences, context_metadata):
            if event.get("event") == "citations_verified":
                citations_verified = event["data"]
            yield event

        if citations_verified:
            # Re-map valid citations
            agent_result["citations"] = citations_verified["citations"]
            # Calibrate confidence using verified citations score
            agent_result["confidence_score"] = citations_verified["citation_correctness"]

        # 6. Human Review Triggering
        context_metadata["confidence_score"] = agent_result.get("confidence_score", 1.0)
        review_status = None
        for event in self.agents["review"].process_task(query, history, document_ids, preferences, context_metadata):
            if event.get("event") == "review_status":
                review_status = event["data"]
            yield event

        if review_status:
            agent_result["needs_review"] = review_status["needs_review"]

        yield {"event": "completed", "data": agent_result}
