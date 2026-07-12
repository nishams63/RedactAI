"""User profile API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user
from schemas.user import UserProfile, UpdateProfileRequest, ChangePasswordRequest
from schemas.auth import MessageResponse
from services.user import UserService
from models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfile)
def get_my_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get the authenticated user's profile."""
    service = UserService(db)
    return service.get_profile(current_user.id)


@router.put("/me", response_model=UserProfile)
def update_my_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's profile."""
    service = UserService(db)
    return service.update_profile(
        user_id=current_user.id,
        full_name=request.full_name,
        avatar_url=request.avatar_url,
    )


@router.post("/me/change-password", response_model=MessageResponse)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the authenticated user's password."""
    service = UserService(db)
    service.change_password(
        user_id=current_user.id,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return {"message": "Password changed successfully"}
