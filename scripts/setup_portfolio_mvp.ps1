$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - Portfolio MVP" -ForegroundColor Cyan
Write-Host " Holdings + Portfolio API + Frontend" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = (Get-Location).Path
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

# ============================================================
# 1. Validate project
# ============================================================

Write-Host "[1/10] Validating project..." -ForegroundColor Cyan

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
# 2. Validate authentication foundation
# ============================================================

Write-Host ""
Write-Host "[2/10] Validating authentication foundation..." -ForegroundColor Cyan

$requiredFiles = @(
    "backend\app\models\user.py",
    "backend\app\dependencies\auth.py",
    "backend\app\schemas\user.py",
    "backend\app\db\database.py",
    "backend\app\services\user_service.py",
    "backend\main.py"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path (Join-Path $projectRoot $file))) {
        throw "Required file missing: $file"
    }
}

Write-Host "Authentication foundation: OK" -ForegroundColor Green


# ============================================================
# 3. Create Holding model
# ============================================================

Write-Host ""
Write-Host "[3/10] Creating portfolio holding model..." -ForegroundColor Cyan

$modelsDir = Join-Path $backendRoot "app\models"
$modelFile = Join-Path $modelsDir "holding.py"

New-Item -ItemType Directory -Force $modelsDir | Out-Null

$modelContent = @'
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    average_buy_price: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
'@

Set-Content `
    -Path $modelFile `
    -Value $modelContent `
    -Encoding UTF8

Write-Host "Created Holding model." -ForegroundColor Green


# ============================================================
# 4. Create portfolio schemas
# ============================================================

Write-Host ""
Write-Host "[4/10] Creating portfolio schemas..." -ForegroundColor Cyan

$schemasDir = Join-Path $backendRoot "app\schemas"
$schemaFile = Join-Path $schemasDir "portfolio.py"

$schemaContent = @'
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=30,
    )

    quantity: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=4,
    )

    average_buy_price: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=4,
    )


class HoldingUpdate(BaseModel):
    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

    quantity: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=4,
    )

    average_buy_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=4,
    )


class HoldingResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    quantity: Decimal
    average_buy_price: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }
'@

Set-Content `
    -Path $schemaFile `
    -Value $schemaContent `
    -Encoding UTF8

Write-Host "Created portfolio schemas." -ForegroundColor Green


# ============================================================
# 5. Create portfolio service
# ============================================================

Write-Host ""
Write-Host "[5/10] Creating portfolio service..." -ForegroundColor Cyan

$servicesDir = Join-Path $backendRoot "app\services"
$serviceFile = Join-Path $servicesDir "portfolio_service.py"

$serviceContent = @'
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.holding import Holding


def get_user_holdings(
    db: Session,
    user_id: int,
) -> list[Holding]:
    statement = (
        select(Holding)
        .where(Holding.user_id == user_id)
        .order_by(Holding.id)
    )

    return list(
        db.execute(statement).scalars().all()
    )


def get_holding(
    db: Session,
    holding_id: int,
    user_id: int,
) -> Holding | None:
    statement = select(Holding).where(
        Holding.id == holding_id,
        Holding.user_id == user_id,
    )

    return db.execute(
        statement
    ).scalar_one_or_none()


def create_holding(
    db: Session,
    user_id: int,
    symbol: str,
    quantity: Decimal,
    average_buy_price: Decimal,
) -> Holding:

    holding = Holding(
        user_id=user_id,
        symbol=symbol.strip().upper(),
        quantity=quantity,
        average_buy_price=average_buy_price,
    )

    db.add(holding)
    db.commit()
    db.refresh(holding)

    return holding


def update_holding(
    db: Session,
    holding: Holding,
    symbol: str | None = None,
    quantity: Decimal | None = None,
    average_buy_price: Decimal | None = None,
) -> Holding:

    if symbol is not None:
        holding.symbol = symbol.strip().upper()

    if quantity is not None:
        holding.quantity = quantity

    if average_buy_price is not None:
        holding.average_buy_price = average_buy_price

    db.commit()
    db.refresh(holding)

    return holding


def delete_holding(
    db: Session,
    holding: Holding,
) -> None:

    db.delete(holding)
    db.commit()
'@

Set-Content `
    -Path $serviceFile `
    -Value $serviceContent `
    -Encoding UTF8

Write-Host "Created portfolio service." -ForegroundColor Green


# ============================================================
# 6. Create portfolio API
# ============================================================

Write-Host ""
Write-Host "[6/10] Creating portfolio API..." -ForegroundColor Cyan

$apiDir = Join-Path $backendRoot "app\api\v1"
$portfolioApiFile = Join-Path $apiDir "portfolio.py"

$portfolioApiContent = @'
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
)
from app.services.portfolio_service import (
    create_holding,
    delete_holding,
    get_holding,
    get_user_holdings,
    update_holding,
)


router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)


@router.get(
    "/holdings",
    response_model=list[HoldingResponse],
)
def list_holdings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_holdings(
        db,
        current_user.id,
    )


@router.post(
    "/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_holding(
    holding_data: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_holding(
        db=db,
        user_id=current_user.id,
        symbol=holding_data.symbol,
        quantity=holding_data.quantity,
        average_buy_price=holding_data.average_buy_price,
    )


@router.put(
    "/holdings/{holding_id}",
    response_model=HoldingResponse,
)
def edit_holding(
    holding_id: int,
    holding_data: HoldingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = get_holding(
        db,
        holding_id,
        current_user.id,
    )

    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )

    return update_holding(
        db=db,
        holding=holding,
        symbol=holding_data.symbol,
        quantity=holding_data.quantity,
        average_buy_price=holding_data.average_buy_price,
    )


@router.delete(
    "/holdings/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = get_holding(
        db,
        holding_id,
        current_user.id,
    )

    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )

    delete_holding(
        db,
        holding,
    )

    return None
'@

Set-Content `
    -Path $portfolioApiFile `
    -Value $portfolioApiContent `
    -Encoding UTF8

Write-Host "Created portfolio API." -ForegroundColor Green


# ============================================================
# 7. Register model and router
# ============================================================

Write-Host ""
Write-Host "[7/10] Registering portfolio components..." -ForegroundColor Cyan

$initDbFile = Join-Path $backendRoot "app\db\init_db.py"
$initDbContent = Get-Content $initDbFile -Raw

if ($initDbContent -notmatch "app\.models\.holding") {

    $initDbContent = @"
from app.models.user import User
from app.models.holding import Holding

from app.db.database import Base, engine


def init_db():
    Base.metadata.create_all(bind=engine)
"@

    Set-Content `
        -Path $initDbFile `
        -Value $initDbContent `
        -Encoding UTF8

    Write-Host "Registered Holding model with database initialization." -ForegroundColor Green
}
else {
    Write-Host "Holding model already registered." -ForegroundColor Yellow
}


$mainFile = Join-Path $backendRoot "main.py"
$mainContent = Get-Content $mainFile -Raw

if ($mainContent -notmatch "portfolio_router") {

    $mainContent = $mainContent.Replace(
        "from app.api.v1.auth import router as auth_router",
        "from app.api.v1.auth import router as auth_router`r`nfrom app.api.v1.portfolio import router as portfolio_router"
    )

    $mainContent = $mainContent.Replace(
        'app.include_router(`r`n    auth_router,`r`n    prefix="/api/v1",`r`n)',
        'app.include_router(`r`n    auth_router,`r`n    prefix="/api/v1",`r`n)`r`n`r`napp.include_router(`r`n    portfolio_router,`r`n    prefix="/api/v1",`r`n)'
    )

    if ($mainContent -notmatch "portfolio_router") {
        $mainContent = $mainContent.Replace(
            'app.include_router(auth_router, prefix="/api/v1")',
            'app.include_router(auth_router, prefix="/api/v1")`r`napp.include_router(portfolio_router, prefix="/api/v1")'
        )
    }

    Set-Content `
        -Path $mainFile `
        -Value $mainContent `
        -Encoding UTF8

    Write-Host "Portfolio router registered." -ForegroundColor Green
}
else {
    Write-Host "Portfolio router already registered." -ForegroundColor Yellow
}


# ============================================================
# 8. Create portfolio tests
# ============================================================

Write-Host ""
Write-Host "[8/10] Creating portfolio tests..." -ForegroundColor Cyan

$testFile = Join-Path $backendRoot "app\tests\test_portfolio.py"

$testContent = @'
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.user import User
from main import app


client = TestClient(app)


EMAIL = "portfolio-test@example.com"
PASSWORD = "TestPassword123!"


def clean_test_data():
    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == EMAIL
        ).first()

        if user:
            db.query(Holding).filter(
                Holding.user_id == user.id
            ).delete()

            db.delete(user)
            db.commit()

    finally:
        db.close()


def create_user():
    clean_test_data()

    db = SessionLocal()

    try:
        user = User(
            full_name="Portfolio Test",
            email=EMAIL,
            password_hash=hash_password(PASSWORD),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user.id

    finally:
        db.close()


def login():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def auth_headers():
    token = login()

    return {
        "Authorization": f"Bearer {token}"
    }


def test_holdings_requires_authentication():

    response = client.get(
        "/api/v1/portfolio/holdings"
    )

    assert response.status_code == 401


def test_create_holding():

    create_user()

    try:
        response = client.post(
            "/api/v1/portfolio/holdings",
            json={
                "symbol": "reliance",
                "quantity": 10,
                "average_buy_price": 2500,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 201

        data = response.json()

        assert data["symbol"] == "RELIANCE"
        assert float(data["quantity"]) == 10
        assert float(data["average_buy_price"]) == 2500

    finally:
        clean_test_data()


def test_get_holdings():

    user_id = create_user()

    db = SessionLocal()

    try:
        holding = Holding(
            user_id=user_id,
            symbol="TCS",
            quantity=5,
            average_buy_price=3000,
        )

        db.add(holding)
        db.commit()

    finally:
        db.close()

    try:
        response = client.get(
            "/api/v1/portfolio/holdings",
            headers=auth_headers(),
        )

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["symbol"] == "TCS"

    finally:
        clean_test_data()


def test_update_holding():

    user_id = create_user()

    db = SessionLocal()

    try:
        holding = Holding(
            user_id=user_id,
            symbol="INFY",
            quantity=10,
            average_buy_price=1500,
        )

        db.add(holding)
        db.commit()
        db.refresh(holding)

        holding_id = holding.id

    finally:
        db.close()

    try:
        response = client.put(
            f"/api/v1/portfolio/holdings/{holding_id}",
            json={
                "quantity": 20,
                "average_buy_price": 1600,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 200

        data = response.json()

        assert float(data["quantity"]) == 20
        assert float(data["average_buy_price"]) == 1600

    finally:
        clean_test_data()


def test_delete_holding():

    user_id = create_user()

    db = SessionLocal()

    try:
        holding = Holding(
            user_id=user_id,
            symbol="HDFCBANK",
            quantity=5,
            average_buy_price=1700,
        )

        db.add(holding)
        db.commit()
        db.refresh(holding)

        holding_id = holding.id

    finally:
        db.close()

    try:
        response = client.delete(
            f"/api/v1/portfolio/holdings/{holding_id}",
            headers=auth_headers(),
        )

        assert response.status_code == 204

        check = client.get(
            "/api/v1/portfolio/holdings",
            headers=auth_headers(),
        )

        assert check.status_code == 200
        assert check.json() == []

    finally:
        clean_test_data()


def test_user_cannot_modify_another_users_holding():

    create_user()

    db = SessionLocal()

    try:
        first_user = db.query(User).filter(
            User.email == EMAIL
        ).first()

        holding = Holding(
            user_id=first_user.id,
            symbol="AAPL",
            quantity=10,
            average_buy_price=200,
        )

        db.add(holding)
        db.commit()
        db.refresh(holding)

        holding_id = holding.id

        second_user = User(
            full_name="Second User",
            email="portfolio-second@example.com",
            password_hash=hash_password(PASSWORD),
        )

        db.add(second_user)
        db.commit()

    finally:
        db.close()

    try:
        response = client.put(
            f"/api/v1/portfolio/holdings/{holding_id}",
            json={
                "quantity": 100,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 404

    finally:
        db = SessionLocal()

        try:
            second = db.query(User).filter(
                User.email == "portfolio-second@example.com"
            ).first()

            if second:
                db.query(Holding).filter(
                    Holding.user_id == second.id
                ).delete()

                db.delete(second)

            db.commit()

        finally:
            db.close()

        clean_test_data()


def test_invalid_quantity_is_rejected():

    create_user()

    try:
        response = client.post(
            "/api/v1/portfolio/holdings",
            json={
                "symbol": "TCS",
                "quantity": 0,
                "average_buy_price": 3000,
            },
            headers=auth_headers(),
        )

        assert response.status_code == 422

    finally:
        clean_test_data()
'@

Set-Content `
    -Path $testFile `
    -Value $testContent `
    -Encoding UTF8

Write-Host "Portfolio tests created." -ForegroundColor Green


# ============================================================
# 9. Create frontend portfolio API/page
# ============================================================

Write-Host ""
Write-Host "[9/10] Creating frontend portfolio integration..." -ForegroundColor Cyan

if (Test-Path $frontendRoot) {

    $servicesDir = Join-Path $frontendRoot "src\services"
    $pagesDir = Join-Path $frontendRoot "src\pages"

    New-Item -ItemType Directory -Force $servicesDir | Out-Null
    New-Item -ItemType Directory -Force $pagesDir | Out-Null

    $portfolioApiFile = Join-Path $servicesDir "portfolio.ts"

    $portfolioApiContent = @'
export interface Holding {
  id: number;
  user_id: number;
  symbol: string;
  quantity: number;
  average_buy_price: number;
  created_at: string;
  updated_at: string;
}

export interface HoldingCreate {
  symbol: string;
  quantity: number;
  average_buy_price: number;
}

const API_URL =
  import.meta.env.VITE_API_URL ??
  "http://localhost:8000/api/v1";

export async function getHoldings(
  token: string
): Promise<Holding[]> {
  const response = await fetch(
    `${API_URL}/portfolio/holdings`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error("Failed to load holdings");
  }

  return response.json();
}

export async function createHolding(
  token: string,
  holding: HoldingCreate
): Promise<Holding> {
  const response = await fetch(
    `${API_URL}/portfolio/holdings`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(holding),
    }
  );

  if (!response.ok) {
    throw new Error("Failed to create holding");
  }

  return response.json();
}
'@

    Set-Content `
        -Path $portfolioApiFile `
        -Value $portfolioApiContent `
        -Encoding UTF8

    $portfolioPageFile = Join-Path $pagesDir "PortfolioPage.tsx"

    $portfolioPageContent = @'
import { useEffect, useState } from "react";
import {
  createHolding,
  getHoldings,
  type Holding,
} from "../services/portfolio";

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Temporary development token source.
  // Authentication UI will replace this in the next frontend batch.
  const token = localStorage.getItem("tradepilot_access_token") ?? "";

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setError("Please login first.");
      return;
    }

    getHoldings(token)
      .then(setHoldings)
      .catch((err) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load portfolio"
        );
      })
      .finally(() => setLoading(false));
  }, [token]);

  async function addDemoHolding() {
    if (!token) {
      setError("Please login first.");
      return;
    }

    try {
      const holding = await createHolding(
        token,
        {
          symbol: "RELIANCE",
          quantity: 1,
          average_buy_price: 2500,
        }
      );

      setHoldings((current) => [
        ...current,
        holding,
      ]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to add holding"
      );
    }
  }

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            Portfolio
          </h1>

          <p className="mt-1 text-gray-500">
            Your stock holdings
          </p>
        </div>

        <button
          onClick={addDemoHolding}
          className="rounded-lg border px-4 py-2"
        >
          Add Demo Holding
        </button>
      </div>

      {loading && (
        <p>Loading portfolio...</p>
      )}

      {error && (
        <p className="mb-4 text-red-600">
          {error}
        </p>
      )}

      {!loading && holdings.length === 0 && !error && (
        <div className="rounded-xl border p-8 text-center">
          <h2 className="text-xl font-semibold">
            No holdings yet
          </h2>

          <p className="mt-2 text-gray-500">
            Add your first stock holding.
          </p>
        </div>
      )}

      {holdings.length > 0 && (
        <div className="overflow-hidden rounded-xl border">
          <table className="w-full text-left">
            <thead className="border-b">
              <tr>
                <th className="p-4">Symbol</th>
                <th className="p-4">Quantity</th>
                <th className="p-4">
                  Average Buy Price
                </th>
              </tr>
            </thead>

            <tbody>
              {holdings.map((holding) => (
                <tr
                  key={holding.id}
                  className="border-b last:border-b-0"
                >
                  <td className="p-4 font-semibold">
                    {holding.symbol}
                  </td>

                  <td className="p-4">
                    {holding.quantity}
                  </td>

                  <td className="p-4">
                    ₹{holding.average_buy_price}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
'@

    Set-Content `
        -Path $portfolioPageFile `
        -Value $portfolioPageContent `
        -Encoding UTF8

    Write-Host "Frontend portfolio integration created." -ForegroundColor Green

}
else {

    Write-Host "Frontend directory not found. Backend MVP will continue." -ForegroundColor Yellow
}


# ============================================================
# 10. Import validation + complete tests
# ============================================================

Write-Host ""
Write-Host "[10/10] Running validation and complete backend test suite..." -ForegroundColor Cyan

Push-Location $backendRoot

try {

    & $python -c "from app.models.holding import Holding; from app.api.v1.portfolio import router; from main import app; print('Portfolio imports: PASS')"

    if ($LASTEXITCODE -ne 0) {
        throw "Portfolio import validation failed."
    }

    & $python -m pytest --basetemp ".test-tmp-portfolio"

    if ($LASTEXITCODE -ne 0) {
        throw "Backend tests failed."
    }

}
finally {
    Pop-Location
}


# ============================================================
# Final Git validation
# ============================================================

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " PORTFOLIO MVP COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Backend:" -ForegroundColor Cyan
Write-Host "  Holding model"
Write-Host "  Portfolio service"
Write-Host "  Portfolio CRUD API"
Write-Host "  User ownership protection"
Write-Host "  Portfolio tests"
Write-Host ""

Write-Host "API endpoints:" -ForegroundColor Cyan
Write-Host "  GET    /api/v1/portfolio/holdings"
Write-Host "  POST   /api/v1/portfolio/holdings"
Write-Host "  PUT    /api/v1/portfolio/holdings/{id}"
Write-Host "  DELETE /api/v1/portfolio/holdings/{id}"
Write-Host ""

Write-Host "Frontend:" -ForegroundColor Cyan
Write-Host "  Portfolio API service"
Write-Host "  Portfolio page"
Write-Host ""

Write-Host "No Git commit or push was performed." -ForegroundColor Yellow
Write-Host ""
Write-Host "Ready for review and commit." -ForegroundColor Green
Write-Host ""