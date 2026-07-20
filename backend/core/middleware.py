"""Global middleware — exception handler, logging, security headers, rate limiting, and masking."""
import logging
import time
import uuid
import re
import traceback
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from core.config import settings

logger = logging.getLogger("redactai")

# In-memory sliding window rate limiter
RATE_LIMIT_WINDOW = 60 # seconds
RATE_LIMIT_MAX_REQUESTS = 100
ip_request_history = defaultdict(list)


class SensitiveDataMaskingFilter(logging.Filter):
    """Scan and replace sensitive data patterns (Aadhaar, PAN, tokens) in all logged outputs."""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[MASKED_AADHAAR]", record.msg)
            record.msg = re.sub(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[MASKED_PAN]", record.msg)
            record.msg = re.sub(r"Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "Bearer [MASKED_TOKEN]", record.msg)
            record.msg = re.sub(r"\"password\":\s*\"[^\"]+\"", "\"password\": \"[MASKED]\"", record.msg)
        return True


# Apply masking filter to root and redactai loggers
mask_filter = SensitiveDataMaskingFilter()
logging.getLogger().addFilter(mask_filter)
logger.addFilter(mask_filter)


class GlobalExceptionMiddleware:
    """Catches unhandled exceptions and returns a structured JSON error response."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "type": str(type(exc).__name__)},
            )
            await response(scope, receive, send)


def setup_middleware(app: FastAPI) -> None:
    """Attach all middleware to the FastAPI application."""
    from fastapi.middleware.gzip import GZipMiddleware
    
    # Response GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS
    origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.(vercel\.app|onrender\.com)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Proxy Headers (real client IP mapping in production behind load balancers)
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    # Trusted hosts (production hardening)
    if settings.ENVIRONMENT == "production":
        hosts = settings.ALLOWED_HOSTS if isinstance(settings.ALLOWED_HOSTS, list) else [settings.ALLOWED_HOSTS]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)

    # Global exception handler
    app.add_middleware(GlobalExceptionMiddleware)

    # Request logging, rate limiting, request size limit, correlation ID, and performance profiling middleware
    app.add_middleware(RequestLoggingMiddleware)


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Rate Limiting
        client_ip = scope.get("client", ["127.0.0.1"])[0]
        now = time.time()
        
        # Clean up timestamps older than window
        timestamps = ip_request_history[client_ip]
        timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        ip_request_history[client_ip] = timestamps
        
        if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
            try:
                from database.session import SessionLocal
                from models.ai_models import SecurityAlert
                db = SessionLocal()
                alert = SecurityAlert(
                    event_type="RATE_LIMIT_VIOLATION",
                    severity="MEDIUM",
                    description=f"IP {client_ip} triggered rate limit of {RATE_LIMIT_MAX_REQUESTS} req/min.",
                    details={"ip_address": client_ip}
                )
                db.add(alert)
                db.commit()
                db.close()
            except Exception:
                pass
                
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit exceeded."}
            )
            await response(scope, receive, send)
            return
            
        timestamps.append(now)

        # 2. Request Size Limits (50MB)
        headers = dict(scope.get("headers", []))
        content_length_str = headers.get(b"content-length", b"0").decode()
        try:
            content_length = int(content_length_str)
        except ValueError:
            content_length = 0
            
        max_size = 50 * 1024 * 1024 # 50MB
        if content_length > max_size:
            response = JSONResponse(
                status_code=413,
                content={"detail": f"Request payload too large. Maximum allowed size is {max_size // (1024*1024)} MB."}
            )
            await response(scope, receive, send)
            return

        # 3. Correlation ID Injection
        request_id = headers.get(b"x-request-id", str(uuid.uuid4()).encode()).decode()
        
        from fastapi import Request
        request = Request(scope, receive=receive)
        request.state.stage_timings = {}
        
        start_time = time.time()
        
        # Wrap send to inject correlation ID and security headers
        status_code = [200]
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message["status"]
                msg_headers = list(message.get("headers", []))
                
                # Correlation ID header
                msg_headers.append((b"x-request-id", request_id.encode()))
                msg_headers.append((b"x-correlation-id", request_id.encode()))
                
                # Strict security headers
                msg_headers.append((b"X-Content-Type-Options", b"nosniff"))
                msg_headers.append((b"X-Frame-Options", b"DENY"))
                msg_headers.append((b"X-XSS-Protection", b"1; mode=block"))
                msg_headers.append((b"Strict-Transport-Security", b"max-age=31536000; includeSubDomains"))
                msg_headers.append((b"Referrer-Policy", b"strict-origin-when-cross-origin"))
                
                message["headers"] = msg_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            process_time = time.time() - start_time
            logger.info(
                f"{request.method} {request.url.path} — {status_code[0]} — {process_time:.3f}s [Request-ID: {request_id}]"
            )
            
            # Save timing profile in DB
            try:
                from database.session import SessionLocal
                from models.ai_models import PerformanceProfile
                stage_timings = getattr(request.state, "stage_timings", {})
                if not stage_timings:
                    stage_timings = {"api_call": round(process_time * 1000, 2)}
                    
                db = SessionLocal()
                profile = PerformanceProfile(
                    request_path=request.url.path,
                    method=request.method,
                    status_code=status_code[0],
                    stages=stage_timings,
                    total_latency=round(process_time * 1000, 2)
                )
                db.add(profile)
                db.commit()
                db.close()
            except Exception as e:
                logger.warning(f"Failed to record performance timing profile: {e}")
