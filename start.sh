#!/bin/sh

MODE=${DEPLOYMENT_MODE:-production}

echo "Starting RedactAI in [$MODE] mode..."

if [ "$MODE" = "single" ] || [ "$MODE" = "huggingface" ]; then
    echo "Launching via Supervisor + Nginx process manager..."
    exec supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
else
    echo "Launching in standalone API mode..."
    cd /app/backend
    python database_bootstrap.py
    exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-2} --proxy-headers
fi
