$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - Commit TP-005.3 + TP-005.4" -ForegroundColor Cyan
Write-Host " Registration + Login API" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = (Get-Location).Path

# ============================================================
# 1. Repository validation
# ============================================================

Write-Host "[1/6] Checking repository..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    throw "Run this script from D:\tradepilot-ai"
}

git status

Write-Host "Repository check: OK" -ForegroundColor Green


# ============================================================
# 2. Verify required files
# ============================================================

Write-Host ""
Write-Host "[2/6] Verifying TP-005.3 + TP-005.4 files..." -ForegroundColor Cyan

$requiredFiles = @(
    "backend\app\schemas\auth.py",
    "backend\app\services\auth_service.py",
    "backend\app\api\v1\auth.py",
    "backend\app\tests\test_auth_api.py",
    "backend\main.py",
    "backend\requirements.txt",
    "scripts\setup_tp0053_tp0054.ps1"
)

foreach ($file in $requiredFiles) {

    if (-not (Test-Path (Join-Path $projectRoot $file))) {
        throw "Required file not found: $file"
    }

    Write-Host "  OK: $file" -ForegroundColor Green
}


# ============================================================
# 3. Run final validation
# ============================================================

Write-Host ""
Write-Host "[3/6] Running final validation..." -ForegroundColor Cyan

$python = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Backend Python virtual environment not found."
}

Push-Location (Join-Path $projectRoot "backend")

try {

    Write-Host ""
    Write-Host "Running pytest..." -ForegroundColor Yellow

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
Write-Host "[4/6] Checking Git changes..." -ForegroundColor Cyan

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed. Commit aborted."
}

Write-Host "Git diff check: PASS" -ForegroundColor Green


# ============================================================
# 5. Stage and commit
# ============================================================

Write-Host ""
Write-Host "[5/6] Creating Git commit..." -ForegroundColor Cyan

git add `
    backend/app/schemas/auth.py `
    backend/app/services/auth_service.py `
    backend/app/api/v1/auth.py `
    backend/app/tests/test_auth_api.py `
    backend/main.py `
    backend/requirements.txt `
    scripts/setup_tp0053_tp0054.ps1

if ($LASTEXITCODE -ne 0) {
    throw "git add failed."
}

git status

Write-Host ""
Write-Host "Creating commit..." -ForegroundColor Yellow

git commit -m "TP-005.3-005.4: Add registration and login APIs"

if ($LASTEXITCODE -ne 0) {
    throw "Git commit failed."
}

Write-Host "Commit created successfully." -ForegroundColor Green


# ============================================================
# 6. Push to GitHub
# ============================================================

Write-Host ""
Write-Host "[6/6] Pushing to GitHub..." -ForegroundColor Cyan

git push

if ($LASTEXITCODE -ne 0) {
    throw "Git push failed."
}

Write-Host "GitHub push: SUCCESS" -ForegroundColor Green


# ============================================================
# Final status
# ============================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " TP-005.3 + TP-005.4 COMMITTED + PUSHED" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

git status

Write-Host ""
Write-Host "Latest commit:" -ForegroundColor Cyan
git log --oneline -1

Write-Host ""
Write-Host "Next tasks: TP-005.5 + TP-005.6" -ForegroundColor Yellow
Write-Host ""