# RedactAI — AI-Powered Legal Document Privacy & Compliance Platform

[![Sprint](https://img.shields.io/badge/Sprint-1%20Foundation-blue)](.)
[![Target Market](https://img.shields.io/badge/Market-India-orange)](.)
[![License](https://img.shields.io/badge/License-Proprietary-red)](.)

> Enterprise-grade platform for automated PII detection, document redaction, and compliance management. Built for India's legal and regulatory landscape.

## 🏗️ Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Frontend   │◄──►│   Backend    │◄──►│  PostgreSQL  │
│  Next.js 15  │    │   FastAPI    │    │     v16      │
│  Port: 3000  │    │  Port: 8000  │    │  Port: 5432  │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
                    ┌──────┴───────┐
                    │              │
              ┌─────▼────┐  ┌─────▼────┐
              │  Redis   │  │  MinIO   │
              │  Celery  │  │    S3    │
              │  :6379   │  │  :9000   │
              └──────────┘  └──────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Run the Application

```bash
# Clone and navigate
cd DS_AI_EMPLOYEE

# Start all services
docker compose up --build -d

# View logs
docker compose logs -f
```

### Access Points
| Service       | URL                          |
|---------------|------------------------------|
| Frontend      | http://localhost:3000         |
| Backend API   | http://localhost:8000         |
| API Docs      | http://localhost:8000/docs    |
| MinIO Console | http://localhost:9001         |

### Default Admin Credentials
- **Email:** admin@redactai.in
- **Password:** Admin@123456

## 📁 Project Structure

```
DS_AI_EMPLOYEE/
├── backend/                    # FastAPI Backend
│   ├── api/v1/                 # Versioned API endpoints
│   ├── core/                   # Config, security, Celery, middleware
│   ├── database/               # Session, seed data
│   ├── dependencies/           # DI (auth, DB, RBAC)
│   ├── models/                 # SQLAlchemy models (13 tables)
│   ├── repositories/           # Repository pattern (CRUD)
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer
│   ├── storage/                # MinIO S3 client
│   ├── tests/                  # Integration tests
│   ├── alembic/                # Database migrations
│   └── .env.{dev|staging|prod} # Environment configs
├── frontend/                   # Next.js 15 Frontend
│   ├── app/                    # Pages (login, register, dashboard)
│   ├── providers/              # Auth, Theme, React Query
│   ├── services/               # API client
│   ├── types/                  # TypeScript definitions
│   └── lib/                    # Utilities
├── ai-services/                # AI Microservice Stubs
│   ├── ocr-service/
│   ├── pii-service/
│   ├── ner-service/
│   ├── redaction-service/
│   ├── compliance-service/
│   ├── report-service/
│   └── agent-service/
└── docker-compose.yml
```

## 🔐 API Endpoints

### Authentication
| Method | Endpoint              | Description                |
|--------|-----------------------|----------------------------|
| POST   | /api/v1/auth/register | Register new user          |
| POST   | /api/v1/auth/login    | Login & get tokens         |
| POST   | /api/v1/auth/logout   | Revoke refresh token       |
| POST   | /api/v1/auth/refresh  | Refresh access token       |

### Users
| Method | Endpoint              | Description                |
|--------|-----------------------|----------------------------|
| GET    | /api/v1/users/me      | Get current user profile   |
| PUT    | /api/v1/users/me      | Update profile             |

### Organizations
| Method | Endpoint               | Description               |
|--------|------------------------|---------------------------|
| GET    | /api/v1/organizations  | List organizations        |
| POST   | /api/v1/organizations  | Create organization       |

### Documents
| Method | Endpoint                      | Description                  |
|--------|-------------------------------|------------------------------|
| POST   | /api/v1/documents/upload      | Upload document              |
| GET    | /api/v1/documents             | List with search/filter/page |
| GET    | /api/v1/documents/dashboard   | Dashboard stats & activity   |
| GET    | /api/v1/documents/{id}        | Get document details         |
| DELETE | /api/v1/documents/{id}        | Delete document              |

## 🗃️ Database Schema (13 Tables)

### Core Tables
- `organizations` — Company/firm entities
- `roles` — RBAC roles (Admin, Legal Officer, Compliance Officer, Reviewer, Viewer)
- `users` — User accounts with org assignment
- `user_roles` — Many-to-many user ↔ role
- `refresh_tokens` — JWT refresh token storage for revocation
- `documents` — Document metadata and storage references
- `document_versions` — Version tracking for document edits

### Async Processing
- `document_processing_jobs` — Celery task tracking with progress

### AI Placeholder Tables (Sprint 2+)
- `models` — AI/ML model registry
- `detected_entities` — NER/PII detection results
- `redactions` — Applied redaction records
- `compliance_results` — Rule compliance assessments
- `processing_logs` — Pipeline stage logging

## 🔒 Security Features
- JWT access tokens (15 min) + refresh tokens (7 days)
- bcrypt password hashing
- RBAC with 5 roles
- CORS configuration
- Security headers (X-Frame-Options, HSTS, CSP)
- Input validation via Pydantic/Zod

## 🎨 Frontend Features
- Dark/Light mode toggle
- Glassmorphism design system
- Animated stat cards and progress bars
- Drag-and-drop document upload
- Searchable/filterable/sortable document table
- Responsive sidebar navigation
- Profile management & password change

## 📋 Sprint Roadmap
- **Sprint 1** ✅ Foundation (Auth, RBAC, Documents, Dashboard, Infrastructure)
- **Sprint 2** — OCR & PII Detection (Tesseract, spaCy, custom NER)
- **Sprint 3** — Redaction Engine & Compliance Checks
- **Sprint 4** — Report Generation & Audit Trails
- **Sprint 5** — Agentic AI Orchestration
