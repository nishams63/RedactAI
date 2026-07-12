# CHANGELOG - RedactAI

All notable changes to the RedactAI platform will be documented in this file.

## [1.0.0-rc1] - 2026-07-12
### Added
- **Enterprise Security Hardening (Sprint 4.5.3)**: 
  - UserLockout & Account Brute Force Protection (5 attempts lock out user for 15 minutes).
  - Configurable session management (Max 5 active sessions with terminate-oldest eviction).
  - Refresh Token Rotation family checks.
  - SHA-256 duplicate file detection and MIME magic bytes check during upload.
  - Structured log masking (masks PII, Aadhaar, PAN, and JWT tokens in stdout).
  - Automated security scanner suite creating PDF security cards.
- **Performance & Scalability (Sprint 4.5.2)**:
  - CacheManager supporting OCR, Embedding, Retrieval, and SLM warming.
  - Multi-page thread-pool parallelization for PyMuPDF rendering.
- **RAG & SLM Enhancement (Sprint 4.5.1)**:
  - Versioned Prompt Registry tables and quality history tracking in DB.
  - 50-Question Quality QA benchmark runner.
- **Downstream Legal Privacy Assistant (Level 3)**:
  - ChromaDB Vector Store integration.
  - Qwen/Qwen2.5-0.5B-Instruct Small Language Model for legal summarizations and explainable Q&A.
- **Enterprise Foundation & Intelligence (Sprints 1-2, Levels 1-2)**:
  - Layout analysis, OCR, NER, ML document classifiers, and DL compliance engine.
- **Release Telemetry (Sprint 4.5.4)**:
  - Liveness and Readiness FastAPI checkers.
  - End-to-end smoke test runners.
  - Next.js 15 Release Readiness dashboard.
