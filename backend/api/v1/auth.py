"""Authentication API endpoints injecting Request context for security profiling."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from dependencies import get_db
from schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, LogoutRequest, ForgotPasswordRequest, MessageResponse,
)
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    service = AuthService(db)
    return service.register(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        organization_name=request.organization_name,
    )


@router.post("/login", response_model=TokenResponse)
def login(login_req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate, manage active sessions limit, and return tokens."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")
    service = AuthService(db)
    return service.login(
        email=login_req.email, 
        password=login_req.password, 
        ip_address=client_ip, 
        user_agent=user_agent
    )


@router.post("/logout", response_model=MessageResponse)
def logout(logout_req: LogoutRequest, db: Session = Depends(get_db)):
    """Logout by revoking the active session and refresh token."""
    service = AuthService(db)
    service.logout(refresh_token_str=logout_req.refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_req: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Exchange a valid refresh token with family rotation checks."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown")
    service = AuthService(db)
    return service.refresh(
        refresh_token_str=refresh_req.refresh_token, 
        ip_address=client_ip, 
        user_agent=user_agent
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(forgot_req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Request password reset link."""
    service = AuthService(db)
    service.forgot_password(email=forgot_req.email)
    return {"message": "If that email exists, a reset link has been sent"}
