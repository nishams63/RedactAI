# RedactAI Operational Readiness and Platform Guide

This comprehensive reference document contains operational guides for administrators, developers, users, troubleshooting, and the AI Pipeline.

## 1. API Documentation
RedactAI exposes REST API endpoints:
- **Authentication**: `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `POST /api/v1/auth/logout`.
- **Documents**: `POST /api/v1/documents/upload`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`.
- **Legal AI**: `POST /api/v1/legal/analyze/{id}`, `POST /api/v1/legal/chat`, `POST /api/v1/legal/review`.
- **Security**: `GET /api/v1/security/stats`, `GET /api/v1/security/sessions`, `POST /api/v1/security/sessions/revoke`.
- **Release Operations**: `GET /api/v1/release/health/readiness`, `GET /api/v1/release/manifest`.

Interactive documentation is served at `/docs` (Swagger UI) when the backend is running.

## 2. Administrator & Configuration Guide
Administrators can customize platform security parameters inside `core/config.py` or `.env` settings:
- `MAX_ACTIVE_SESSIONS`: Limits concurrent active user sessions (default: 5).
- `SESSION_LIMIT_STRATEGY`: Session overflow behavior (`terminate_oldest` or `reject_login`).
- `PASSWORD_EXPIRATION_DAYS`: Lock account password after N days (default: 0, disabled).

Failed login lockout thresholds are fixed at 5 failures within 15 minutes.

## 3. Developer & AI Pipeline Guide
The AI processing pipeline flows sequentially:
1. **Document Upload**: Enforces MIME validation and magic signature verify.
2. **OCR & Parsing**: Page rendering parallelized via ThreadPool.
3. **ML Classifier**: Assigns document types (NDA, HIPAA, GDPR).
4. **Policy check**: Compliance engine reviews clauses.
5. **RAG retrieval**: Chunks indexed in ChromaDB vector store.
6. **SLM reasoning**: Qwen2.5-0.5B evaluates compliance risks and returns answers with citation coverage mappings.

## 4. Troubleshooting Guide
- **Database Connection Error**: Verify PostgreSQL service status or connection credentials URL.
- **MinIO Connection Timeout**: MinIO will fall back to local disk storage automatically.
- **Memory exhaustion**: Check celery concurrency allocations.
