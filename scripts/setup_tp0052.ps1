$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-005.2 Setup" -ForegroundColor Cyan
Write-Host " Authentication Service Layer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# 1. Repository validation
# ============================================================

Write-Host "[1/7] Checking repository..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    Write-Host "ERROR: .git directory not found." -ForegroundColor Red
    Write-Host "Run this script from D:\tradepilot-ai" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "backend")) {
    Write-Host "ERROR: backend directory not found." -ForegroundColor Red
    exit 1
}

Write-Host "Repository check: OK" -ForegroundColor Green


# ============================================================
# 2. Python environment validation
# ============================================================

Write-Host ""
Write-Host "[2/7] Checking Python environment..." -ForegroundColor Cyan

$projectRoot = (Get-Location).Path
$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "ERROR: Backend virtual environment not found." -ForegroundColor Red
    exit 1
}

& $python --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python interpreter cannot be executed." -ForegroundColor Red
    exit 1
}

Write-Host "Python environment: OK" -ForegroundColor Green


# ============================================================
# 3. Validate required TP-005.1 security foundation
# ============================================================

Write-Host ""
Write-Host "[3/7] Validating TP-005.1 security foundation..." -ForegroundColor Cyan

$securityFile = Join-Path $projectRoot "backend\app\core\security.py"

if (-not (Test-Path $securityFile)) {
    Write-Host "ERROR: app\core\security.py not found." -ForegroundColor Red
    Write-Host "TP-005.1 must be completed first." -ForegroundColor Yellow
    exit 1
}

$securityContent = Get-Content $securityFile -Raw

if (
    $securityContent -notmatch "PasswordHash" -or
    $securityContent -notmatch "hash_password" -or
    $securityContent -notmatch "verify_password"
) {
    Write-Host "ERROR: Required password security functions were not found." -ForegroundColor Red
    exit 1
}

Write-Host "TP-005.1 security foundation: OK" -ForegroundColor Green


# ============================================================
# 4. Validate User model and database setup
# ============================================================

Write-Host ""
Write-Host "[4/7] Validating User model and database..." -ForegroundColor Cyan

$userModel = Join-Path $projectRoot "backend\app\models\user.py"
$databaseFile = Join-Path $projectRoot "backend\app\db\database.py"

if (-not (Test-Path $userModel)) {
    Write-Host "ERROR: User model not found." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $databaseFile)) {
    Write-Host "ERROR: database.py not found." -ForegroundColor Red
    exit 1
}

$userContent = Get-Content $userModel -Raw

if ($userContent -notmatch "class\s+User") {
    Write-Host "ERROR: User model class not found." -ForegroundColor Red
    exit 1
}

if ($userContent -notmatch "password_hash") {
    Write-Host "ERROR: password_hash field not found in User model." -ForegroundColor Red
    exit 1
}

Write-Host "User model: OK" -ForegroundColor Green
Write-Host "Database module: OK" -ForegroundColor Green


# ============================================================
# 5. Create authentication service
# ============================================================

Write-Host ""
Write-Host "[5/7] Creating authentication service..." -ForegroundColor Cyan

$servicesDir = Join-Path $projectRoot "backend\app\services"
$authServiceFile = Join-Path $servicesDir "auth_service.py"

New-Item -ItemType Directory -Force $servicesDir | Out-Null

$authServiceContent = @'
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email address, or None when the user does not exist."""
    statement = select(User).where(User.email == email)
    return db.execute(statement).scalar_one_or_none()


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user using email and password.

    Returns the User when credentials are valid.
    Returns None when the user does not exist or the password is incorrect.
    """
    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
'@

if (Test-Path $authServiceFile) {

    Write-Host "auth_service.py already exists. Validating existing implementation..." -ForegroundColor Yellow

    $existingService = Get-Content $authServiceFile -Raw

    if (
        $existingService -notmatch "def\s+get_user_by_email" -or
        $existingService -notmatch "def\s+authenticate_user" -or
        $existingService -notmatch "verify_password" -or
        $existingService -notmatch "select\(User\)"
    ) {
        Write-Host ""
        Write-Host "ERROR: Existing auth_service.py does not contain the required implementation." -ForegroundColor Red
        Write-Host "The script will NOT overwrite it." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Existing authentication service is valid." -ForegroundColor Green

}
else {

    Set-Content `
        -Path $authServiceFile `
        -Value $authServiceContent `
        -Encoding UTF8

    Write-Host "Created app\services\auth_service.py" -ForegroundColor Green
}


# ============================================================
# 6. Create authentication service tests
# ============================================================

Write-Host ""
Write-Host "[6/7] Creating authentication service tests..." -ForegroundColor Cyan

$testsDir = Join-Path $projectRoot "backend\app\tests"
$testFile = Join-Path $testsDir "test_auth_service.py"

New-Item -ItemType Directory -Force $testsDir | Out-Null

$testContent = @'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.database import Base
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    get_user_by_email,
)


def create_test_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    return SessionLocal()


def create_test_user(db):
    user = User(
        full_name="Test User",
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def test_get_user_by_email_returns_user():
    db = create_test_session()

    try:
        user = create_test_user(db)

        result = get_user_by_email(
            db,
            "test@example.com",
        )

        assert result is not None
        assert result.id == user.id
        assert result.email == "test@example.com"
    finally:
        db.close()


def test_get_user_by_email_returns_none_for_unknown_email():
    db = create_test_session()

    try:
        result = get_user_by_email(
            db,
            "missing@example.com",
        )

        assert result is None
    finally:
        db.close()


def test_authenticate_user_returns_user_for_valid_credentials():
    db = create_test_session()

    try:
        user = create_test_user(db)

        result = authenticate_user(
            db,
            "test@example.com",
            "TestPassword123!",
        )

        assert result is not None
        assert result.id == user.id
        assert result.email == "test@example.com"
    finally:
        db.close()


def test_authenticate_user_returns_none_for_wrong_password():
    db = create_test_session()

    try:
        create_test_user(db)

        result = authenticate_user(
            db,
            "test@example.com",
            "WrongPassword123!",
        )

        assert result is None
    finally:
        db.close()


def test_authenticate_user_returns_none_for_unknown_email():
    db = create_test_session()

    try:
        result = authenticate_user(
            db,
            "missing@example.com",
            "TestPassword123!",
        )

        assert result is None
    finally:
        db.close()
'@

if (Test-Path $testFile) {

    Write-Host "test_auth_service.py already exists. Validating existing tests..." -ForegroundColor Yellow

    $existingTests = Get-Content $testFile -Raw

    if (
        $existingTests -notmatch "test_get_user_by_email" -or
        $existingTests -notmatch "test_authenticate_user_returns_user" -or
        $existingTests -notmatch "WrongPassword123"
    ) {
        Write-Host ""
        Write-Host "ERROR: Existing test_auth_service.py does not contain the required tests." -ForegroundColor Red
        Write-Host "The script will NOT overwrite it." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Existing authentication tests are valid." -ForegroundColor Green

}
else {

    Set-Content `
        -Path $testFile `
        -Value $testContent `
        -Encoding UTF8

    Write-Host "Created app\tests\test_auth_service.py" -ForegroundColor Green
}


# ============================================================
# 7. Run tests
# ============================================================

Write-Host ""
Write-Host "[7/7] Running backend test suite..." -ForegroundColor Cyan

Push-Location (Join-Path $projectRoot "backend")

try {

    & $python -m pytest --basetemp ".test-tmp-tp0052"

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: Backend tests failed." -ForegroundColor Red
        exit 1
    }

}
finally {
    Pop-Location
}


# ============================================================
# Final summary
# ============================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " TP-005.2 COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Created/verified:" -ForegroundColor Cyan
Write-Host "  backend/app/services/auth_service.py"
Write-Host "  backend/app/tests/test_auth_service.py"
Write-Host ""

Write-Host "Authentication service capabilities:" -ForegroundColor Cyan
Write-Host "  - Find user by email"
Write-Host "  - Verify password hash"
Write-Host "  - Authenticate valid credentials"
Write-Host "  - Reject invalid password"
Write-Host "  - Reject unknown user"
Write-Host ""

Write-Host "Not implemented yet:" -ForegroundColor Yellow
Write-Host "  - Registration API"
Write-Host "  - Login API"
Write-Host "  - JWT tokens"
Write-Host "  - Authentication endpoints"
Write-Host "  - Frontend authentication"
Write-Host ""

Write-Host "No Git commit or push was performed." -ForegroundColor Cyan
Write-Host ""
Write-Host "TP-005.2 is ready for review." -ForegroundColor Green
Write-Host ""