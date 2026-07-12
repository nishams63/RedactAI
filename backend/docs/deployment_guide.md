# RedactAI Deployment Guide

This document describes how to deploy RedactAI v1.0 RC1 using Docker Compose.

## 1. Prerequisites
- Docker Engine >= 20.10.0
- Docker Compose >= 2.0.0
- Minimum hardware: 4 vCPUs, 8 GB RAM, 20 GB disk space

## 2. Startup Instructions
Deploy the entire stack in detached mode:
```bash
docker-compose up -d --build
```

Verify that all containers are healthy:
```bash
docker-compose ps
```

Expected live containers:
- `redactai-db`: PostgreSQL relational store
- `redactai-redis`: Redis cache & broker broker
- `redactai-minio`: S3 compatible storage
- `redactai-backend`: FastAPI uvicorn gateway
- `redactai-celery-worker`: Celery worker pipeline
- `redactai-frontend`: Next.js portal UI

## 3. Environment Variables Configuration
Configure keys inside `.env` or system settings:
- `JWT_SECRET_KEY`: Long random string for access JWT keys.
- `ENCRYPTION_KEY`: 32 url-safe base64 encoded bytes for database encryption.
- `DATABASE_URL`: PostgreSQL DB link.
- `REDIS_URL`: Redis brokerage pool.
