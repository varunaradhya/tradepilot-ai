$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-005.5 to TP-005.8" -ForegroundColor Cyan
Write-Host " JWT Validation + Protected API" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = (Get-Location).Path
$backendRoot = Join-Path $projectRoot "backend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

# ============================================================
# 1. Validate repository and previous authentication work
# ============================================================

Write-Host "[1/10] Validating project and previous authentication work..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    throw "Run this script from D:\tradepilot-ai"
}

if (-not (Test-Path $backendRoot)) {
    throw "backend directory not found."
}

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found."
}

$requiredPreviousFiles = @(
    "backend\app\core\security.py",
    "backend\app\services\auth_service.py",
    "backend\app\api\v1\auth.py",
    "backend\app\schemas\auth.py",
    "backend\app\schemas\user.py",
    "backend\main.py"
)

foreach ($file in $requiredPreviousFiles) {
    if (-not (Test-Path (Join-Path $projectRoot $file))) {
        throw "Required previous file is missing: $file"
    }
}

Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: $(& $python --version)" -ForegroundColor Green
Write-Host "Previous authentication foundation: OK" -ForegroundColor Green


# ============================================================
# 2. Validate JWT dependency and existing service
# ============================================================

Write-Host ""
Write-Host "[2/10] Validating JWT foundation..." -ForegroundColor Cyan

& $python -c "import jwt; print('PyJWT import: PASS')"

if ($LASTEXITCODE -ne 0) {
    throw "PyJWT is not available."
}

$authServiceFile = Join-Path $backendRoot "app\services\auth_service.py"
$authService = Get-Content $authServiceFile -Raw

if ($authService -notmatch "def\s+create_access_token") {
    throw "create_access_token() is missing."
}

Write-Host "JWT dependency: OK" -ForegroundColor Green
Write-Host "Token creation service: OK" -ForegroundColor Green


# ============================================================
# 3. Create application settings module
# ============================================================

Write-Host ""
Write-Host "[3/10] Creating authentication configuration..." -ForegroundColor Cyan

$coreDir = Join-Path $backendRoot "app\core"
$settingsFile = Join-Path $coreDir "config.py"

New-Item -ItemType Directory -Force $coreDir | Out-Null

$configContent = @'
import os


JWT_ALGORITHM = "HS256"

JWT_SECRET_KEY = os.getenv(
    "TRADEPILOT_JWT_SECRET",
    "development-only-secret-change-before-production",
)

JWT_EXPIRE_MINUTES = int(
    os.getenv(
        "TRADEPILOT_JWT_EXPIRE_MINUTES",
        "60",
    )
)
'@

if (-not (Test-Path $settingsFile)) {
    Set-Content `
        -Path $settingsFile `
        -Value $configContent `
        -Encoding UTF8

    Write-Host "Created app\core\config.py" -ForegroundColor Green
}
else {
    Write-Host "config.py already exists. Validating required settings..." -ForegroundColor Yellow

    $existingConfig = Get-Content $settingsFile -Raw

    if (
        $existingConfig -notmatch "JWT_SECRET_KEY" -or
        $existingConfig -notmatch "JWT_ALGORITHM" -or
        $existingConfig -notmatch "JWT_EXPIRE_MINUTES"
    ) {
        throw "Existing config.py does not contain the required JWT settings. It will not be overwritten."
    }

    Write-Host "JWT configuration: OK" -ForegroundColor Green
}


# ============================================================
# 4. Update authentication service to use centralized config
# ============================================================

Write-Host ""
Write-Host "[4/10] Updating authentication token service..." -ForegroundColor Cyan

$serviceContent = @'
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET_KEY,
)
from app.core.security import hash_password, verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email address."""

    normalized_email = email.strip().lower()

    statement = select(User).where(
        User.email == normalized_email
    )

    return db.execute(statement).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Return a user by primary key."""

    return db.get(User, user_id)


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
    expires_minutes: int = JWT_EXPIRE_MINUTES,
) -> str:
    """Create a JWT access token."""

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=expires_minutes
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Validate and decode a JWT access token."""

    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
'@

Set-Content `
    -Path $authServiceFile `
    -Value $serviceContent `
    -Encoding UTF8

Write-Host "Authentication service updated." -ForegroundColor Green


# ============================================================
# 5. Create authentication dependency
# ============================================================

Write-Host ""
Write-Host "[5/10] Creating current-user authentication dependency..." -ForegroundColor Cyan

$dependenciesDir = Join-Path $backendRoot "app\dependencies"
$dependenciesFile = Join-Path $dependenciesDir "auth.py"

New-Item -ItemType Directory -Force $dependenciesDir | Out-Null

$dependencyContent = @'
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.auth_service import (
    decode_access_token,
    get_user_by_id,
)


bearer_scheme = HTTPBearer(
    auto_error=False,
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    """Return the authenticated user from a valid JWT."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_access_token(
            credentials.credentials
        )

        subject = payload.get("sub")

        if subject is None:
            raise credentials_exception

        user_id = int(subject)

    except (
        ValueError,
        TypeError,
        Exception,
    ):
        raise credentials_exception

    user = get_user_by_id(
        db,
        user_id,
    )

    if user is None:
        raise credentials_exception

    return user
'@

if (Test-Path $dependenciesFile) {
    Write-Host "auth.py dependency already exists. Replacing it with the validated implementation." -ForegroundColor Yellow
}

Set-Content `
    -Path $dependenciesFile `
    -Value $dependencyContent `
    -Encoding UTF8

$initFile = Join-Path $dependenciesDir "__init__.py"

if (-not (Test-Path $initFile)) {
    New-Item `
        -ItemType File `
        -Path $initFile | Out-Null
}

Write-Host "Current-user dependency created." -ForegroundColor Green


# ============================================================
# 6. Create protected users endpoint
# ============================================================

Write-Host ""
Write-Host "[6/10] Creating protected current-user endpoint..." -ForegroundColor Cyan

$usersApiFile = Join-Path $backendRoot "app\api\v1\users.py"

$usersApiContent = @'
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.user_service import get_users


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/",
)
def users_status():
    return {
        "message": "User endpoint is working",
    }


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's profile."""

    return current_user


@router.get(
    "/",
    response_model=list[UserResponse],
)
def list_users(
    db: Session = Depends(get_db),
):
    """Return all users."""

    return get_users(db)
'@

# We need to preserve the existing users API behavior while adding /me.
# The original GET "/" is already used by TP-003.9A as the read-only users API.
# Therefore generate a clean combined implementation.

$usersApiContent = @'
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.user_service import get_users


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "/",
    response_model=list[UserResponse],
)
def list_users(
    db: Session = Depends(get_db),
):
    """Return all users."""

    return get_users(db)


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the authenticated user's profile."""

    return current_user
'@

Set-Content `
    -Path $usersApiFile `
    -Value $usersApiContent `
    -Encoding UTF8

Write-Host "Protected /api/v1/users/me endpoint created." -ForegroundColor Green


# ============================================================
# 7. Update login API to use centralized JWT configuration
# ============================================================

Write-Host ""
Write-Host "[7/10] Updating login API..." -ForegroundColor Cyan

$authApiFile = Join-Path $backendRoot "app\api\v1\auth.py"

$authApiContent = @'
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

    access_token = create_access_token(
        user_id=user.id,
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

Write-Host "Login API updated." -ForegroundColor Green


# ============================================================
# 8. Create protected API tests
# ============================================================

Write-Host ""
Write-Host "[8/10] Creating JWT/protected endpoint tests..." -ForegroundColor Cyan

$testFile = Join-Path $backendRoot "app\tests\test_auth_protected.py"

$testContent = @'
import jwt

from fastapi.testclient import TestClient

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.user import User
from main import app


client = TestClient(app)


TEST_EMAIL = "protected-test@example.com"
TEST_PASSWORD = "TestPassword123!"


def clean_user():
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == TEST_EMAIL
        ).first()

        if user:
            db.delete(user)
            db.commit()

    finally:
        db.close()


def create_test_user():
    clean_user()

    db = SessionLocal()

    try:
        user = User(
            full_name="Protected Test User",
            email=TEST_EMAIL,
            password_hash=hash_password(
                TEST_PASSWORD
            ),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id

    finally:
        db.close()


def get_login_token():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def test_valid_jwt_contains_user_subject():
    user_id = create_test_user()

    try:
        token = get_login_token()

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        assert payload["sub"] == str(user_id)
        assert "iat" in payload
        assert "exp" in payload

    finally:
        clean_user()


def test_current_user_requires_authentication():
    response = client.get(
        "/api/v1/users/me"
    )

    assert response.status_code == 401


def test_current_user_returns_authenticated_user():
    create_test_user()

    try:
        token = get_login_token()

        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["email"] == TEST_EMAIL
        assert data["full_name"] == "Protected Test User"

        assert "password" not in data
        assert "password_hash" not in data

    finally:
        clean_user()


def test_current_user_rejects_invalid_token():
    create_test_user()

    try:
        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": "Bearer invalid-token",
            },
        )

        assert response.status_code == 401

    finally:
        clean_user()


def test_current_user_rejects_expired_token():
    create_test_user()

    try:
        token = jwt.encode(
            {
                "sub": "1",
                "iat": 1,
                "exp": 1,
            },
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM,
        )

        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 401

    finally:
        clean_user()


def test_existing_users_endpoint_still_works():
    response = client.get(
        "/api/v1/users/"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
'@

Set-Content `
    -Path $testFile `
    -Value $testContent `
    -Encoding UTF8

Write-Host "Protected endpoint tests created." -ForegroundColor Green


# ============================================================
# 9. Run full test suite
# ============================================================

Write-Host ""
Write-Host "[9/10] Running complete backend test suite..." -ForegroundColor Cyan

Push-Location $backendRoot

try {

    & $python -c "from main import app; print('FastAPI application import: PASS')"

    if ($LASTEXITCODE -ne 0) {
        throw "FastAPI application import failed."
    }

    & $python -m pytest --basetemp ".test-tmp-tp0055-0058"

    if ($LASTEXITCODE -ne 0) {
        throw "Backend test suite failed."
    }

}
finally {
    Pop-Location
}


# ============================================================
# 10. Final validation
# ============================================================

Write-Host ""
Write-Host "[10/10] Final validation..." -ForegroundColor Cyan

Push-Location $backendRoot

try {

    & $python -c "from app.dependencies.auth import get_current_user; from app.services.auth_service import decode_access_token; print('JWT authentication dependency: PASS')"

    if ($LASTEXITCODE -ne 0) {
        throw "JWT dependency validation failed."
    }

}
finally {
    Pop-Location
}

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " TP-005.5 TO TP-005.8 COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Implemented:" -ForegroundColor Cyan
Write-Host "  TP-005.5 - JWT validation and decoding"
Write-Host "  TP-005.6 - Current-user authentication dependency"
Write-Host "  TP-005.7 - Protected /api/v1/users/me endpoint"
Write-Host "  TP-005.8 - JWT/protected endpoint integration tests"
Write-Host ""

Write-Host "Authentication flow:" -ForegroundColor Cyan
Write-Host "  Login"
Write-Host "    -> JWT"
Write-Host "    -> Bearer token"
Write-Host "    -> JWT validation"
Write-Host "    -> Current user"
Write-Host "    -> Protected endpoint"
Write-Host ""

Write-Host "Endpoint:" -ForegroundColor Cyan
Write-Host "  GET /api/v1/users/me"
Write-Host ""

Write-Host "No Git commit or push was performed." -ForegroundColor Yellow
Write-Host ""
Write-Host "Ready for the 4-step commit." -ForegroundColor Green
Write-Host ""