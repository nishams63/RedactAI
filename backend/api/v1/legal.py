"""FastAPI API Router for Level 3 Legal AI & SLM services."""
import uuid
import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user, check_permissions
from models.user import User
from models.document import Document
from models.ai_models import HumanReview
from services.legal_ai.qa import DocumentQAEngine
from services.legal_ai.compliance import ComplianceCheckEngine
from services.legal_ai.reasoning import LegalReasoningEngine
from services.legal_ai.summarizer import LegalDocumentSummarizer
from services.legal_ai.knowledge_base.loader import KnowledgeIngestionPipeline
from services.legal_ai.model_registry import LegalModelRegistry
from services.legal_ai.explanations import PrivacyExplanationEngine
from services.legal_ai.prompts import PromptRegistryManager
from services.legal_ai.evaluator import LegalQAQualityEvaluator

router = APIRouter(prefix="/legal", tags=["Legal AI"])

# --- Request / Response Schemas ---
class LegalChatRequest(BaseModel):
    document_id: str
    question: str
    kb_version: Optional[str] = "v1.0.0"

class HumanReviewCreate(BaseModel):
    document_id: str
    category: str
    ai_recommendation: Dict[str, Any]
    reviewer_decision: str  # APPROVED, OVERRIDDEN
    reviewer_comments: Optional[str] = None
    final_decision: Dict[str, Any]

@router.post("/chat")
def chat_context(request: LegalChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Interactive Q&A for a document utilizing versioned RAG and local SLM."""
    start_time = time.time()
    registry = LegalModelRegistry(db)
    
    qa_engine = DocumentQAEngine(db, kb_version=request.kb_version)
    result = qa_engine.answer_question(request.document_id, request.question)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Register/update SLM metrics in Model Registry
    registry.register_model(
        name=result["reasoning_engine"],
        framework="Transformers (PyTorch)",
        embedding_model="all-MiniLM-L6-v2",
        vector_store="ChromaDB",
        kb_version=request.kb_version
    )
    registry.log_inference(result["reasoning_engine"], start_time)
    
    return result

@router.post("/analyze/{document_id}")
def analyze_document_clauses(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Split document into clauses and perform privacy impact reasoning."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    text = ""
    if hasattr(doc, "pages") and doc.pages:
        text = "\n".join([p.text for p in doc.pages if p.text])
    if not text:
        text = doc.title or "General legal text"

    reasoning_engine = LegalReasoningEngine()
    clauses = reasoning_engine.analyze_document_clauses(text)
    
    # Generate PII explanations
    exp_engine = PrivacyExplanationEngine()
    detected_entities = []
    if hasattr(doc, "detected_entities") and doc.detected_entities:
        entities = [{"entity_type": e.entity_type, "text": e.text} for e in doc.detected_entities]
        detected_entities = exp_engine.explain_all_entities(entities)

    return {
        "document_id": document_id,
        "clauses": clauses,
        "pii_explanations": detected_entities,
        "reasoning_engine": "Rule-Based Privacy Model"
    }

@router.post("/compliance/{document_id}")
def compliance_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Check document text against regulatory policy rules (DPDP, RBI)."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    text = ""
    if hasattr(doc, "pages") and doc.pages:
        text = "\n".join([p.text for p in doc.pages if p.text])
    if not text:
        text = doc.title or "General Contract"

    comp_engine = ComplianceCheckEngine()
    result = comp_engine.evaluate_compliance(text)
    return result

@router.post("/summarize/{document_id}")
def summarize_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Generate risk assessment and executive privacy summaries."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    text = ""
    if hasattr(doc, "pages") and doc.pages:
        text = "\n".join([p.text for p in doc.pages if p.text])
    if not text:
        text = doc.title or "General Contract"

    summarizer = LegalDocumentSummarizer()
    result = summarizer.summarize_document(doc.title, text)
    return result

@router.get("/knowledge")
def get_knowledge_base(version: Optional[str] = "v1.0.0", current_user: User = Depends(get_current_user)):
    """Retrieve all ingested legal sections in knowledge base version."""
    pipeline = KnowledgeIngestionPipeline()
    chunks = pipeline.get_active_chunks(version)
    return {
        "version": version,
        "total_chunks": len(chunks),
        "chunks": chunks
    }

@router.get("/models")
def get_active_models(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List active reasoning and embedding models from registry."""
    registry = LegalModelRegistry(db)
    models = registry.get_active_models()
    return {
        "models": models
    }

@router.post("/review")
def create_human_review(request: HumanReviewCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Submit a reviewer decision and feedback for compliance or sensitivity classification."""
    review = HumanReview(
        document_id=uuid.UUID(request.document_id),
        category=request.category,
        ai_recommendation=request.ai_recommendation,
        reviewer_decision=request.reviewer_decision,
        reviewer_comments=request.reviewer_comments,
        final_decision=request.final_decision,
        reviewed_by=current_user.id
    )
    db.add(review)
    db.commit()
    return {"message": "Human review recorded successfully", "review_id": str(review.id)}


# --- Prompt Versioning & Quality Metrics Schemas ---
class PromptRegisterRequest(BaseModel):
    prompt_id: str
    version: str
    template: str
    associated_model: str
    kb_version: str
    metrics: Optional[Dict[str, Any]] = None


@router.get("/quality")
def get_quality_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve the latest quality metrics, confidence calibration, and historical benchmark runs."""
    evaluator = LegalQAQualityEvaluator(db)
    history = evaluator.get_run_history()
    
    # If history is empty, run an initial benchmark run to establish a baseline
    if not history:
        evaluator.run_benchmark(use_slm=False)
        history = evaluator.get_run_history()
        
    return {
        "latest": history[0] if history else {},
        "history": history
    }


@router.post("/benchmark")
def run_quality_benchmark(use_slm: bool = Query(default=False), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Trigger a manual validation benchmark run over the 50 legal QA question suite."""
    evaluator = LegalQAQualityEvaluator(db)
    result = evaluator.run_benchmark(use_slm=use_slm)
    return result


@router.get("/prompts")
def get_versioned_prompts(prompt_id: str = "rag_qa_template", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve versioned prompts registry, active template, and performance metric history."""
    prompt_manager = PromptRegistryManager(db)
    active = prompt_manager.get_prompt_details(prompt_id)
    history = prompt_manager.get_history(prompt_id)
    return {
        "active": active,
        "history": history
    }


@router.post("/prompts/register")
def register_versioned_prompt(request: PromptRegisterRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Register a new RAG prompt template version without overwriting historical versions."""
    prompt_manager = PromptRegistryManager(db)
    prompt = prompt_manager.register_prompt(
        prompt_id=request.prompt_id,
        version=request.version,
        template=request.template,
        associated_model=request.associated_model,
        kb_version=request.kb_version,
        metrics=request.metrics
    )
    return {
        "message": f"Prompt version '{request.version}' registered successfully",
        "prompt_id": prompt.prompt_id,
        "version": prompt.version
    }


# --- Performance Optimization & Queue Monitoring Endpoints ---
@router.get("/performance")
def get_performance_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve cache hit rates, active processing queue parameters, and CPU/RAM/API latencies."""
    from services.legal_ai.cache_manager import CacheManager
    from services.legal_ai.queue_monitor import QueueMonitor
    import psutil
    
    # 1. Cache statistics
    cache_stats = CacheManager().get_stats()
    
    # 2. Queue metrics
    queue_stats = QueueMonitor(db).get_metrics()
    
    # 3. System resources
    system_resources = {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent
    }
    
    # 4. API latencies from PerformanceProfiles
    from models.ai_models import PerformanceProfile
    recent_profiles = db.query(PerformanceProfile).order_by(PerformanceProfile.created_at.desc()).limit(100).all()
    
    latencies = [p.total_latency for p in recent_profiles]
    p50 = float(round(sum(latencies) / len(latencies), 2)) if latencies else 0.0
    p95 = float(round(max(latencies), 2)) if latencies else 0.0
    
    # Get stage timings breakdown for recent jobs
    stage_breakdown = {}
    task_profiles = [p for p in recent_profiles if p.method == "TASK"]
    if task_profiles:
        keys = ["validation", "layout", "ocr", "pii_ner", "classification"]
        for k in keys:
            vals = [p.stages.get(k, 0.0) for p in task_profiles if p.stages and k in p.stages]
            stage_breakdown[k] = round(sum(vals) / len(vals), 2) if vals else 0.0
    
    return {
        "cache": cache_stats,
        "queue": queue_stats,
        "system": system_resources,
        "api_p50_ms": p50,
        "api_p95_ms": p95,
        "stage_latencies_ms": stage_breakdown
    }


@router.post("/performance/benchmark")
def trigger_performance_load_test(concurrency: int = Query(default=10), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Trigger parallel load test execution and perform regression metrics checks."""
    from services.legal_ai.profiler import PerformanceProfiler
    profiler = PerformanceProfiler(db)
    benchmark = profiler.run_load_test(concurrency=concurrency)
    return {
        "message": f"Load test with concurrency {concurrency} complete.",
        "benchmark_id": str(benchmark.id),
        "throughput_req_sec": benchmark.throughput,
        "avg_latency_ms": benchmark.avg_latency,
        "peak_latency_ms": benchmark.peak_latency,
        "failure_rate": benchmark.failure_rate,
        "cpu_util": benchmark.cpu_util,
        "ram_util": benchmark.ram_util,
        "improvements": benchmark.improvement_report,
        "regressions": benchmark.regression_report
    }


@router.get("/performance/benchmarks")
def get_historical_benchmarks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Retrieve list of historical benchmark runs."""
    from models.ai_models import PerformanceBenchmark
    runs = db.query(PerformanceBenchmark).order_by(PerformanceBenchmark.created_at.desc()).limit(20).all()
    return {
        "history": [
            {
                "id": str(r.id),
                "created_at": r.created_at,
                "concurrency": r.concurrency,
                "throughput": r.throughput,
                "avg_latency": r.avg_latency,
                "peak_latency": r.peak_latency,
                "failure_rate": r.failure_rate,
                "cpu_util": r.cpu_util,
                "ram_util": r.ram_util,
                "improvements": r.improvement_report,
                "regressions": r.regression_report
            } for r in runs
        ]
    }
