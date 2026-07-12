# RedactAI Architecture Guide

This document outlines the high-level architecture, directory layout, database models, and service interfaces for RedactAI v1.0.

## 1. Component Topology
RedactAI is built on a multi-tier enterprise architecture:
1. **Next.js 15 Client Portal**: Responsive dashboard for data ingestion, policy management, compliance reporting, and user administration.
2. **FastAPI Application Gateway**: High-throughput REST API handler implementing endpoint protections, rate limiting, and request logging.
3. **ChromaDB Vector Store**: Fast, persistent storage for versioned document chunk embeddings.
4. **Celery Task Broker**: Handles asynchronous OCR page extractions, layout classification, and downstream ML pipeline operations.
5. **PostgreSQL Relational DB**: Stores metadata, logs, sessions, prompts registry, compliance metrics, and human overrides feedback.
6. **Local SLM Engine**: Direct inference pipeline using Qwen/Qwen2.5-0.5B-Instruct weight sets.

## 2. Directory Layout
```
├── backend/
│   ├── api/             # REST endpoints (auth, legal, release, security)
│   ├── core/            # Middleware, security cryptography, config settings
│   ├── database/        # DB connection pools, migrations, seed configurations
│   ├── models/          # SQLAlchemy schemas (users, documents, logs)
│   ├── repositories/    # Database transaction utilities
│   ├── services/        # Logic services (SLM, ML, RAG retrievers, caching)
│   └── docs/            # Platform operational guides
├── frontend/
│   ├── app/             # Next.js 15 pages and dashboard views
│   ├── components/      # UI widgets (graphs, tables, score meters)
│   └── providers/       # Global React contexts
```
