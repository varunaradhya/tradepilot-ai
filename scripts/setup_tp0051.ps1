$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-005.1 Setup" -ForegroundColor Cyan
Write-Host " Authentication Security Foundation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# 1. Repository validation
# ============================================================

Write-Host "[1/8] Checking TradePilot repository..." -ForegroundColor Cyan

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
# 2. Python virtual environment validation
# ============================================================

Write-Host ""
Write-Host "[2/8] Checking Python virtual environment..." -ForegroundColor Cyan

$projectRoot = (Get-Location).Path
$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "ERROR: Python virtual environment not found:" -ForegroundColor Red
    Write-Host $python -ForegroundColor Yellow
    exit 1
}

$pythonVersion = & $python --version

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not execute the backend Python interpreter." -ForegroundColor Red
    exit 1
}

Write-Host "Python: $pythonVersion" -ForegroundColor Green
Write-Host "Virtual environment: OK" -ForegroundColor Green


# ============================================================
# 3. Install security dependencies
# ============================================================

Write-Host ""
Write-Host "[3/8] Installing security dependencies..." -ForegroundColor Cyan

& $python -m pip install "pwdlib[argon2]" "PyJWT"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Security dependency installation failed." -ForegroundColor Red
    exit 1
}

Write-Host "Security dependencies installed." -ForegroundColor Green


# ============================================================
# 4. Create / validate security module
# ============================================================

Write-Host ""
Write-Host "[4/8] Creating security module..." -ForegroundColor Cyan

$coreDir = Join-Path $projectRoot "backend\app\core"
$initFile = Join-Path $coreDir "__init__.py"
$securityFile = Join-Path $coreDir "security.py"

New-Item -ItemType Directory -Force $coreDir | Out-Null

if (-not (Test-Path $initFile)) {
    New-Item -ItemType File -Path $initFile | Out-Null
    Write-Host "Created app\core\__init__.py" -ForegroundColor Green
}
else {
    Write-Host "app\core\__init__.py already exists." -ForegroundColor Yellow
}

# Expected security implementation.
$securityContent = @'
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plain-text password."""
    return password_hash.verify(password, hashed_password)
'@

if (Test-Path $securityFile) {

    Write-Host "security.py already exists. Validating it..." -ForegroundColor Yellow

    $existingSecurity = Get-Content $securityFile -Raw

    # Do not compare exact formatting.
    # Validate that the required implementation elements exist.
    $hasPasswordHash = $existingSecurity -match "PasswordHash"
    $hasRecommended = $existingSecurity -match "PasswordHash\.recommended"
    $hasHashFunction = $existingSecurity -match "def\s+hash_password"
    $hasVerifyFunction = $existingSecurity -match "def\s+verify_password"

    if (
        -not $hasPasswordHash -or
        -not $hasRecommended -or
        -not $hasHashFunction -or
        -not $hasVerifyFunction
    ) {
        Write-Host ""
        Write-Host "ERROR: Existing security.py does not contain the required implementation." -ForegroundColor Red
        Write-Host "The script will NOT overwrite it automatically." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Existing security.py contains the required implementation." -ForegroundColor Green
}
else {

    Set-Content `
        -Path $securityFile `
        -Value $securityContent `
        -Encoding UTF8

    Write-Host "Created app\core\security.py" -ForegroundColor Green
}


# ============================================================
# 5. Validate imports and Python syntax
# ============================================================

Write-Host ""
Write-Host "[5/8] Validating security module..." -ForegroundColor Cyan

Push-Location (Join-Path $projectRoot "backend")

try {

    & $python -c "from app.core.security import hash_password, verify_password; import jwt; print('Security imports: PASS')"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Security module import failed." -ForegroundColor Red
        exit 1
    }

}
finally {
    Pop-Location
}


# ============================================================
# 6. Test Argon2 password hashing
# ============================================================

Write-Host ""
Write-Host "[6/8] Testing Argon2 password hashing..." -ForegroundColor Cyan

$testFile = Join-Path $projectRoot "backend\tp0051_security_test.py"

$testContent = @'
from app.core.security import hash_password, verify_password


password = "TestPassword123!"

hashed_password = hash_password(password)

assert hashed_password != password
assert hashed_password.startswith("$argon2")

assert verify_password(
    password,
    hashed_password,
)

assert not verify_password(
    "WrongPassword123!",
    hashed_password,
)

print("Password hashing test: PASS")
'@

Set-Content `
    -Path $testFile `
    -Value $testContent `
    -Encoding UTF8

try {

    Push-Location (Join-Path $projectRoot "backend")

    try {

        & $python "tp0051_security_test.py"

        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Password hashing validation failed." -ForegroundColor Red
            exit 1
        }

    }
    finally {
        Pop-Location
    }

}
finally {

    if (Test-Path $testFile) {
        Remove-Item $testFile -Force -ErrorAction SilentlyContinue
    }
}


# ============================================================
# 7. Update requirements.txt
# ============================================================

Write-Host ""
Write-Host "[7/8] Updating requirements.txt..." -ForegroundColor Cyan

$requirementsFile = Join-Path $projectRoot "backend\requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-Host "ERROR: backend\requirements.txt not found." -ForegroundColor Red
    exit 1
}

$requirements = Get-Content $requirementsFile

# Get installed versions.
$pwdlibVersion = & $python -c "import importlib.metadata as m; print(m.version('pwdlib'))"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not determine pwdlib version." -ForegroundColor Red
    exit 1
}

$jwtVersion = & $python -c "import importlib.metadata as m; print(m.version('PyJWT'))"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not determine PyJWT version." -ForegroundColor Red
    exit 1
}

# Add pwdlib if missing.
if (-not ($requirements -match "^pwdlib==")) {

    Add-Content `
        -Path $requirementsFile `
        -Value "pwdlib==$pwdlibVersion"

    Write-Host "Added pwdlib==$pwdlibVersion" -ForegroundColor Green
}
else {
    Write-Host "pwdlib already exists in requirements.txt" -ForegroundColor Yellow
}

# Add PyJWT if missing.
if (-not ($requirements -match "^PyJWT==")) {

    Add-Content `
        -Path $requirementsFile `
        -Value "PyJWT==$jwtVersion"

    Write-Host "Added PyJWT==$jwtVersion" -ForegroundColor Green
}
else {
    Write-Host "PyJWT already exists in requirements.txt" -ForegroundColor Yellow
}


# ============================================================
# 8. Run complete backend test suite
# ============================================================

Write-Host ""
Write-Host "[8/8] Running backend tests..." -ForegroundColor Cyan

$testTemp = Join-Path $projectRoot "backend\.test-tmp-tp0051"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $testTemp | Out-Null

Push-Location (Join-Path $projectRoot "backend")

try {

    & $python -m pytest --basetemp ".test-tmp-tp0051"

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "ERROR: Backend test suite failed." -ForegroundColor Red
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
Write-Host " TP-005.1 COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Security foundation:" -ForegroundColor Cyan
Write-Host "  - pwdlib installed"
Write-Host "  - Argon2 support installed"
Write-Host "  - PyJWT installed"
Write-Host "  - Password hashing verified"
Write-Host "  - Password verification verified"
Write-Host ""

Write-Host "Files:" -ForegroundColor Cyan
Write-Host "  - backend/app/core/__init__.py"
Write-Host "  - backend/app/core/security.py"
Write-Host ""

Write-Host "Validation:" -ForegroundColor Cyan
Write-Host "  - Security imports: PASS"
Write-Host "  - Argon2 hashing: PASS"
Write-Host "  - Backend pytest suite: PASS"
Write-Host ""

Write-Host "No changes made to:" -ForegroundColor Cyan
Write-Host "  - User model"
Write-Host "  - Existing API endpoints"
Write-Host "  - Frontend"
Write-Host "  - Docker"
Write-Host "  - Git history"
Write-Host "  - GitHub"
Write-Host ""

Write-Host "TP-005.1 is ready for review." -ForegroundColor Green
Write-Host ""