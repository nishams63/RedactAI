"""FastAPI dependency injection — DB session, current user, and RBAC checks."""
import uuid
import logging
from typing import Generator, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database.session import SessionLocal
from core.security import decode_access_token
from models.user import User

logger = logging.getLogger("redactai.deps")

security_scheme = HTTPBearer()


def get_db() -> Generator:
    """Yield a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate user from JWT access token, enforcing active session checking."""
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    # Enforce session revocation verification
    session_key = payload.get("session_key")
    if session_key:
        from models.ai_models import UserSession
        session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.session_key == session_key,
            UserSession.is_active == True
        ).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked or expired")
        
    return user


def check_permissions(required_roles: List[str]):
    """Dependency factory that enforces RBAC — returns a dependency function."""
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = [r.name for r in current_user.roles]
        # Admin bypasses all checks
        if "Admin" in user_roles:
            return current_user
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}",
            )
        return current_user
    return permission_checker
