import logging
import uuid
import os
import time
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from models.document import Document
from models.document_intelligence import DocumentMetadata, DocumentPage, DocumentBlock, DocumentEntity, ProcessingJob
from models.ai_models import ProcessingLog
from services.ai.registry import ai_registry
from storage.s3 import storage_client

logger = logging.getLogger("redactai.ai.orchestrator")

# ─── Feature Flags ────────────────────────────────────────────────────
ENABLE_LAYOUT_ANALYSIS = os.getenv("ENABLE_LAYOUT_ANALYSIS", "True").lower() == "true"
ENABLE_PII_DETECTION = os.getenv("ENABLE_PII_DETECTION", "True").lower() == "true"
ENABLE_NER_DETECTION = os.getenv("ENABLE_NER_DETECTION", "True").lower() == "true"

# Risk classification mapping
RISK_MAPPING = {
    # Critical risk
    "AADHAAR": "CRITICAL",
    "PASSPORT": "CRITICAL",
    "BANK_ACCOUNT": "CRITICAL",
    # High risk
    "PAN": "HIGH",
    "DRIVING_LICENSE": "HIGH",
    "VOTER_ID": "HIGH",
    "IFSC": "HIGH",
    "CREDIT_CARD": "HIGH",
    "UPI_ID": "HIGH",
    # Medium risk
    "PHONE": "MEDIUM",
    "EMAIL": "MEDIUM",
    "ADDRESS": "MEDIUM",
    "PIN_CODE": "MEDIUM",
    "MONEY": "MEDIUM",
    "LAW": "MEDIUM",
    "COURT": "MEDIUM",
    "JUDGE": "MEDIUM",
    "CASE_NUMBER": "MEDIUM",
    # Low risk
    "PERSON": "LOW",
    "ORGANIZATION": "LOW",
    "LOCATION": "LOW",
    "DATE": "LOW",
}

class AIOrchestrator:
    """Orchestrates the 10-stage Document Intelligence Pipeline."""

    def __init__(self, db: Session):
        self.db = db

    def _log_stage(self, doc_id: uuid.UUID, stage: str, message: str, level: str = "INFO"):
        """Save a processing milestone log into the database."""
        log = ProcessingLog(
            id=uuid.uuid4(),
            document_id=doc_id,
            stage=stage,
            log_level=level,
            message=message
        )
        self.db.add(log)
        self.db.commit()
        logger.info(f"[{stage}] Document {doc_id}: {message}")

    def _update_job(self, job: ProcessingJob, status: str, progress: int, error_message: str = None):
        """Update active job state in database."""
        job.status = status
        job.progress = progress
        if error_message:
            job.error_message = error_message
        self.db.commit()

    def process_document(self, document_id: uuid.UUID, job_id: uuid.UUID) -> Dict[str, Any]:
        """Runs the complete Document Intelligence State Machine on the uploaded file."""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        job = self.db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            # Create a fallback tracking job if missing
            job = ProcessingJob(
                id=uuid.uuid4(),
                document_id=document_id,
                job_type="FULL_PIPELINE",
                status="PENDING",
                progress=0
            )
            self.db.add(job)
            self.db.commit()

        try:
            stage_timings = {}
            total_start = time.time()
            v_start = time.time()
            # ─────────────────────────────────────────────────────────
            # STAGE 1: File Validation (VALIDATING)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "VALIDATING", 10)
            self._log_stage(doc.id, "VALIDATING", "File validation check started.")
            
            # Fetch file bytes from storage client
            file_bytes = storage_client.download_file(doc.storage_path)
            if not file_bytes:
                raise ValueError("Failed to retrieve document binary from storage client.")
            
            allowed_exts = [".pdf", ".docx", ".png", ".jpg", ".jpeg"]
            ext = os.path.splitext(doc.original_filename)[1].lower()
            if ext not in allowed_exts:
                raise ValueError(f"Unsupported file extension {ext}")
            
            self._log_stage(doc.id, "VALIDATING", "File successfully validated against whitelist.")

            # ─────────────────────────────────────────────────────────
            # STAGE 2: File Type Detection (DETECTING)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "DETECTING", 20)
            self._log_stage(doc.id, "DETECTING", "Detecting file layout type.")
            
            file_type = "Image"
            if ext == ".docx":
                file_type = "Word Document"
            elif ext == ".pdf":
                # Detect if digital or scanned
                try:
                    import fitz
                    pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                except Exception as pdf_err:
                    logger.error(f"Corrupted PDF or invalid stream: {pdf_err}")
                    raise ValueError(f"Failed to parse PDF document. It may be corrupted. Error: {pdf_err}")
                
                try:
                    if pdf_doc.is_encrypted:
                        raise ValueError("PDF is password protected or encrypted.")
                    has_text = False
                    for p in pdf_doc:
                        if p.get_text().strip():
                            has_text = True
                            break
                    file_type = "Digital PDF" if has_text else "Scanned PDF"
                    pdf_doc.close()
                except Exception as e:
                    pdf_doc.close()
                    logger.error(f"Error checking PDF layout: {e}")
                    raise e

            self._log_stage(doc.id, "DETECTING", f"File type classified as: {file_type}")

            # ─────────────────────────────────────────────────────────
            # STAGE 3 & 4: Metadata & Language Detection (EXTRACTING)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "EXTRACTING", 30)
            self._log_stage(doc.id, "EXTRACTING", "Extracting document properties and metadata.")

            # PDF properties
            author = None
            producer = None
            created_date = None
            modified_date = None
            page_count = 1
            encryption_status = "UNENCRYPTED"
            signature_status = "UNSIGNED"

            if file_type in ["Digital PDF", "Scanned PDF"]:
                try:
                    import fitz
                    pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                    page_count = len(pdf_doc)
                    metadata = pdf_doc.metadata or {}
                    author = metadata.get("author")
                    producer = metadata.get("producer")
                    encryption_status = "ENCRYPTED" if pdf_doc.is_encrypted else "UNENCRYPTED"
                    
                    # Parse signature signs
                    for page in pdf_doc:
                        if page.search_for("signature") or page.search_for("signed"):
                            signature_status = "SIGNED"
                            break
                    pdf_doc.close()
                except Exception as meta_err:
                    logger.warning(f"Metadata read error: {meta_err}")

            stage_timings["validation"] = round((time.time() - v_start) * 1000, 2)
            l_start = time.time()
            # ─────────────────────────────────────────────────────────
            # STAGE 5: Layout Analysis (ANALYZING)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "ANALYZING", 40)
            self._log_stage(doc.id, "ANALYZING", "Layout segmentation analysis started.")
            
            layout_blocks = []
            if ENABLE_LAYOUT_ANALYSIS:
                layout_prov = ai_registry.get_layout_provider()
                layout_blocks = layout_prov.analyze_layout(file_bytes, doc.mime_type)
                
            self._log_stage(doc.id, "ANALYZING", f"Layout analysis complete. Extracted {len(layout_blocks)} structural blocks.")

            stage_timings["layout"] = round((time.time() - l_start) * 1000, 2)
            o_start = time.time()
            # ─────────────────────────────────────────────────────────
            # STAGE 6: Text Extraction (OCR vs. PyMuPDF)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "EXTRACTING", 50)
            self._log_stage(doc.id, "EXTRACTING", f"Extracting raw text contents using {file_type} extractor.")

            ocr_prov = ai_registry.get_ocr_provider(file_type)
            ocr_result = ocr_prov.extract_text(file_bytes, ext.replace(".", ""))
            
            # Save raw OCR pages JSON into MinIO / storage client
            ocr_key = f"ocr/{doc.id}/{doc.id}_ocr.json"
            import json
            storage_client.upload_file(
                file_content=json.dumps(ocr_result).encode("utf-8"),
                document_id=str(doc.id),
                filename=f"{doc.id}_ocr.json",
                content_type="application/json",
                prefix="ocr"
            )

            # Store plain text into DB document_pages table
            full_text = ""
            for p_idx, page_data in enumerate(ocr_result["pages"]):
                p_num = page_data["page_number"]
                p_text = page_data["text"]
                full_text += p_text + "\n"
                
                db_page = DocumentPage(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    page_number=p_num,
                    text=p_text
                )
                self.db.add(db_page)

            # Detect language of full extracted text
            lang_prov = ai_registry.get_language_provider()
            detected_lang = lang_prov.detect_language(full_text[:5000])
            self._log_stage(doc.id, "EXTRACTING", f"Language detected: {detected_lang}")

            # Save layout blocks to DB
            for idx, block in enumerate(layout_blocks):
                db_block = DocumentBlock(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    page_number=block["page_number"],
                    block_type=block["block_type"],
                    text=block["text"],
                    coordinates=block["coordinates"],
                    reading_order=block["reading_order"]
                )
                self.db.add(db_block)

            # Save document metadata
            db_metadata = DocumentMetadata(
                id=uuid.uuid4(),
                document_id=doc.id,
                file_size=len(file_bytes),
                mime_type=doc.mime_type,
                file_type=file_type,
                page_count=page_count,
                author=author,
                producer=producer,
                encryption_status=encryption_status,
                signature_status=signature_status,
                language=detected_lang
            )
            self.db.add(db_metadata)
            self.db.commit()

            self._log_stage(doc.id, "EXTRACTING", f"Text extraction complete. Total pages saved: {page_count}.")

            stage_timings["ocr"] = round((time.time() - o_start) * 1000, 2)
            p_start = time.time()
            # ─────────────────────────────────────────────────────────
            # STAGE 7 & 8: PII & NER Detection (ANALYZING)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "ANALYZING", 75)
            self._log_stage(doc.id, "ANALYZING", "Entity detection & scan started.")

            detected_entities = []

            # 7. Microsoft Presidio PII Scanner
            if ENABLE_PII_DETECTION:
                self._log_stage(doc.id, "ANALYZING", "PII analysis scan running.")
                pii_prov = ai_registry.get_pii_provider()
                # Analyze PII page by page to get proper page offsets
                for page_data in ocr_result["pages"]:
                    p_num = page_data["page_number"]
                    p_text = page_data["text"]
                    pii_results = pii_prov.detect_pii(p_text)
                    for ent in pii_results:
                        ent["page_number"] = p_num
                        detected_entities.append(ent)
                self._log_stage(doc.id, "ANALYZING", "PII analysis scan completed.")

            # 8. spaCy NER Scanner
            if ENABLE_NER_DETECTION:
                self._log_stage(doc.id, "ANALYZING", "NER analysis scan running.")
                ner_prov = ai_registry.get_ner_provider()
                for page_data in ocr_result["pages"]:
                    p_num = page_data["page_number"]
                    p_text = page_data["text"]
                    ner_results = ner_prov.extract_entities(p_text)
                    for ent in ner_results:
                        # Avoid duplicates between PII and NER (e.g. EMAIL or PHONE flagged as general ORG)
                        duplicate = any(
                            e["page_number"] == p_num and
                            e["start_char"] == ent["start_char"] and
                            e["end_char"] == ent["end_char"]
                            for e in detected_entities
                        )
                        if not duplicate:
                            ent["page_number"] = p_num
                            detected_entities.append(ent)
                self._log_stage(doc.id, "ANALYZING", "NER analysis scan completed.")

            stage_timings["pii_ner"] = round((time.time() - p_start) * 1000, 2)
            c_start = time.time()
            # ─────────────────────────────────────────────────────────
            # STAGE 9: Risk Classification (CLASSIFYING)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "CLASSIFYING", 90)
            self._log_stage(doc.id, "CLASSIFYING", "Running Risk Classification Engine.")

            # Calculate bounds relative to words/coordinates for bounding box visualization
            for ent in detected_entities:
                risk_lvl = RISK_MAPPING.get(ent["entity_type"], "LOW")
                
                # Estimate coordinate bounding boxes using word matches inside the page
                page_words = ocr_result["pages"][ent["page_number"] - 1]["words"]
                bbox = None
                matched_coords = []
                
                # Clean the entity value and split into words
                ent_val = ent["value"].strip()
                ent_words = [w.strip(",.():;'\"").lower() for w in ent_val.split() if w.strip(",.():;'\"")]
                
                if len(ent_words) == 1:
                    # Single word match: must match case-insensitive exactly or as a significant substring
                    target = ent_words[0]
                    for w in page_words:
                        cleaned_w = w["text"].strip(",.():;'\"").lower()
                        if cleaned_w == target or (len(target) > 3 and target in cleaned_w):
                            matched_coords.append(w["coordinates"])
                elif len(ent_words) > 1:
                    # Multi-word match: find consecutive words on the page matching the sequence
                    for i in range(len(page_words) - len(ent_words) + 1):
                        seq_match = True
                        for j in range(len(ent_words)):
                            cleaned_w = page_words[i + j]["text"].strip(",.():;'\"").lower()
                            # Check if the cleaned word matches the corresponding entity word
                            if cleaned_w != ent_words[j] and ent_words[j] not in cleaned_w:
                                seq_match = False
                                break
                        if seq_match:
                            # Add only the coordinates of this specific matched sequence
                            for j in range(len(ent_words)):
                                matched_coords.append(page_words[i + j]["coordinates"])
                            break

                if matched_coords:
                    # Merge coordinates: [min_x, min_y, max_x, max_y]
                    min_x = min(c[0] for c in matched_coords)
                    min_y = min(c[1] for c in matched_coords)
                    max_x = max(c[2] for c in matched_coords)
                    max_y = max(c[3] for c in matched_coords)
                    bbox = [min_x, min_y, max_x, max_y]
                else:
                    # Fallback default block coordinate
                    bbox = [100.0, 100.0, 200.0, 120.0]

                db_entity = DocumentEntity(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    page_number=ent["page_number"],
                    entity_type=ent["entity_type"],
                    value=ent["value"],
                    confidence=ent["confidence"],
                    start_char=ent["start_char"],
                    end_char=ent["end_char"],
                    bounding_box=bbox,
                    risk_level=risk_lvl
                )
                self.db.add(db_entity)

            self.db.commit()
            self._log_stage(doc.id, "CLASSIFYING", f"Risk evaluation complete. Detected {len(detected_entities)} entities.")

            # ─────────────────────────────────────────────────────────
            # STAGE 9.5: Generate Redacted PDF Document (REDACTING)
            # ─────────────────────────────────────────────────────────
            if ext == ".pdf":
                try:
                    self._log_stage(doc.id, "REDACTING", "Generating visually redacted PDF document...")
                    import fitz
                    pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                    
                    # Only redact actual PII / high-risk entities
                    REDACT_TYPES = {
                        "AADHAAR", "PAN", "PASSPORT", "DRIVING_LICENSE", "VOTER_ID",
                        "EMAIL", "PHONE", "BANK_ACCOUNT", "CREDIT_CARD", "IFSC", "UPI_ID",
                        "PERSON", "ADDRESS", "UK_NHS", "US_DRIVER_LICENSE", "PIN_CODE", "URL"
                    }
                    
                    # Collect unique redaction values per page
                    db_entities = self.db.query(DocumentEntity).filter(DocumentEntity.document_id == doc.id).all()
                    
                    # Group redaction targets: page_number -> set of text values to redact
                    redaction_targets = {}
                    for db_ent in db_entities:
                        if db_ent.entity_type not in REDACT_TYPES:
                            continue
                        p_num = db_ent.page_number
                        if p_num not in redaction_targets:
                            redaction_targets[p_num] = set()
                        
                        # Clean the value — remove newlines, normalize whitespace
                        val = db_ent.value.strip()
                        val = val.replace("\n", " ").replace("\r", " ")
                        # Collapse multiple spaces to single
                        val = " ".join(val.split())
                        
                        if len(val) >= 2:  # Skip single chars
                            redaction_targets[p_num].add(val)
                            # Also add individual words for multi-word values (handles line-broken entities)
                            words = val.split()
                            if len(words) > 1:
                                for w in words:
                                    if len(w) >= 3:  # Skip tiny fragments like "No" or "at"
                                        redaction_targets[p_num].add(w)
                    
                    redaction_count = 0
                    for p_num, targets in redaction_targets.items():
                        if 0 <= p_num - 1 < len(pdf_doc):
                            page = pdf_doc[p_num - 1]
                            for target_text in targets:
                                # Use PyMuPDF's search_for to find exact text rectangles
                                rects = page.search_for(target_text)
                                for rect in rects:
                                    # Add redaction annotation
                                    page.add_redact_annot(rect, fill=(0, 0, 0))
                                    redaction_count += 1
                            # Apply all redactions for this page at once
                            page.apply_redactions()
                    
                    logger.info(f"Applied {redaction_count} redaction boxes across {len(redaction_targets)} pages")
                    
                    # Save redacted PDF to bytes
                    redacted_pdf_bytes = pdf_doc.tobytes()
                    pdf_doc.close()
                    
                    # Save the redacted PDF file under the "redacted" folder
                    storage_client.upload_file(
                        file_content=redacted_pdf_bytes,
                        document_id=str(doc.id),
                        filename=doc.original_filename,
                        content_type="application/pdf",
                        prefix="redacted"
                    )
                    self._log_stage(doc.id, "REDACTING", f"Successfully generated redacted PDF ({redaction_count} redactions).")
                except Exception as redact_err:
                    logger.warning(f"Redacted PDF generation failed: {redact_err}")
                    import traceback
                    traceback.print_exc()
                    self._log_stage(doc.id, "REDACTING", f"Redacted PDF generation failed: {str(redact_err)}", "WARNING")

            stage_timings["classification"] = round((time.time() - c_start) * 1000, 2)
            
            # ─────────────────────────────────────────────────────────
            # STAGE 10: Store Results (COMPLETED)
            # ─────────────────────────────────────────────────────────
            self._update_job(job, "COMPLETED", 100)
            doc.status = "Processed"
            self.db.commit()
            
            # Save background profile run to database
            try:
                from models.ai_models import PerformanceProfile
                total_duration = (time.time() - total_start) * 1000
                profile = PerformanceProfile(
                    request_path=f"background_job_{doc.id}",
                    method="TASK",
                    status_code=200,
                    stages=stage_timings,
                    total_latency=round(total_duration, 2)
                )
                self.db.add(profile)
                self.db.commit()
            except Exception as pe:
                logger.warning(f"Failed to record background profile: {pe}")
            
            self._log_stage(doc.id, "COMPLETED", "Pipeline completed successfully. Document marked as Processed.")

            # ─────────────────────────────────────────────────────────
            # STAGE 11: Auto ML & DL Consensus Prediction (Non-blocking)
            # ─────────────────────────────────────────────────────────
            try:
                from services.deep_learning.inference import DLInferenceEngine
                engine = DLInferenceEngine(self.db)
                
                # Fetch text from processed pages
                pages = self.db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).order_by(DocumentPage.page_number.asc()).all()
                full_text = " ".join(p.text for p in pages) if pages else ""
                
                result = engine.predict_consensus(str(doc.id), full_text)
                self._log_stage(
                    doc.id,
                    "CONSENSUS_PREDICTION",
                    f"Consensus Class: {result['winning_class']} (Winning Model: {result['winning_model']}, Agreement: {result['agreement']})"
                )
            except FileNotFoundError:
                # Models not fully trained yet, skip prediction
                pass
            except Exception as dl_err:
                logger.warning(f"Consensus auto-prediction failed: {dl_err}")
                self._log_stage(doc.id, "CONSENSUS_PREDICTION", f"Consensus prediction failed: {str(dl_err)}", "WARNING")

            return {"status": "SUCCESS", "document_id": str(doc.id)}
        except Exception as e:
            self._update_job(job, "FAILED", job.progress, str(e))
            doc.status = "Failed"
            self.db.commit()
            self._log_stage(doc.id, "FAILED", f"Pipeline failed: {str(e)}", "ERROR")
            raise e
