# RedactAI Production Deployment Guide

This document provides step-by-step instructions to deploy RedactAI as a production-grade cloud application.

---

## 1. System Architecture

```mermaid
graph TD
    Client[Browser / Client] -->|HTTPS| Vercel[Vercel Frontend]
    Client -->|HTTPS| Railway[Railway API Gateway]
    Vercel -->|REST API Calls| Railway
    Railway -->|SQL Queries| Postgres[(PostgreSQL DB)]
    Railway -->|Cache & Session| Redis[(Redis Cache)]
    Railway -->|File Storage| S3[AWS S3 / MinIO]
```

---

## 2. Environment Configurations & Secrets

### Frontend Environment Variables (Vercel)
Set these variables in your Vercel Project Settings:
*   `NEXT_PUBLIC_API_URL`: Public address of the backend service (e.g. `https://redactai-api.up.railway.app/api/v1`).

### Backend Environment Variables (Railway)
Configure these variables in your Railway Service Variables:
*   `ENVIRONMENT`: `production`
*   `DATABASE_URL`: Connection string for PostgreSQL (e.g. `postgresql://user:password@host:port/dbname`).
*   `REDIS_URL`: Connection URL for Redis (e.g. `redis://host:port/0`).
*   `MINIO_ENDPOINT`: *(Optional)* S3 endpoint (leave empty for AWS S3).
*   `MINIO_ACCESS_KEY`: AWS Access Key or MinIO user access key.
*   `MINIO_SECRET_KEY`: AWS Secret Key or MinIO secret access key.
*   `MINIO_BUCKET`: Target S3 bucket name (default: `redactai-storage`).
*   `MINIO_SECURE`: Set to `True` for HTTPS connections.
*   `JWT_SECRET_KEY`: Cryptographic signing key (minimum 32 characters, base64 recommended).
*   `JWT_REFRESH_SECRET_KEY`: Refresh signing key.
*   `ENCRYPTION_KEY`: base64-encoded 32-byte Fernet key for encrypting database PII flags.
*   `ALLOWED_HOSTS`: Comma-separated list of hostnames allowed to query the API (e.g., `redactai-api.up.railway.app,api.redactai.in`).
*   `CORS_ORIGINS`: Comma-separated list of client domains allowed (e.g., `https://redactai.in,https://redactai-frontend.vercel.app`).
*   `HF_HOME`: `.cache/huggingface`
*   `MODEL_CACHE_DIR`: `.cache/models`

---

## 3. Step-by-Step Deployment Order

### Step 3.1: Database & Cache Provisioning
1. Launch a **PostgreSQL** instance on Railway (or AWS RDS). Execute Alembic migrations to seed the initial tables.
2. Launch a **Redis** instance on Railway (or Elasticache).
3. Create an **AWS S3** bucket (e.g., `redactai-storage`) with public access blocked and set up an IAM Policy allowing read/write operations.

### Step 3.2: Backend Deployment (Railway)
1. In the Railway dashboard, click **New Project** and connect your GitHub repository.
2. Select the `/backend` folder as the Root Directory.
3. Configure all backend environment variables. Railway will detect the `Procfile` automatically and run:
   ```bash
   bash scripts/start_prod.sh
   ```
4. Expose the port by linking the project domain.

### Step 3.3: Frontend Deployment (Vercel)
1. In Vercel, click **Add New Project** and import the GitHub repository.
2. Under **Framework Preset**, select **Next.js**.
3. Under **Root Directory**, select `frontend`.
4. Configure `NEXT_PUBLIC_API_URL` under Environment Variables.
5. Click **Deploy**. Vercel will build and host the static components.

---

## 4. Rollback Procedure

If the production deploy fails validation checks or triggers alerts:

1. **Frontend Rollback (Vercel)**:
   * Navigate to the Project Deployments tab in Vercel.
   * Select the last stable deployment.
   * Click **Promote to Production** to instantly revert the static routing.
2. **Backend Rollback (Railway)**:
   * Select the stable target commit in Railway.
   * Click **Rollback** to redeploy the previous container.
3. **Database Schema Rollback**:
   * If database migrations caused issues, ssh into the backend server environment and run:
     ```bash
     alembic downgrade -1
     ```
