$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-008 Portfolio Valuation + Dashboard" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$root = (Get-Location).Path
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path ".git")) {
    throw "Run this script from D:\tradepilot-ai"
}

if (-not (Test-Path $python)) {
    throw "Backend virtual environment not found."
}

# ============================================================
# 1. Validate project
# ============================================================

Write-Host "[1/10] Validating project..." -ForegroundColor Cyan

Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: OK" -ForegroundColor Green


# ============================================================
# 2. Create valuation schemas
# ============================================================

Write-Host ""
Write-Host "[2/10] Creating portfolio valuation schemas..." -ForegroundColor Cyan

$schemasDir = Join-Path $backend "app\schemas"
New-Item -ItemType Directory -Force -Path $schemasDir | Out-Null

$valuationSchema = @'
from pydantic import BaseModel


class HoldingValuation(BaseModel):
    id: int
    symbol: str
    quantity: float
    average_buy_price: float
    invested_amount: float
    current_price: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float


class PortfolioSummary(BaseModel):
    total_invested: float
    current_value: float
    profit_loss: float
    profit_loss_percent: float
    holdings_count: int


class PortfolioValuationResponse(BaseModel):
    summary: PortfolioSummary
    holdings: list[HoldingValuation]
'@

Set-Content `
    -Path (Join-Path $schemasDir "valuation.py") `
    -Value $valuationSchema `
    -Encoding UTF8

Write-Host "Created app\schemas\valuation.py" -ForegroundColor Green


# ============================================================
# 3. Create valuation service
# ============================================================

Write-Host ""
Write-Host "[3/10] Creating portfolio valuation service..." -ForegroundColor Cyan

$servicesDir = Join-Path $backend "app\services"
New-Item -ItemType Directory -Force -Path $servicesDir | Out-Null

$valuationService = @'
from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.services.market_service import (
    MarketDataProviderError,
    get_quote,
)


def calculate_portfolio_valuation(
    db: Session,
    user_id: int,
):
    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id)
        .order_by(Holding.symbol.asc())
        .all()
    )

    valuation_holdings = []

    total_invested = 0.0
    current_value = 0.0

    for holding in holdings:

        invested_amount = (
            float(holding.quantity)
            * float(holding.average_buy_price)
        )

        try:
            quote = get_quote(holding.symbol)
            current_price = float(quote.price)

        except MarketDataProviderError:
            current_price = float(holding.average_buy_price)

        holding_current_value = (
            float(holding.quantity)
            * current_price
        )

        profit_loss = (
            holding_current_value
            - invested_amount
        )

        profit_loss_percent = (
            (profit_loss / invested_amount) * 100
            if invested_amount != 0
            else 0.0
        )

        valuation_holdings.append(
            {
                "id": holding.id,
                "symbol": holding.symbol,
                "quantity": float(holding.quantity),
                "average_buy_price": float(
                    holding.average_buy_price
                ),
                "invested_amount": round(
                    invested_amount,
                    2,
                ),
                "current_price": round(
                    current_price,
                    2,
                ),
                "current_value": round(
                    holding_current_value,
                    2,
                ),
                "profit_loss": round(
                    profit_loss,
                    2,
                ),
                "profit_loss_percent": round(
                    profit_loss_percent,
                    2,
                ),
            }
        )

        total_invested += invested_amount
        current_value += holding_current_value

    total_profit_loss = (
        current_value
        - total_invested
    )

    total_profit_loss_percent = (
        (total_profit_loss / total_invested) * 100
        if total_invested != 0
        else 0.0
    )

    return {
        "summary": {
            "total_invested": round(
                total_invested,
                2,
            ),
            "current_value": round(
                current_value,
                2,
            ),
            "profit_loss": round(
                total_profit_loss,
                2,
            ),
            "profit_loss_percent": round(
                total_profit_loss_percent,
                2,
            ),
            "holdings_count": len(holdings),
        },
        "holdings": valuation_holdings,
    }
'@

Set-Content `
    -Path (Join-Path $servicesDir "valuation_service.py") `
    -Value $valuationService `
    -Encoding UTF8

Write-Host "Created app\services\valuation_service.py" -ForegroundColor Green


# ============================================================
# 4. Create valuation API
# ============================================================

Write-Host ""
Write-Host "[4/10] Creating portfolio valuation API..." -ForegroundColor Cyan

$apiDir = Join-Path $backend "app\api\v1"
New-Item -ItemType Directory -Force -Path $apiDir | Out-Null

$valuationApi = @'
from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.valuation import PortfolioValuationResponse
from app.services.valuation_service import calculate_portfolio_valuation


router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio Valuation"],
)


@router.get(
    "/valuation",
    response_model=PortfolioValuationResponse,
)
def portfolio_valuation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calculate_portfolio_valuation(
        db=db,
        user_id=current_user.id,
    )
'@

Set-Content `
    -Path (Join-Path $apiDir "valuation.py") `
    -Value $valuationApi `
    -Encoding UTF8

Write-Host "Created app\api\v1\valuation.py" -ForegroundColor Green


# ============================================================
# 5. Register valuation router
# ============================================================

Write-Host ""
Write-Host "[5/10] Registering valuation API..." -ForegroundColor Cyan

$mainFile = Join-Path $backend "main.py"
$mainContent = Get-Content $mainFile -Raw

$valuationImport =
    "from app.api.v1.valuation import router as valuation_router"

if (-not $mainContent.Contains($valuationImport)) {

    $portfolioImport =
        "from app.api.v1.portfolio import router as portfolio_router"

    if ($mainContent.Contains($portfolioImport)) {

        $mainContent = $mainContent.Replace(
            $portfolioImport,
            $portfolioImport + "`r`n" + $valuationImport
        )

    }
    else {
        throw "Portfolio router import not found in main.py."
    }
}

if (-not $mainContent.Contains("valuation_router")) {
    throw "Valuation router could not be registered."
}

$valuationRegistration =
    "app.include_router(`r`n    valuation_router,`r`n    prefix=`"/api/v1`",`r`n)"

if (-not $mainContent.Contains(
    "valuation_router,`r`n    prefix=`"/api/v1`""
)) {

    $portfolioRegistration =
        "app.include_router(`r`n    portfolio_router,`r`n    prefix=`"/api/v1`",`r`n)"

    if ($mainContent.Contains($portfolioRegistration)) {

        $mainContent = $mainContent.Replace(
            $portfolioRegistration,
            $portfolioRegistration + "`r`n" + $valuationRegistration
        )

    }
    else {
        throw "Portfolio router registration not found in main.py."
    }
}

$mainContent = $mainContent.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $mainFile),
    $mainContent,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "Valuation router registered." -ForegroundColor Green


# ============================================================
# 6. Create valuation tests
# ============================================================

Write-Host ""
Write-Host "[6/10] Creating valuation tests..." -ForegroundColor Cyan

$testDir = Join-Path $backend "app\tests"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

$valuationTests = @'
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "valuation@example.com"
PASSWORD = "TestPassword123!"


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


def auth_headers():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def test_valuation_requires_authentication():

    response = client.get(
        "/api/v1/portfolio/valuation"
    )

    assert response.status_code == 401


@patch("app.services.valuation_service.get_quote")
def test_empty_portfolio_valuation(mock_quote):

    create_test_user()

    response = client.get(
        "/api/v1/portfolio/valuation",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_invested"] == 0
    assert data["summary"]["current_value"] == 0
    assert data["summary"]["profit_loss"] == 0
    assert data["summary"]["profit_loss_percent"] == 0
    assert data["summary"]["holdings_count"] == 0
    assert data["holdings"] == []

    mock_quote.assert_not_called()


@patch("app.services.valuation_service.get_quote")
def test_portfolio_valuation(mock_quote):

    create_test_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        holding = Holding(
            user_id=user.id,
            symbol="TEST",
            quantity=10,
            average_buy_price=100,
        )

        db.add(holding)
        db.commit()

    finally:
        db.close()

    class Quote:
        price = 120.0

    mock_quote.return_value = Quote()

    response = client.get(
        "/api/v1/portfolio/valuation",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_invested"] == 1000
    assert data["summary"]["current_value"] == 1200
    assert data["summary"]["profit_loss"] == 200
    assert data["summary"]["profit_loss_percent"] == 20
    assert data["summary"]["holdings_count"] == 1

    holding = data["holdings"][0]

    assert holding["symbol"] == "TEST"
    assert holding["quantity"] == 10
    assert holding["average_buy_price"] == 100
    assert holding["invested_amount"] == 1000
    assert holding["current_price"] == 120
    assert holding["current_value"] == 1200
    assert holding["profit_loss"] == 200
    assert holding["profit_loss_percent"] == 20


@patch("app.services.valuation_service.get_quote")
def test_multiple_holdings_are_aggregated(mock_quote):

    create_test_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
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

        db.commit()

    finally:
        db.close()

    class Quote:
        def __init__(self, price):
            self.price = price

    def quote_side_effect(symbol):

        if symbol == "AAA":
            return Quote(120)

        return Quote(60)

    mock_quote.side_effect = quote_side_effect

    response = client.get(
        "/api/v1/portfolio/valuation",
        headers=auth_headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_invested"] == 2000
    assert data["summary"]["current_value"] == 2400
    assert data["summary"]["profit_loss"] == 400
    assert data["summary"]["profit_loss_percent"] == 20
    assert data["summary"]["holdings_count"] == 2
'@

Set-Content `
    -Path (Join-Path $testDir "test_valuation.py") `
    -Value $valuationTests `
    -Encoding UTF8

Write-Host "Created valuation tests." -ForegroundColor Green


# ============================================================
# 7. Create frontend dashboard
# ============================================================

Write-Host ""
Write-Host "[7/10] Creating frontend dashboard..." -ForegroundColor Cyan

$frontendPages = Join-Path $root "frontend\src\pages"
$frontendServices = Join-Path $root "frontend\src\services"

New-Item -ItemType Directory -Force -Path $frontendPages | Out-Null
New-Item -ItemType Directory -Force -Path $frontendServices | Out-Null

$dashboardService = @'
import { api } from "./api";

export interface ValuationHolding {
  id: number;
  symbol: string;
  quantity: number;
  average_buy_price: number;
  invested_amount: number;
  current_price: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percent: number;
}

export interface PortfolioSummary {
  total_invested: number;
  current_value: number;
  profit_loss: number;
  profit_loss_percent: number;
  holdings_count: number;
}

export interface PortfolioValuation {
  summary: PortfolioSummary;
  holdings: ValuationHolding[];
}

export async function getPortfolioValuation(): Promise<PortfolioValuation> {
  return api.get<PortfolioValuation>("/portfolio/valuation");
}
'@

Set-Content `
    -Path (Join-Path $frontendServices "valuation.ts") `
    -Value $dashboardService `
    -Encoding UTF8


$dashboardPage = @'
import { useEffect, useState } from "react";

import {
  getPortfolioValuation,
  type PortfolioValuation,
} from "../services/valuation";


function money(value: number) {
  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}


export default function DashboardPage() {

  const [portfolio, setPortfolio] =
    useState<PortfolioValuation | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  async function loadDashboard() {

    setLoading(true);
    setError("");

    try {

      const result =
        await getPortfolioValuation();

      setPortfolio(result);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load portfolio.",
      );

    } finally {

      setLoading(false);

    }
  }


  useEffect(() => {
    void loadDashboard();
  }, []);


  if (loading) {

    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <p className="text-slate-600">
            Loading portfolio...
          </p>
        </div>
      </main>
    );

  }


  if (error) {

    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">

          <h1 className="text-3xl font-bold text-slate-900">
            Portfolio Dashboard
          </h1>

          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>

        </div>
      </main>
    );

  }


  if (!portfolio) {
    return null;
  }


  const {
    summary,
    holdings,
  } = portfolio;


  const profitPositive =
    summary.profit_loss >= 0;


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-7xl">

        <div className="flex items-center justify-between">

          <div>

            <h1 className="text-3xl font-bold text-slate-900">
              Portfolio Dashboard
            </h1>

            <p className="mt-2 text-slate-600">
              Track your investments and current performance.
            </p>

          </div>

          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
          >
            Refresh
          </button>

        </div>


        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Invested
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              ₹{money(summary.total_invested)}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Current Value
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              ₹{money(summary.current_value)}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Profit / Loss
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              {profitPositive ? "+" : ""}
              ₹{money(summary.profit_loss)}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Return
            </p>

            <p className="mt-2 text-2xl font-bold text-slate-900">
              {profitPositive ? "+" : ""}
              {summary.profit_loss_percent.toFixed(2)}%
            </p>

          </div>

        </section>


        <section className="mt-8 rounded-xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 p-5">

            <h2 className="text-xl font-semibold text-slate-900">
              Holdings
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              {summary.holdings_count} position
              {summary.holdings_count === 1 ? "" : "s"}
            </p>

          </div>


          {holdings.length === 0 ? (

            <div className="p-8 text-center text-slate-500">
              No holdings yet.
            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-left text-sm">

                <thead className="bg-slate-50 text-slate-500">

                  <tr>

                    <th className="px-5 py-3">
                      Symbol
                    </th>

                    <th className="px-5 py-3">
                      Qty
                    </th>

                    <th className="px-5 py-3">
                      Avg. Price
                    </th>

                    <th className="px-5 py-3">
                      Current
                    </th>

                    <th className="px-5 py-3">
                      Invested
                    </th>

                    <th className="px-5 py-3">
                      Value
                    </th>

                    <th className="px-5 py-3">
                      P/L
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {holdings.map((holding) => (

                    <tr
                      key={holding.id}
                      className="border-t border-slate-100"
                    >

                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {holding.symbol}
                      </td>

                      <td className="px-5 py-4">
                        {holding.quantity}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(holding.average_buy_price)}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(holding.current_price)}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(holding.invested_amount)}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(holding.current_value)}
                      </td>

                      <td className="px-5 py-4">

                        <div>
                          {holding.profit_loss >= 0 ? "+" : ""}
                          ₹{money(holding.profit_loss)}
                        </div>

                        <div className="text-xs text-slate-500">
                          {holding.profit_loss_percent >= 0 ? "+" : ""}
                          {holding.profit_loss_percent.toFixed(2)}%
                        </div>

                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

        </section>

      </div>

    </main>
  );
}
'@

Set-Content `
    -Path (Join-Path $frontendPages "DashboardPage.tsx") `
    -Value $dashboardPage `
    -Encoding UTF8

Write-Host "Created DashboardPage.tsx." -ForegroundColor Green


# ============================================================
# 8. Update frontend app
# ============================================================

Write-Host ""
Write-Host "[8/10] Updating frontend application..." -ForegroundColor Cyan

$appFile = Join-Path $root "frontend\src\App.tsx"

$appCode = @'
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return <DashboardPage />;
}
'@

Set-Content `
    -Path $appFile `
    -Value $appCode `
    -Encoding UTF8

Write-Host "Dashboard is now the main application page." -ForegroundColor Green


# ============================================================
# 9. Backend validation
# ============================================================

Write-Host ""
Write-Host "[9/10] Running backend validation..." -ForegroundColor Cyan

Push-Location $backend

try {

    & $python -c "from app.api.v1.valuation import router; print('Valuation routes:', [(r.path, r.methods) for r in router.routes])"

    if ($LASTEXITCODE -ne 0) {
        throw "Valuation router import failed."
    }

    & $python -m pytest

    if ($LASTEXITCODE -ne 0) {
        throw "Complete backend test suite failed."
    }

}
finally {
    Pop-Location
}

Write-Host "Backend validation: PASS" -ForegroundColor Green


# ============================================================
# 10. Git validation
# ============================================================

Write-Host ""
Write-Host "[10/10] Running Git validation..." -ForegroundColor Cyan

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host "git diff --check: PASS" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " TP-008 PORTFOLIO VALUATION + DASHBOARD COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Implemented:" -ForegroundColor Green
Write-Host "  TP-008.1 Portfolio valuation service"
Write-Host "  TP-008.2 Current market price integration"
Write-Host "  TP-008.3 Invested amount calculation"
Write-Host "  TP-008.4 Current portfolio value"
Write-Host "  TP-008.5 Profit / Loss calculation"
Write-Host "  TP-008.6 Portfolio valuation API"
Write-Host "  TP-008.7 Valuation tests"
Write-Host "  TP-008.8 Frontend valuation service"
Write-Host "  TP-008.9 Portfolio dashboard"
Write-Host ""
Write-Host "No Git commit or push performed." -ForegroundColor Yellow
Write-Host ""