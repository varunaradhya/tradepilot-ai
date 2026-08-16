from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import ChangePasswordRequest, UserProfileUpdate, UserResponse
from app.services.user_service import get_users

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return get_users(db)

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    profile: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.full_name = profile.full_name.strip()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_current_user_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
