# --- Stage 1: Build Frontend ---
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Build production frontend with relative API path
ENV NEXT_PUBLIC_API_URL=/api/v1
RUN npm run build

# --- Stage 2: Production Base ---
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies (including Nginx and Supervisor)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js in the production image for Next.js start
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies and install
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && python -m spacy download en_core_web_sm


# Copy backend source
COPY backend/ ./backend/

# Copy built frontend source and configuration files
COPY --from=frontend-builder /app/frontend /app/frontend
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /app/start.sh

# Expose ports
EXPOSE 7860 8000

# Make start script executable
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
