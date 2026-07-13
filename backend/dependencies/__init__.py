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

from fastapi import Query

security_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator:
    """Yield a SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    token: str | None = Query(None),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate user from JWT access token, supporting both header and query param."""
    import traceback
    try:
        logger.info(f"get_current_user dependency execution started: credentials={credentials is not None}, token={token is not None}")
        token_str = None
        if credentials and credentials.credentials:
            token_str = credentials.credentials
        elif token:
            token_str = token

        if not token_str:
            logger.warning("Authentication failed: No token found in headers or query parameter.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        payload = decode_access_token(token_str)
        if payload is None:
            logger.warning("Authentication failed: Invalid or expired access token payload.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token")

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Authentication failed: Token payload missing subject claim (sub).")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject claim")

        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if not user:
            logger.warning(f"Authentication failed: User with ID {user_id} not found in database.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        if not user.is_active:
            logger.warning(f"Authentication failed: User account {user.email} is deactivated.")
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
                logger.warning(f"Authentication failed: Session {session_key} revoked or expired for user {user.email}.")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked or expired")
            
        logger.info(f"get_current_user dependency verification succeeded: user={user.email}")
        return user
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"UNHANDLED EXCEPTION IN get_current_user: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Authentication dependency internal error: {str(e)}")


def check_permissions(required_roles: List[str]):
    """Dependency factory that enforces RBAC — returns a dependency function."""
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        import traceback
        try:
            logger.info(f"permission_checker started: checking roles={required_roles} for user={current_user.email}")
            user_roles = [r.name for r in current_user.roles]
            # Admin bypasses all checks
            if "Admin" in user_roles:
                logger.info(f"permission_checker bypass: user={current_user.email} is Admin")
                return current_user
            if not any(role in user_roles for role in required_roles):
                logger.warning(f"permission_checker failed: user={current_user.email} roles={user_roles} lacks required={required_roles}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {required_roles}",
                )
            logger.info(f"permission_checker succeeded for user={current_user.email}")
            return current_user
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"UNHANDLED EXCEPTION IN permission_checker: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Permission dependency internal error: {str(e)}")
    return permission_checker

