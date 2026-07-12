"""Authentication service handles registration, login, token refresh, session revocation, and security audits."""
import uuid
import logging
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token, 
    verify_password_strength
)
from core.config import settings
from repositories.user import UserRepository, RefreshTokenRepository
from repositories.organization import OrganizationRepository
from models.user import RefreshToken, User
from models.role import Role
from models.ai_models import UserSession, LoginAttempt, PasswordHistory, AuditLog, SecurityAlert

logger = logging.getLogger("redactai.auth")

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.org_repo = OrganizationRepository(db)

    def register(self, email: str, password: str, full_name: str, organization_name: str | None = None) -> dict:
        """Registers a new user and validates password complexity and history constraint logs."""
        # 1. Password complexity check
        if not verify_password_strength(password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak. Must be at least 8 characters and include uppercase, lowercase, numbers, and special characters."
            )

        # Check if email already exists
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        # Resolve or create organization
        org_id = None
        if organization_name:
            org = self.org_repo.get_by_name(organization_name)
            if not org:
                org = self.org_repo.create({"id": uuid.uuid4(), "name": organization_name})
            org_id = org.id

        hashed = hash_password(password)
        # Create user
        user = self.user_repo.create({
            "id": uuid.uuid4(),
            "email": email,
            "hashed_password": hashed,
            "full_name": full_name,
            "organization_id": org_id,
            "password_changed_at": datetime.now(timezone.utc)
        })

        # Save initial password history
        hist = PasswordHistory(user_id=user.id, hashed_password=hashed)
        self.db.add(hist)

        # Assign default Viewer role
        viewer_role = self.db.query(Role).filter(Role.name == "Viewer").first()
        if viewer_role:
            self.user_repo.assign_role(user.id, viewer_role.id)

        self.db.commit()

        # Log to audit trail
        audit = AuditLog(
            user_id=user.id,
            user_email=email,
            action="REGISTER",
            resource="UserAccount",
            result="SUCCESS",
            ip_address="127.0.0.1"
        )
        self.db.add(audit)
        self.db.commit()

        # Generate tokens
        tokens = self._generate_tokens_and_session(user, "127.0.0.1", "API-Register")
        logger.info(f"User registered: {email}")
        return tokens

    def login(self, email: str, password: str, ip_address: str = "127.0.0.1", user_agent: str = "Unknown") -> dict:
        """Logs in the user, validating lockouts, active sessions, and password expiration."""
        user = self.user_repo.get_by_email(email)
        
        # 1. Lockout verification check
        if user and user.locked_until and datetime.now(timezone.utc).replace(tzinfo=None) < user.locked_until.replace(tzinfo=None):
            # Log lockout event
            attempt = LoginAttempt(email=email, ip_address=ip_address, user_agent=user_agent, status="LOCKED_OUT")
            self.db.add(attempt)
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Account temporarily locked. Please try again in 15 minutes."
            )

        # 2. Authenticate
        if not user or not verify_password(password, user.hashed_password):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                    # Trigger alert
                    alert = SecurityAlert(
                        event_type="BRUTE_FORCE_LOCKOUT",
                        severity="CRITICAL",
                        description=f"User account locked for 15m after 5 failed logins: {email}",
                        details={"ip_address": ip_address, "user_agent": user_agent}
                    )
                    self.db.add(alert)
                
                self.db.commit()

            # Record failed login attempt
            attempt = LoginAttempt(email=email, ip_address=ip_address, user_agent=user_agent, status="FAILED")
            self.db.add(attempt)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

        # Reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()

        # 3. Password Expiration check
        if settings.PASSWORD_EXPIRATION_DAYS > 0:
            changed_at = user.password_changed_at or user.created_at
            if (datetime.now(timezone.utc) - changed_at.replace(tzinfo=timezone.utc)).days >= settings.PASSWORD_EXPIRATION_DAYS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Password expired. Please reset your password to proceed."
                )

        # 4. Session management & limits
        active_sessions = self.db.query(UserSession).filter(
            UserSession.user_id == user.id, 
            UserSession.is_active == True
        ).order_by(UserSession.created_at.asc()).all()

        if len(active_sessions) >= settings.MAX_ACTIVE_SESSIONS:
            if settings.SESSION_LIMIT_STRATEGY == "terminate_oldest":
                # Deactivate the oldest session
                oldest = active_sessions[0]
                oldest.is_active = False
                
                # Revoke associated refresh token
                ref_tok = self.db.query(RefreshToken).filter(
                    RefreshToken.user_id == user.id,
                    RefreshToken.token == oldest.session_key
                ).first()
                if ref_tok:
                    ref_tok.is_revoked = True
                
                self.db.commit()
                logger.info(f"Terminated oldest active session for user {email} (Limit reached)")
                
                audit = AuditLog(
                    user_id=user.id,
                    user_email=email,
                    action="SESSION_EVICT",
                    resource=f"Session_{oldest.id}",
                    result="SUCCESS",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                self.db.add(audit)
            else:
                # Reject login strategy
                attempt = LoginAttempt(email=email, ip_address=ip_address, user_agent=user_agent, status="REJECT_SESSION_LIMIT")
                self.db.add(attempt)
                self.db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Maximum active session count reached. Please logout of other sessions first."
                )

        # 5. Success login telemetry log
        attempt = LoginAttempt(email=email, ip_address=ip_address, user_agent=user_agent, status="SUCCESS")
        self.db.add(attempt)
        
        audit = AuditLog(
            user_id=user.id,
            user_email=email,
            action="LOGIN",
            resource="UserAccount",
            result="SUCCESS",
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(audit)
        self.db.commit()

        # Generate tokens
        tokens = self._generate_tokens_and_session(user, ip_address, user_agent)
        logger.info(f"User logged in: {email}")
        return tokens

    def refresh(self, refresh_token_str: str, ip_address: str = "127.0.0.1", user_agent: str = "Unknown") -> dict:
        """Exchanges refresh token with rotation family checks, creating new session key."""
        token_record = self.token_repo.get_by_token(refresh_token_str)
        if not token_record or token_record.is_revoked:
            # Replay attack warning: if token already revoked, someone is reusing it!
            if token_record:
                # Revoke all tokens in this user's family as precaution
                self.db.query(RefreshToken).filter(RefreshToken.user_id == token_record.user_id).update({"is_revoked": True})
                self.db.query(UserSession).filter(UserSession.user_id == token_record.user_id).update({"is_active": False})
                self.db.commit()
                
                alert = SecurityAlert(
                    event_type="REPLAY_ATTACK_DETECTED",
                    severity="HIGH",
                    description=f"Potential refresh token replay attack detected for user ID {token_record.user_id}. Revoked all sessions.",
                    details={"token_reused": refresh_token_str, "ip_address": ip_address}
                )
                self.db.add(alert)
                self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if token_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

        # Deactivate old session
        from core.security import decode_refresh_token
        payload = decode_refresh_token(refresh_token_str)
        session_key = payload.get("session_key") if payload else None
        if session_key:
            session = self.db.query(UserSession).filter(
                UserSession.user_id == token_record.user_id,
                UserSession.session_key == session_key
            ).first()
            if session:
                session.is_active = False

        # Revoke old token
        self.token_repo.revoke_token(refresh_token_str)
        self.db.commit()

        # Fetch user
        user = self.db.query(User).filter(User.id == token_record.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")

        # Generate new tokens and session
        tokens = self._generate_tokens_and_session(user, ip_address, user_agent)
        return tokens

    def logout(self, refresh_token_str: str) -> None:
        """Terminates session key and revokes refresh token."""
        from core.security import decode_refresh_token
        payload = decode_refresh_token(refresh_token_str)
        session_key = payload.get("session_key") if payload else None
        
        token_record = self.token_repo.get_by_token(refresh_token_str)
        if token_record:
            if session_key:
                session = self.db.query(UserSession).filter(
                    UserSession.user_id == token_record.user_id,
                    UserSession.session_key == session_key
                ).first()
                if session:
                    session.is_active = False
            
            audit = AuditLog(
                user_id=token_record.user_id,
                action="LOGOUT",
                resource=f"Session_{session.id if session else 'Unknown'}",
                result="SUCCESS"
            )
            self.db.add(audit)
            
        self.token_repo.revoke_token(refresh_token_str)
        self.db.commit()
        logger.info("User logged out, session terminated")

    def change_password(self, user: User, new_password: str) -> None:
        """Updates user password verifying history constraints."""
        # Validate strength
        if not verify_password_strength(new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak. Must be at least 8 characters and include uppercase, lowercase, numbers, and special characters."
            )

        # Validate history (last 5 passwords)
        history = self.db.query(PasswordHistory).filter(PasswordHistory.user_id == user.id).order_by(PasswordHistory.created_at.desc()).limit(5).all()
        for past in history:
            if verify_password(new_password, past.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reuse any of your last 5 passwords."
                )

        hashed = hash_password(new_password)
        
        # Save password change
        user.hashed_password = hashed
        user.password_changed_at = datetime.now(timezone.utc)
        
        # Record history
        hist = PasswordHistory(user_id=user.id, hashed_password=hashed)
        self.db.add(hist)
        
        audit = AuditLog(
            user_id=user.id,
            action="PASSWORD_CHANGE",
            resource="UserAccount",
            result="SUCCESS"
        )
        self.db.add(audit)
        
        # Revoke all other active sessions for secure logout everywhere on password reset
        self.db.query(UserSession).filter(UserSession.user_id == user.id).update({"is_active": False})
        self.db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"is_revoked": True})
        
        self.db.commit()

    def forgot_password(self, email: str) -> None:
        user = self.user_repo.get_by_email(email)
        if user:
            logger.info(f"[STUB] Password reset requested for {email}. Security logged.")

    def _generate_tokens_and_session(self, user: User, ip_address: str, user_agent: str) -> dict:
        # Generate new session UUID
        session_uuid = str(uuid.uuid4())
        
        # Create access token embedding session_key and role definitions
        roles_list = [r.name for r in user.roles]
        access_token = create_access_token(data={
            "sub": str(user.id),
            "session_key": session_uuid,
            "roles": roles_list
        })
        
        # Create refresh token mapped to session UUID
        refresh_token = create_refresh_token(data={
            "sub": str(user.id),
            "session_key": session_uuid
        })

        # Store session in database
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session = UserSession(
            user_id=user.id,
            session_key=session_uuid, # Mapped to session UUID
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at.replace(tzinfo=None),
            is_active=True
        )
        self.db.add(session)

        # Store refresh token record
        self.token_repo.create({
            "id": uuid.uuid4(),
            "token": refresh_token,
            "user_id": user.id,
            "expires_at": expires_at,
        })
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
