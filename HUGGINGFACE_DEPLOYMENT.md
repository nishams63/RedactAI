# Hugging Face Spaces Deployment Guide

This guide details how to deploy a single-container demo profile of RedactAI on Hugging Face Docker Spaces.

---

## 1. Space Creation & Settings

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. Configure the following fields:
   - **Space Name**: `redact-ai` (or any custom name)
   - **License**: `mit` (or choose another)
   - **SDK**: Select **Docker**
   - **Docker Template**: Select **Blank** (do not use template defaults)
   - **Space Visibility**: **Public** (recommended for demo purposes)
3. Click **Create Space**.

---

## 2. Hardware Recommendation

RedactAI features built-in **automatic resource detection** and **graceful AI fallbacks**. However, for optimal performance:
- **Minimum Requirement (Free)**: CPU Basic (2 vCPUs, 16GB RAM) - runs with lazy loading and fallback rules if PyTorch downloads time out.
- **Recommended (Paid)**: CPU Upgrade (4 vCPUs, 32GB RAM) or Nvidia T4/L4 GPU (for faster Deep Learning and Legal-BERT inference).

---

## 3. Environment Variables

Go to your Hugging Face Space **Settings** page, scroll to **Variables and secrets**, and add the following variables:

| Secret Name | Suggested Value | Description |
| :--- | :--- | :--- |
| `DEPLOYMENT_MODE` | `huggingface` | Enables single-container local mode, bypassing Celery, Redis, Postgres, and MinIO. |
| `ENVIRONMENT` | `huggingface` | Profile indicator. |
| `JWT_SECRET_KEY` | `[generate-32-character-random-hex]` | Access token signature key. |
| `JWT_REFRESH_SECRET_KEY` | `[generate-32-character-random-hex]` | Refresh token signature key. |
| `ENCRYPTION_KEY` | `XEfwmtmC9_gIOpoqPIY7kthp84fsSQuhg2IxjAiAB2E=` | 32-byte Fernet key for document database encryption. |

*Note: Since SQLite database initializes and seeds itself automatically, no database credentials are required.*

---

## 4. Build & Deployment Steps

Hugging Face Spaces compiles your code automatically when you push to the Space's Git remote.

### Option A: Via GitHub Action
1. Set up a GitHub Action to mirror your repository to Hugging Face Spaces on push:
   - Git Remote URL: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`
   - Use a Hugging Face Access Token with `write` privileges.

### Option B: Local Push to Hugging Face
1. Clone your Hugging Face space repository locally:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
   ```
2. Copy the RedactAI files into the folder and push:
   ```bash
   git add .
   git commit -m "Deploy RedactAI v1.0"
   git push origin main
   ```

---

## 5. Troubleshooting Guide

### Container Crash on Startup (Exit Code 1)
- Check the Hugging Face **Logs** tab. Look at the **Startup Diagnostics Table** output.
- Make sure `JWT_SECRET_KEY` and `JWT_REFRESH_SECRET_KEY` are configured in Space secrets and are at least 16 characters long.

### Slow Model Load or High Inference Latency
- If running on basic free hardware, Legal-BERT deep learning models may load slowly. The application will log a warning and continue starting, falling back to keyword-statistical classifier rules.

### "No open ports detected"
- Hugging Face expects the container to expose and listen on port `7860`. The unified Dockerfile is pre-configured to bind Nginx gateway on port `7860`. Do not modify Nginx port assignments in `nginx.conf`.
