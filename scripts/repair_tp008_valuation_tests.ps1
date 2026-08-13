$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-008 Valuation Test Repair" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$root = (Get-Location).Path
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$testFile = Join-Path $backend "app\tests\test_valuation.py"

# ============================================================
# 1. Validate
# ============================================================

Write-Host "[1/4] Validating project..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    throw "Run this script from D:\tradepilot-ai"
}

if (-not (Test-Path $python)) {
    throw "Backend Python environment not found."
}

if (-not (Test-Path $testFile)) {
    throw "Valuation test file not found."
}

Write-Host "Project: OK" -ForegroundColor Green


# ============================================================
# 2. Make valuation tests isolated
# ============================================================

Write-Host ""
Write-Host "[2/4] Making valuation tests fully isolated..." -ForegroundColor Cyan

$content = Get-Content $testFile -Raw

# Replace create_test_user() with a version that always
# removes existing holdings for the test user.
$startMarker = "def create_test_user():"
$endMarker = "def auth_headers():"

$startIndex = $content.IndexOf($startMarker)
$endIndex = $content.IndexOf($endMarker)

if ($startIndex -lt 0 -or $endIndex -lt 0 -or $endIndex -le $startIndex) {
    throw "Could not locate create_test_user function."
}

$newCreateUser = @'
def create_test_user():
    db = SessionLocal()

    try:
        existing = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        if existing:
            user_id = existing.id

            db.query(Holding).filter(
                Holding.user_id == user_id
            ).delete(
                synchronize_session=False
            )

            db.commit()

        else:
            user = User(
                full_name="Valuation User",
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            user_id = user.id

        return user_id

    finally:
        db.close()


'@

$content = `
    $content.Substring(0, $startIndex) +
    $newCreateUser +
    $content.Substring($endIndex)

# Also ensure the multiple-holdings test does not depend on
# previous test state.
$target = @'
        db.add_all(
            [
                Holding(
                    user_id=user.id,
                    symbol="AAA",
                    quantity=10,
                    average_buy_price=100,
                ),
                Holding(
                    user_id=user.id,
                    symbol="BBB",
                    quantity=20,
                    average_buy_price=50,
                ),
            ]
        )
'@

$replacement = @'
        db.query(Holding).filter(
            Holding.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.add_all(
            [
                Holding(
                    user_id=user.id,
                    symbol="AAA",
                    quantity=10,
                    average_buy_price=100,
                ),
                Holding(
                    user_id=user.id,
                    symbol="BBB",
                    quantity=20,
                    average_buy_price=50,
                ),
            ]
        )
'@

if ($content.Contains($target)) {
    $content = $content.Replace(
        $target,
        $replacement
    )
}

$content = $content.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $testFile),
    $content,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "Valuation tests are now isolated." -ForegroundColor Green


# ============================================================
# 3. Run valuation tests
# ============================================================

Write-Host ""
Write-Host "[3/4] Running valuation tests..." -ForegroundColor Cyan

Push-Location $backend

try {

    & $python -m pytest app/tests/test_valuation.py

    if ($LASTEXITCODE -ne 0) {
        throw "Valuation tests failed."
    }

}
finally {
    Pop-Location
}

Write-Host "Valuation tests: PASS" -ForegroundColor Green


# ============================================================
# 4. Run complete backend suite
# ============================================================

Write-Host ""
Write-Host "[4/4] Running complete backend test suite..." -ForegroundColor Cyan

Push-Location $backend

try {

    & $python -m pytest

    if ($LASTEXITCODE -ne 0) {
        throw "Complete backend test suite failed."
    }

}
finally {
    Pop-Location
}

Write-Host "Backend tests: PASS" -ForegroundColor Green

Write-Host ""
Write-Host "Running Git validation..." -ForegroundColor Cyan

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host "git diff --check: PASS" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " TP-008 TEST REPAIR SUCCESSFUL" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Valuation tests: PASS" -ForegroundColor Green
Write-Host "Complete backend tests: PASS" -ForegroundColor Green
Write-Host "Git validation: PASS" -ForegroundColor Green

Write-Host ""
Write-Host "No Git commit or push performed." -ForegroundColor Yellow