$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - Commit TP-005.5 to TP-005.8" -ForegroundColor Cyan
Write-Host " JWT + Protected API" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = (Get-Location).Path
$backendRoot = Join-Path $projectRoot "backend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

# ============================================================
# 1. Repository validation
# ============================================================

Write-Host "[1/7] Checking repository..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    throw "Run this script from D:\tradepilot-ai"
}

if (-not (Test-Path $python)) {
    throw "Backend Python virtual environment not found."
}

Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: $(& $python --version)" -ForegroundColor Green


# ============================================================
# 2. Verify TP-005.5 to TP-005.8 files
# ============================================================

Write-Host ""
Write-Host "[2/7] Verifying implementation files..." -ForegroundColor Cyan

$requiredFiles = @(
    "backend\app\core\config.py",
    "backend\app\services\auth_service.py",
    "backend\app\dependencies\__init__.py",
    "backend\app\dependencies\auth.py",
    "backend\app\api\v1\users.py",
    "backend\app\api\v1\auth.py",
    "backend\app\tests\test_auth_protected.py",
    "backend\main.py",
    "scripts\setup_tp0055_tp0058.ps1"
)

foreach ($file in $requiredFiles) {

    if (-not (Test-Path (Join-Path $projectRoot $file))) {
        throw "Required file missing: $file"
    }

    Write-Host "  OK: $file" -ForegroundColor Green
}


# ============================================================
# 3. Run complete test suite
# ============================================================

Write-Host ""
Write-Host "[3/7] Running complete backend test suite..." -ForegroundColor Cyan

Push-Location $backendRoot

try {

    & $python -m pytest --basetemp ".test-tmp-commit"

    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed. Commit aborted."
    }

}
finally {
    Pop-Location
}

Write-Host "Tests: PASS" -ForegroundColor Green


# ============================================================
# 4. Git diff validation
# ============================================================

Write-Host ""
Write-Host "[4/7] Running Git validation..." -ForegroundColor Cyan

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed. Commit aborted."
}

Write-Host "git diff --check: PASS" -ForegroundColor Green


# ============================================================
# 5. Stage TP-005.5 to TP-005.8
# ============================================================

Write-Host ""
Write-Host "[5/7] Staging TP-005.5 to TP-005.8..." -ForegroundColor Cyan

git add `
    backend/app/core/config.py `
    backend/app/services/auth_service.py `
    backend/app/dependencies/__init__.py `
    backend/app/dependencies/auth.py `
    backend/app/api/v1/users.py `
    backend/app/api/v1/auth.py `
    backend/app/tests/test_auth_protected.py `
    backend/main.py `
    scripts/setup_tp0055_tp0058.ps1 `
    scripts/commit_tp0055_tp0058.ps1

if ($LASTEXITCODE -ne 0) {
    throw "git add failed."
}

Write-Host "Files staged successfully." -ForegroundColor Green


# ============================================================
# 6. Show staged changes and commit
# ============================================================

Write-Host ""
Write-Host "[6/7] Reviewing staged changes..." -ForegroundColor Cyan

git status --short

Write-Host ""
Write-Host "Creating commit..." -ForegroundColor Yellow

git commit -m "TP-005.5-005.8: Add JWT authentication and protected API"

if ($LASTEXITCODE -ne 0) {
    throw "Git commit failed."
}

Write-Host "Commit created successfully." -ForegroundColor Green


# ============================================================
# 7. Push to GitHub
# ============================================================

Write-Host ""
Write-Host "[7/7] Pushing to GitHub..." -ForegroundColor Cyan

git push

if ($LASTEXITCODE -ne 0) {
    throw "Git push failed."
}

Write-Host "GitHub push: SUCCESS" -ForegroundColor Green


# ============================================================
# Final verification
# ============================================================

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " TP-005.5 TO TP-005.8 COMMITTED + PUSHED" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Latest commit:" -ForegroundColor Cyan
git log --oneline -1

Write-Host ""
Write-Host "Final Git status:" -ForegroundColor Cyan
git status

Write-Host ""
Write-Host "Completed:" -ForegroundColor Green
Write-Host "  TP-005.5 - JWT validation"
Write-Host "  TP-005.6 - Current-user dependency"
Write-Host "  TP-005.7 - Protected endpoint"
Write-Host "  TP-005.8 - Protected API tests"

Write-Host ""
Write-Host "Next batch: TP-005.9 to TP-005.12" -ForegroundColor Yellow
Write-Host ""