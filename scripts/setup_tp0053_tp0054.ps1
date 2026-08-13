$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-005.3 + TP-005.4" -ForegroundColor Cyan
Write-Host " Registration + Login API" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = (Get-Location).Path
$backendRoot = Join-Path $projectRoot "backend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

# ============================================================
# 1. Validate project
# ============================================================

Write-Host "[1/8] Validating project..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    throw "Run this script from D:\tradepilot-ai"
}

if (-not (Test-Path $backendRoot)) {
    throw "Backend directory not found."
}

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found."
}

Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: $(& $python --version)" -ForegroundColor Green


# ============================================================
# 2. Validate TP-005.1 and TP-005.2
# ============================================================

Write-Host ""
Write-Host "[2/8] Validating authentication foundation..." -ForegroundColor Cyan

$securityFile = Join-Path $backendRoot "app\core\security.py"
$authServiceFile = Join-Path $backendRoot "app\services\auth_service.py"

if (-not (Test-Path $securityFile)) {
    throw "TP-005.1 security.py not found."
}

if (-not (Test-Path $authServiceFile)) {
    throw "TP-005.2 auth_service.py not found."
}

$security = Get-Content $securityFile -Raw
$authService = Get-Content $authServiceFile -Raw

if (
    $security -notmatch "hash_password" -or
    $security -notmatch "verify_password"
) {
    throw "TP-005.1 security functions are missing."
}

if (
    $authService -notmatch "get_user_by_email" -or
    $authService -notmatch "authenticate_user"
) {
    throw "TP-005.2 authentication service is incomplete."
}

Write-Host "TP-005.1: OK" -ForegroundColor Green
Write-Host "TP-005.2: OK" -ForegroundColor Green


# ============================================================
# 3. Install required API dependencies
# ============================================================

Write-Host ""
Write-Host "[3/8] Installing authentication dependencies..." -ForegroundColor Cyan

& $python -m pip install "pwdlib[argon2]" "PyJWT" "email-validator"

if ($LASTEXITCODE -ne 0) {
    throw "Authentication dependency installation failed."
}

Write-Host "Authentication dependencies: OK" -ForegroundColor Green


# ============================================================
# 4. Create authentication schemas
# ============================================================

Write-Host ""
Write-Host "[4/8] Creating authentication schemas..." -ForegroundColor Cyan

$schemasDir = Join-Path $backendRoot "app\schemas"
$authSchemaFile = Join-Path $schemasDir "auth.py"

New-Item -ItemType Directory -Force $schemasDir | Out-Null

$schemaContent = @'
from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
'@

if (Test-Path $authSchemaFile) {

    Write-Host "auth.py already exists. Replacing it with the validated schema implementation." -ForegroundColor Yellow

}

Set-Content `
    -Path $authSchemaFile `
    -Value $schemaContent `
    -Encoding UTF8

Write-Host "Authentication schemas ready." -ForegroundColor Green


# ============================================================
# 5. Create/update authentication service
# ============================================================

Write-Host ""
Write-Host "[5/8] Preparing authentication service..." -ForegroundColor Cyan

$authServiceContent = @'
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


JWT_ALGORITHM = "HS256"


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email address, or None when the user does not exist."""

    normalized_email = email.strip().lower()

    statement = select(User).where(
        User.email == normalized_email
    )

    return db.execute(statement).scalar_one_or_none()


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user using email and password."""

    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    return user


def create_user(
    db: Session,
    full_name: str,
    email: str,
    password: str,
) -> User:
    """Create a user with a securely hashed password."""

    user = User(
        full_name=full_name.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise

    db.refresh(user)

    return user


def create_access_token(
    user_id: int,
    secret_key: str,
    expires_minutes: int = 60,
) -> str:
    """Create a JWT access token."""

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=JWT_ALGORITHM,
    )
'@

Set-Content `
    -Path $authServiceFile `
    -Value $authServiceContent `
    -Encoding UTF8

Write-Host "Authentication service ready." -ForegroundColor Green


# ============================================================
# 6. Create auth API and repair main.py
# ============================================================

Write-Host ""
Write-Host "[6/8] Creating authentication API and registering router..." -ForegroundColor Cyan

$apiDir = Join-Path $backendRoot "app\api\v1"
$authApiFile = Join-Path $apiDir "auth.py"

New-Item -ItemType Directory -Force $apiDir | Out-Null

$authApiContent = @'
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate
from app.schemas.user import UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_email,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = get_user_by_email(
        db,
        user_data.email,
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    return create_user(
        db=db,
        full_name=user_data.full_name,
        email=user_data.email,
        password=user_data.password,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        credentials.email,
        credentials.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret_key = os.getenv(
        "TRADEPILOT_JWT_SECRET",
        "development-only-secret-change-before-production",
    )

    access_token = create_access_token(
        user_id=user.id,
        secret_key=secret_key,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
'@

Set-Content `
    -Path $authApiFile `
    -Value $authApiContent `
    -Encoding UTF8

Write-Host "Created app\api\v1\auth.py" -ForegroundColor Green


# ------------------------------------------------------------
# Repair main.py using complete known-good content.
# ------------------------------------------------------------

$mainFile = Join-Path $backendRoot "main.py"

$mainContent = @'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.db.init_db import init_db


app = FastAPI(
    title="TradePilot AI",
    description="AI-powered stock portfolio tracking and analysis platform",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(
    users_router,
    prefix="/api/v1",
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {
        "message": "TradePilot AI API is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }
'@

Set-Content `
    -Path $mainFile `
    -Value $mainContent `
    -Encoding UTF8

Write-Host "main.py repaired and authentication router registered." -ForegroundColor Green


# ============================================================
# 7. Create authentication API tests
# ============================================================

Write-Host ""
Write-Host "[7/8] Creating authentication API tests..." -ForegroundColor Cyan

$testsDir = Join-Path $backendRoot "app\tests"
$testFile = Join-Path $testsDir "test_auth_api.py"

New-Item -ItemType Directory -Force $testsDir | Out-Null

$testContent = @'
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User
from main import app


client = TestClient(app)


def clean_user(email: str):
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == email
        ).first()

        if user:
            db.delete(user)
            db.commit()

    finally:
        db.close()


def test_register_user():
    email = "register-test@example.com"

    clean_user(email)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Register Test",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == email
    assert data["full_name"] == "Register Test"
    assert "password" not in data
    assert "password_hash" not in data

    clean_user(email)


def test_duplicate_registration_returns_conflict():
    email = "duplicate-test@example.com"

    clean_user(email)

    first = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Duplicate Test",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert first.status_code == 201

    second = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Duplicate Test",
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert second.status_code == 409

    clean_user(email)


def test_register_rejects_short_password():
    email = "short-password@example.com"

    clean_user(email)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Short Password",
            "email": email,
            "password": "short",
        },
    )

    assert response.status_code == 422

    clean_user(email)


def test_login_returns_jwt():
    email = "login-test@example.com"

    clean_user(email)

    db = SessionLocal()

    try:
        user = User(
            full_name="Login Test",
            email=email,
            password_hash=hash_password(
                "TestPassword123!"
            ),
        )

        db.add(user)
        db.commit()

    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert isinstance(
        data["access_token"],
        str,
    )
    assert len(data["access_token"]) > 20

    clean_user(email)


def test_login_rejects_wrong_password():
    email = "wrong-password@example.com"

    clean_user(email)

    db = SessionLocal()

    try:
        user = User(
            full_name="Wrong Password Test",
            email=email,
            password_hash=hash_password(
                "TestPassword123!"
            ),
        )

        db.add(user)
        db.commit()

    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401

    clean_user(email)


def test_login_rejects_unknown_user():
    email = "unknown-user@example.com"

    clean_user(email)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401
'@

Set-Content `
    -Path $testFile `
    -Value $testContent `
    -Encoding UTF8

Write-Host "Created authentication API tests." -ForegroundColor Green


# ============================================================
# 8. Validate and run complete test suite
# ============================================================

Write-Host ""
Write-Host "[8/8] Running complete backend test suite..." -ForegroundColor Cyan

Push-Location $backendRoot

try {

    # First verify main.py can be imported.
    & $python -c "from main import app; print('FastAPI application import: PASS')"

    if ($LASTEXITCODE -ne 0) {
        throw "FastAPI application import failed."
    }

    & $python -m pytest --basetemp ".test-tmp-tp0053-0054"

    if ($LASTEXITCODE -ne 0) {
        throw "Backend tests failed."
    }

}
finally {
    Pop-Location
}


# ============================================================
# Update requirements.txt
# ============================================================

Write-Host ""
Write-Host "Updating requirements.txt..." -ForegroundColor Cyan

$requirementsFile = Join-Path $backendRoot "requirements.txt"
$requirements = Get-Content $requirementsFile

$emailValidatorVersion = & $python -c "import importlib.metadata as m; print(m.version('email-validator'))"

if (-not ($requirements -match "^email-validator==")) {

    Add-Content `
        -Path $requirementsFile `
        -Value "email-validator==$emailValidatorVersion"

    Write-Host "Added email-validator==$emailValidatorVersion" -ForegroundColor Green

}
else {

    Write-Host "email-validator already exists." -ForegroundColor Yellow
}


# ============================================================
# Final summary
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " TP-005.3 + TP-005.4 COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Write-Host "Implemented:" -ForegroundColor Cyan
Write-Host "  - User registration"
Write-Host "  - Secure password hashing"
Write-Host "  - Duplicate email protection"
Write-Host "  - Login"
Write-Host "  - JWT access token generation"
Write-Host "  - Invalid credential handling"
Write-Host ""

Write-Host "Endpoints:" -ForegroundColor Cyan
Write-Host "  POST /api/v1/auth/register"
Write-Host "  POST /api/v1/auth/login"
Write-Host ""

Write-Host "Validation:" -ForegroundColor Cyan
Write-Host "  - FastAPI import: PASS"
Write-Host "  - Authentication tests: PASS"
Write-Host "  - Existing tests: PASS"
Write-Host ""

Write-Host "No Git commit or push was performed." -ForegroundColor Cyan
Write-Host ""