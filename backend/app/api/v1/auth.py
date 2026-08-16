from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import ForgotPasswordRequest, LoginRequest, TokenResponse, UserCreate
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate_user, create_access_token, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user_data.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    return create_user(db=db, full_name=user_data.full_name, email=user_data.email, password=user_data.password)

@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, credentials.email, credentials.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(user_id=user.id), "token_type": "bearer"}

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Deliberately return the same response whether the account exists or not.
    # Email/token delivery will be attached when SMTP/provider settings are configured.
    _ = get_user_by_email(db, payload.email)
    return {"message": "If an account exists for this email, password reset instructions will be sent."}
