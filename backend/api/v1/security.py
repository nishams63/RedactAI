"""Security auditing, session management, and automated testing API endpoints."""
import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user, check_permissions
from models.user import User
from models.ai_models import UserSession, LoginAttempt, AuditLog, SecurityAlert
from services.legal_ai.security_checker import SecurityChecker, REPORTS_DIR

router = APIRouter(prefix="/security", tags=["Security Dashboard"])


@router.get("/stats")
def get_security_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve security score breakdown and system telemetry statistics."""
    checker = SecurityChecker(db)
    score_breakdown = checker.calculate_security_score()
    
    active_sessions = db.query(UserSession).filter(UserSession.is_active == True).count()
    total_alerts = db.query(SecurityAlert).count()
    failed_logins = db.query(LoginAttempt).filter(LoginAttempt.status == "FAILED").count()
    audit_count = db.query(AuditLog).count()
    
    return {
        "score": score_breakdown,
        "active_sessions": active_sessions,
        "total_alerts": total_alerts,
        "failed_logins": failed_logins,
        "audit_logs_count": audit_count
    }


@router.get("/audit")
def get_audit_logs(
    current_user: User = Depends(check_permissions(["Admin", "Legal Officer"])),
    db: Session = Depends(get_db)
):
    """Retrieve immutable audit trail events (restricted to Admin/Legal Officer)."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return logs


@router.get("/alerts")
def get_security_alerts(
    current_user: User = Depends(check_permissions(["Admin"])),
    db: Session = Depends(get_db)
):
    """Retrieve active and resolved security warnings."""
    alerts = db.query(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(50).all()
    return alerts


@router.get("/sessions")
def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List active user sessions (Viewer logs self; Admin logs all)."""
    roles = [r.name for r in current_user.roles]
    if "Admin" in roles:
        sessions = db.query(UserSession).filter(UserSession.is_active == True).order_by(UserSession.last_active_at.desc()).all()
    else:
        sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id, UserSession.is_active == True).order_by(UserSession.last_active_at.desc()).all()
    
    # Map user emails for display
    resp = []
    for s in sessions:
        user_email = "Unknown"
        usr = db.query(User).filter(User.id == s.user_id).first()
        if usr:
            user_email = usr.email
            
        resp.append({
            "id": str(s.id),
            "user_email": user_email,
            "ip_address": s.ip_address or "127.0.0.1",
            "user_agent": s.user_agent or "Unknown",
            "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    return resp


@router.post("/sessions/revoke")
def revoke_session(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually revoke and deactivate a specific active user session."""
    session_id_str = body.get("session_id")
    if not session_id_str:
        raise HTTPException(status_code=400, detail="Missing session_id")
        
    try:
        session_id = uuid.UUID(session_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    session = db.query(UserSession).filter(UserSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    roles = [r.name for r in current_user.roles]
    if "Admin" not in roles and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this session")

    session.is_active = False
    
    # Revoke refresh token records corresponding to this session key
    from models.user import RefreshToken
    db.query(RefreshToken).filter(
        RefreshToken.user_id == session.user_id,
        RefreshToken.token == session.session_key
    ).update({"is_revoked": True})
    
    db.commit()

    # Log revocation in audit trail
    audit = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action="SESSION_REVOKE",
        resource=f"Session_{session_id}",
        result="SUCCESS"
    )
    db.add(audit)
    db.commit()

    return {"message": "Session successfully revoked"}


@router.post("/test")
def trigger_security_validation_tests(
    current_user: User = Depends(check_permissions(["Admin"])),
    db: Session = Depends(get_db)
):
    """Trigger the automated OWASP safety suite execution and export new PDF reports."""
    checker = SecurityChecker(db)
    test_summary = checker.execute_security_tests()
    return test_summary


@router.get("/report/download")
def download_security_pdf_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the generated PDF security scan report file."""
    pdf_path = os.path.join(REPORTS_DIR, "Security_Report.pdf")
    
    # Re-generate if missing
    if not os.path.exists(pdf_path):
        checker = SecurityChecker(db)
        checker.execute_security_tests()
        
    if not os.path.exists(pdf_path):
        err_path = pdf_path.replace(".pdf", "_error.txt")
        if os.path.exists(err_path):
            with open(err_path, "r") as f:
                err_msg = f.read()
            raise HTTPException(status_code=503, detail=err_msg)
        raise HTTPException(status_code=404, detail="PDF report could not be compiled.")
        
    return FileResponse(
        pdf_path, 
        media_type="application/pdf", 
        filename="RedactAI_Security_Report.pdf"
    )
