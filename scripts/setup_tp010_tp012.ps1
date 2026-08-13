$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-010 to TP-012 Feature Batch" -ForegroundColor Cyan
Write-Host " P&L + Analytics + Watchlist + Dashboard Upgrade" -ForegroundColor Cyan
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
# 1. VALIDATE
# ============================================================

Write-Host "[1/15] Validating project..." -ForegroundColor Cyan

Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: OK" -ForegroundColor Green


# ============================================================
# 2. ANALYTICS SCHEMAS
# ============================================================

Write-Host ""
Write-Host "[2/15] Creating analytics schemas..." -ForegroundColor Cyan

$schemaDir = Join-Path $backend "app\schemas"
New-Item -ItemType Directory -Force -Path $schemaDir | Out-Null

$analyticsSchema = @'
from pydantic import BaseModel


class StockPerformance(BaseModel):
    symbol: str
    quantity: float
    invested_amount: float
    current_value: float
    unrealized_profit_loss: float
    unrealized_profit_loss_percent: float


class PortfolioAnalytics(BaseModel):
    total_invested: float
    current_value: float
    unrealized_profit_loss: float
    unrealized_profit_loss_percent: float
    realized_profit_loss: float
    total_profit_loss: float
    total_return_percent: float
    best_performer: str | None
    worst_performer: str | None
    holdings_count: int
    transactions_count: int
    stocks: list[StockPerformance]
'@

Set-Content `
    -Path (Join-Path $schemaDir "analytics.py") `
    -Value $analyticsSchema `
    -Encoding UTF8

Write-Host "Analytics schemas created." -ForegroundColor Green


# ============================================================
# 3. ANALYTICS SERVICE
# ============================================================

Write-Host ""
Write-Host "[3/15] Creating P&L analytics service..." -ForegroundColor Cyan

$serviceDir = Join-Path $backend "app\services"
New-Item -ItemType Directory -Force -Path $serviceDir | Out-Null

$analyticsService = @'
from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.market_service import (
    MarketDataProviderError,
    get_quote,
)


def calculate_realized_profit_loss(
    db: Session,
    user_id: int,
) -> float:

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(
            Transaction.transaction_date.asc(),
            Transaction.id.asc(),
        )
        .all()
    )

    positions = {}
    realized = 0.0

    for transaction in transactions:

        symbol = transaction.symbol
        quantity = float(transaction.quantity)
        price = float(transaction.price)

        if symbol not in positions:
            positions[symbol] = {
                "quantity": 0.0,
                "average_cost": 0.0,
            }

        position = positions[symbol]

        if transaction.transaction_type == "BUY":

            old_quantity = position["quantity"]
            old_average = position["average_cost"]

            new_quantity = old_quantity + quantity

            if new_quantity > 0:

                position["average_cost"] = (
                    (
                        old_quantity * old_average
                    )
                    + (
                        quantity * price
                    )
                ) / new_quantity

            position["quantity"] = new_quantity

        elif transaction.transaction_type == "SELL":

            if quantity <= position["quantity"]:

                realized += (
                    quantity
                    * (
                        price
                        - position["average_cost"]
                    )
                )

                position["quantity"] -= quantity

    return round(realized, 2)


def calculate_analytics(
    db: Session,
    user_id: int,
):

    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id)
        .order_by(Holding.symbol.asc())
        .all()
    )

    transaction_count = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .count()
    )

    stocks = []

    total_invested = 0.0
    current_value = 0.0

    for holding in holdings:

        quantity = float(holding.quantity)
        average_price = float(
            holding.average_buy_price
        )

        invested = quantity * average_price

        try:

            quote = get_quote(
                holding.symbol
            )

            current_price = float(
                quote.price
            )

        except MarketDataProviderError:

            current_price = average_price

        value = quantity * current_price

        unrealized = value - invested

        unrealized_percent = (
            (unrealized / invested) * 100
            if invested
            else 0.0
        )

        stocks.append(
            {
                "symbol": holding.symbol,
                "quantity": quantity,
                "invested_amount": round(
                    invested,
                    2,
                ),
                "current_value": round(
                    value,
                    2,
                ),
                "unrealized_profit_loss": round(
                    unrealized,
                    2,
                ),
                "unrealized_profit_loss_percent": round(
                    unrealized_percent,
                    2,
                ),
            }
        )

        total_invested += invested
        current_value += value

    unrealized_profit_loss = (
        current_value - total_invested
    )

    unrealized_percent = (
        (
            unrealized_profit_loss
            / total_invested
        ) * 100
        if total_invested
        else 0.0
    )

    realized_profit_loss = (
        calculate_realized_profit_loss(
            db,
            user_id,
        )
    )

    total_profit_loss = (
        realized_profit_loss
        + unrealized_profit_loss
    )

    total_return_percent = (
        (
            total_profit_loss
            / total_invested
        ) * 100
        if total_invested
        else 0.0
    )

    best_performer = None
    worst_performer = None

    if stocks:

        best = max(
            stocks,
            key=lambda item:
            item["unrealized_profit_loss_percent"],
        )

        worst = min(
            stocks,
            key=lambda item:
            item["unrealized_profit_loss_percent"],
        )

        best_performer = best["symbol"]
        worst_performer = worst["symbol"]

    return {
        "total_invested": round(
            total_invested,
            2,
        ),
        "current_value": round(
            current_value,
            2,
        ),
        "unrealized_profit_loss": round(
            unrealized_profit_loss,
            2,
        ),
        "unrealized_profit_loss_percent": round(
            unrealized_percent,
            2,
        ),
        "realized_profit_loss": round(
            realized_profit_loss,
            2,
        ),
        "total_profit_loss": round(
            total_profit_loss,
            2,
        ),
        "total_return_percent": round(
            total_return_percent,
            2,
        ),
        "best_performer": best_performer,
        "worst_performer": worst_performer,
        "holdings_count": len(holdings),
        "transactions_count": transaction_count,
        "stocks": stocks,
    }
'@

Set-Content `
    -Path (Join-Path $serviceDir "analytics_service.py") `
    -Value $analyticsService `
    -Encoding UTF8

Write-Host "Analytics service created." -ForegroundColor Green


# ============================================================
# 4. ANALYTICS API
# ============================================================

Write-Host ""
Write-Host "[4/15] Creating analytics API..." -ForegroundColor Cyan

$apiDir = Join-Path $backend "app\api\v1"
New-Item -ItemType Directory -Force -Path $apiDir | Out-Null

$analyticsApi = @'
from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import PortfolioAnalytics
from app.services.analytics_service import calculate_analytics


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get(
    "/portfolio",
    response_model=PortfolioAnalytics,
)
def portfolio_analytics(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    return calculate_analytics(
        db=db,
        user_id=current_user.id,
    )
'@

Set-Content `
    -Path (Join-Path $apiDir "analytics.py") `
    -Value $analyticsApi `
    -Encoding UTF8

Write-Host "Analytics API created." -ForegroundColor Green


# ============================================================
# 5. WATCHLIST MODEL
# ============================================================

Write-Host ""
Write-Host "[5/15] Creating watchlist model..." -ForegroundColor Cyan

$modelDir = Join-Path $backend "app\models"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

$watchlistModel = @'
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Watchlist(Base):

    __tablename__ = "watchlist"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "symbol",
            name="uq_watchlist_user_symbol",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
'@

Set-Content `
    -Path (Join-Path $modelDir "watchlist.py") `
    -Value $watchlistModel `
    -Encoding UTF8

Write-Host "Watchlist model created." -ForegroundColor Green


# ============================================================
# 6. WATCHLIST SCHEMAS
# ============================================================

Write-Host ""
Write-Host "[6/15] Creating watchlist schemas..." -ForegroundColor Cyan

$watchlistSchema = @'
from pydantic import BaseModel, Field


class WatchlistCreate(BaseModel):

    symbol: str = Field(
        min_length=1,
        max_length=20,
    )


class WatchlistResponse(BaseModel):

    id: int
    symbol: str

    model_config = {
        "from_attributes": True,
    }


class WatchlistQuote(BaseModel):

    id: int
    symbol: str
    price: float
    change: float
    change_percent: float
'@

Set-Content `
    -Path (Join-Path $schemaDir "watchlist.py") `
    -Value $watchlistSchema `
    -Encoding UTF8

Write-Host "Watchlist schemas created." -ForegroundColor Green


# ============================================================
# 7. WATCHLIST SERVICE
# ============================================================

Write-Host ""
Write-Host "[7/15] Creating watchlist service..." -ForegroundColor Cyan

$watchlistService = @'
from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist


def add_watchlist_symbol(
    db: Session,
    user_id: int,
    symbol: str,
):

    symbol = symbol.strip().upper()

    existing = (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == user_id,
            Watchlist.symbol == symbol,
        )
        .first()
    )

    if existing:
        return existing

    item = Watchlist(
        user_id=user_id,
        symbol=symbol,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def get_watchlist(
    db: Session,
    user_id: int,
):

    return (
        db.query(Watchlist)
        .filter(
            Watchlist.user_id == user_id
        )
        .order_by(
            Watchlist.symbol.asc()
        )
        .all()
    )


def get_watchlist_item(
    db: Session,
    user_id: int,
    item_id: int,
):

    return (
        db.query(Watchlist)
        .filter(
            Watchlist.id == item_id,
            Watchlist.user_id == user_id,
        )
        .first()
    )


def delete_watchlist_symbol(
    db: Session,
    user_id: int,
    item_id: int,
):

    item = get_watchlist_item(
        db,
        user_id,
        item_id,
    )

    if item is None:
        return False

    db.delete(item)
    db.commit()

    return True
'@

Set-Content `
    -Path (Join-Path $serviceDir "watchlist_service.py") `
    -Value $watchlistService `
    -Encoding UTF8

Write-Host "Watchlist service created." -ForegroundColor Green


# ============================================================
# 8. WATCHLIST API
# ============================================================

Write-Host ""
Write-Host "[8/15] Creating watchlist API..." -ForegroundColor Cyan

$watchlistApi = @'
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistQuote,
    WatchlistResponse,
)
from app.services.market_service import (
    MarketDataProviderError,
    get_quote,
)
from app.services.watchlist_service import (
    add_watchlist_symbol,
    delete_watchlist_symbol,
    get_watchlist,
)


router = APIRouter(
    prefix="/watchlist",
    tags=["Watchlist"],
)


@router.post(
    "",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_symbol(
    data: WatchlistCreate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    return add_watchlist_symbol(
        db=db,
        user_id=current_user.id,
        symbol=data.symbol,
    )


@router.get(
    "",
    response_model=list[WatchlistResponse],
)
def list_symbols(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    return get_watchlist(
        db,
        current_user.id,
    )


@router.get(
    "/quotes",
    response_model=list[WatchlistQuote],
)
def watchlist_quotes(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    items = get_watchlist(
        db,
        current_user.id,
    )

    results = []

    for item in items:

        try:

            quote = get_quote(
                item.symbol
            )

            results.append(
                {
                    "id": item.id,
                    "symbol": item.symbol,
                    "price": float(
                        quote.price
                    ),
                    "change": float(
                        getattr(
                            quote,
                            "change",
                            0,
                        )
                    ),
                    "change_percent": float(
                        getattr(
                            quote,
                            "change_percent",
                            0,
                        )
                    ),
                }
            )

        except MarketDataProviderError:

            results.append(
                {
                    "id": item.id,
                    "symbol": item.symbol,
                    "price": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                }
            )

    return results


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_symbol(
    item_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    deleted = delete_watchlist_symbol(
        db,
        current_user.id,
        item_id,
    )

    if not deleted:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found",
        )

    return None
'@

Set-Content `
    -Path (Join-Path $apiDir "watchlist.py") `
    -Value $watchlistApi `
    -Encoding UTF8

Write-Host "Watchlist API created." -ForegroundColor Green


# ============================================================
# 9. REGISTER MODELS + ROUTERS
# ============================================================

Write-Host ""
Write-Host "[9/15] Registering analytics and watchlist..." -ForegroundColor Cyan

$initDb = Join-Path $backend "app\db\init_db.py"
$initContent = Get-Content $initDb -Raw

$watchImport =
    "from app.models.watchlist import Watchlist"

if (-not $initContent.Contains($watchImport)) {

    $transactionImport =
        "from app.models.transaction import Transaction"

    if ($initContent.Contains($transactionImport)) {

        $initContent = $initContent.Replace(
            $transactionImport,
            $transactionImport + "`r`n" + $watchImport
        )

    }
    else {

        $initContent =
            $watchImport + "`r`n" + $initContent
    }
}

$initContent = $initContent.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $initDb),
    $initContent,
    (New-Object System.Text.UTF8Encoding($false))
)


$mainFile = Join-Path $backend "main.py"
$mainContent = Get-Content $mainFile -Raw

$analyticsImport =
    "from app.api.v1.analytics import router as analytics_router"

$watchlistImport =
    "from app.api.v1.watchlist import router as watchlist_router"

if (-not $mainContent.Contains($analyticsImport)) {

    $transactionImport =
        "from app.api.v1.transactions import router as transactions_router"

    if ($mainContent.Contains($transactionImport)) {

        $mainContent = $mainContent.Replace(
            $transactionImport,
            $transactionImport +
            "`r`n" +
            $analyticsImport +
            "`r`n" +
            $watchlistImport
        )

    }
    else {

        throw "Transaction router import not found."
    }
}


$transactionRegistration =
    "app.include_router(`r`n    transactions_router,`r`n    prefix=`"/api/v1`",`r`n)"

$analyticsRegistration =
    "app.include_router(`r`n    analytics_router,`r`n    prefix=`"/api/v1`",`r`n)"

$watchlistRegistration =
    "app.include_router(`r`n    watchlist_router,`r`n    prefix=`"/api/v1`",`r`n)"


if (-not $mainContent.Contains(
    "analytics_router,`r`n    prefix=`"/api/v1`""
)) {

    if ($mainContent.Contains($transactionRegistration)) {

        $mainContent = $mainContent.Replace(
            $transactionRegistration,
            $transactionRegistration +
            "`r`n" +
            $analyticsRegistration +
            "`r`n" +
            $watchlistRegistration
        )

    }
    else {

        throw "Transaction router registration not found."
    }
}


$mainContent = $mainContent.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $mainFile),
    $mainContent,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "Analytics and watchlist registered." -ForegroundColor Green


# ============================================================
# 10. ANALYTICS + WATCHLIST TESTS
# ============================================================

Write-Host ""
Write-Host "[10/15] Creating analytics and watchlist tests..." -ForegroundColor Cyan

$testDir = Join-Path $backend "app\tests"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

$analyticsTests = @'
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "analytics-test@example.com"
PASSWORD = "TestPassword123!"


def create_user():

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        if user is None:

            user = User(
                full_name="Analytics Test User",
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        db.query(Transaction).filter(
            Transaction.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.query(Holding).filter(
            Holding.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.commit()

        return user.id

    finally:
        db.close()


def headers():

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization":
            f"Bearer {response.json()['access_token']}"
    }


def test_analytics_requires_authentication():

    response = client.get(
        "/api/v1/analytics/portfolio"
    )

    assert response.status_code == 401


@patch(
    "app.services.analytics_service.get_quote"
)
def test_analytics_calculates_unrealized_pnl(
    mock_quote,
):

    create_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        db.add(
            Holding(
                user_id=user.id,
                symbol="TCS",
                quantity=10,
                average_buy_price=100,
            )
        )

        db.add(
            Transaction(
                user_id=user.id,
                symbol="TCS",
                transaction_type="BUY",
                quantity=10,
                price=100,
            )
        )

        db.commit()

    finally:
        db.close()

    class Quote:
        price = 120

    mock_quote.return_value = Quote()

    response = client.get(
        "/api/v1/analytics/portfolio",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_invested"] == 1000
    assert data["current_value"] == 1200
    assert data["unrealized_profit_loss"] == 200
    assert data["unrealized_profit_loss_percent"] == 20
    assert data["total_profit_loss"] == 200
    assert data["total_return_percent"] == 20


def test_analytics_calculates_realized_pnl():

    create_user()

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        db.add_all(
            [
                Transaction(
                    user_id=user.id,
                    symbol="INFY",
                    transaction_type="BUY",
                    quantity=10,
                    price=100,
                ),
                Transaction(
                    user_id=user.id,
                    symbol="INFY",
                    transaction_type="SELL",
                    quantity=5,
                    price=130,
                ),
            ]
        )

        db.commit()

    finally:
        db.close()

    response = client.get(
        "/api/v1/analytics/portfolio",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["realized_profit_loss"] == 150


def test_empty_analytics():

    create_user()

    response = client.get(
        "/api/v1/analytics/portfolio",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_invested"] == 0
    assert data["current_value"] == 0
    assert data["total_profit_loss"] == 0
    assert data["holdings_count"] == 0
'@

Set-Content `
    -Path (Join-Path $testDir "test_analytics.py") `
    -Value $analyticsTests `
    -Encoding UTF8


$watchlistTests = @'
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.watchlist import Watchlist
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "watchlist-test@example.com"
PASSWORD = "TestPassword123!"


def create_user():

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        if user is None:

            user = User(
                full_name="Watchlist Test User",
                email=EMAIL,
                password_hash=hash_password(PASSWORD),
            )

            db.add(user)
            db.commit()
            db.refresh(user)

        db.query(Watchlist).filter(
            Watchlist.user_id == user.id
        ).delete(
            synchronize_session=False
        )

        db.commit()

    finally:
        db.close()


def headers():

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200

    return {
        "Authorization":
            f"Bearer {response.json()['access_token']}"
    }


def test_watchlist_requires_authentication():

    response = client.get(
        "/api/v1/watchlist"
    )

    assert response.status_code == 401


def test_add_and_list_watchlist():

    create_user()

    response = client.post(
        "/api/v1/watchlist",
        json={
            "symbol": "reliance",
        },
        headers=headers(),
    )

    assert response.status_code == 201
    assert response.json()["symbol"] == "RELIANCE"

    response = client.get(
        "/api/v1/watchlist",
        headers=headers(),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["symbol"] == "RELIANCE"


def test_duplicate_watchlist_is_safe():

    create_user()

    auth = headers()

    first = client.post(
        "/api/v1/watchlist",
        json={"symbol": "TCS"},
        headers=auth,
    )

    second = client.post(
        "/api/v1/watchlist",
        json={"symbol": "TCS"},
        headers=auth,
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        "/api/v1/watchlist",
        headers=auth,
    )

    assert len(response.json()) == 1


@patch(
    "app.api.v1.watchlist.get_quote"
)
def test_watchlist_quotes(mock_quote):

    create_user()

    auth = headers()

    client.post(
        "/api/v1/watchlist",
        json={"symbol": "INFY"},
        headers=auth,
    )

    class Quote:
        price = 1500
        change = 25
        change_percent = 1.69

    mock_quote.return_value = Quote()

    response = client.get(
        "/api/v1/watchlist/quotes",
        headers=auth,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["symbol"] == "INFY"
    assert data[0]["price"] == 1500
    assert data[0]["change"] == 25


def test_delete_watchlist():

    create_user()

    auth = headers()

    response = client.post(
        "/api/v1/watchlist",
        json={"symbol": "HDFCBANK"},
        headers=auth,
    )

    item_id = response.json()["id"]

    response = client.delete(
        f"/api/v1/watchlist/{item_id}",
        headers=auth,
    )

    assert response.status_code == 204

    response = client.get(
        "/api/v1/watchlist",
        headers=auth,
    )

    assert response.json() == []
'@

Set-Content `
    -Path (Join-Path $testDir "test_watchlist.py") `
    -Value $watchlistTests `
    -Encoding UTF8

Write-Host "Analytics and watchlist tests created." -ForegroundColor Green


# ============================================================
# 11. FRONTEND SERVICES
# ============================================================

Write-Host ""
Write-Host "[11/15] Creating frontend analytics and watchlist services..." -ForegroundColor Cyan

$frontendServices = Join-Path $root "frontend\src\services"
New-Item -ItemType Directory -Force -Path $frontendServices | Out-Null

$analyticsFrontend = @'
import { api } from "./api";


export interface StockPerformance {
  symbol: string;
  quantity: number;
  invested_amount: number;
  current_value: number;
  unrealized_profit_loss: number;
  unrealized_profit_loss_percent: number;
}


export interface PortfolioAnalytics {
  total_invested: number;
  current_value: number;
  unrealized_profit_loss: number;
  unrealized_profit_loss_percent: number;
  realized_profit_loss: number;
  total_profit_loss: number;
  total_return_percent: number;
  best_performer: string | null;
  worst_performer: string | null;
  holdings_count: number;
  transactions_count: number;
  stocks: StockPerformance[];
}


export async function getPortfolioAnalytics() {

  return api.get<PortfolioAnalytics>(
    "/analytics/portfolio",
  );

}
'@

Set-Content `
    -Path (Join-Path $frontendServices "analytics.ts") `
    -Value $analyticsFrontend `
    -Encoding UTF8


$watchlistFrontend = @'
import { api } from "./api";


export interface WatchlistItem {
  id: number;
  symbol: string;
}


export interface WatchlistQuote {
  id: number;
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
}


export async function getWatchlist() {

  return api.get<WatchlistItem[]>(
    "/watchlist",
  );

}


export async function getWatchlistQuotes() {

  return api.get<WatchlistQuote[]>(
    "/watchlist/quotes",
  );

}


export async function addWatchlistSymbol(
  symbol: string,
) {

  return api.post<WatchlistItem>(
    "/watchlist",
    {
      symbol,
    },
  );

}


export async function deleteWatchlistSymbol(
  id: number,
) {

  return api.delete<void>(
    `/watchlist/${id}`,
  );

}
'@

Set-Content `
    -Path (Join-Path $frontendServices "watchlist.ts") `
    -Value $watchlistFrontend `
    -Encoding UTF8

Write-Host "Frontend services created." -ForegroundColor Green


# ============================================================
# 12. DASHBOARD UPGRADE
# ============================================================

Write-Host ""
Write-Host "[12/15] Upgrading dashboard..." -ForegroundColor Cyan

$dashboardFile =
    Join-Path $root "frontend\src\pages\DashboardPage.tsx"

$dashboard = @'
import { useEffect, useState } from "react";

import {
  getPortfolioAnalytics,
  type PortfolioAnalytics,
} from "../services/analytics";

import {
  addWatchlistSymbol,
  deleteWatchlistSymbol,
  getWatchlistQuotes,
  type WatchlistQuote,
} from "../services/watchlist";


function money(value: number) {

  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

}


export default function DashboardPage() {

  const [analytics, setAnalytics] =
    useState<PortfolioAnalytics | null>(null);

  const [watchlist, setWatchlist] =
    useState<WatchlistQuote[]>([]);

  const [newSymbol, setNewSymbol] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  async function loadDashboard() {

    try {

      setLoading(true);
      setError("");

      const [
        analyticsData,
        watchlistData,
      ] = await Promise.all([
        getPortfolioAnalytics(),
        getWatchlistQuotes(),
      ]);

      setAnalytics(analyticsData);
      setWatchlist(watchlistData);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load dashboard.",
      );

    } finally {

      setLoading(false);

    }

  }


  useEffect(() => {
    void loadDashboard();
  }, []);


  async function addSymbol() {

    const symbol = newSymbol.trim();

    if (!symbol) {
      return;
    }

    try {

      await addWatchlistSymbol(symbol);

      setNewSymbol("");

      await loadDashboard();

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to add symbol.",
      );

    }

  }


  async function removeSymbol(id: number) {

    try {

      await deleteWatchlistSymbol(id);

      await loadDashboard();

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to remove symbol.",
      );

    }

  }


  if (loading) {

    return (
      <main className="min-h-screen bg-slate-50 p-6">
        <div className="mx-auto max-w-7xl">
          <p>Loading dashboard...</p>
        </div>
      </main>
    );

  }


  if (!analytics) {
    return null;
  }


  const profitPositive =
    analytics.total_profit_loss >= 0;


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-7xl">

        <div className="flex items-center justify-between">

          <div>

            <h1 className="text-3xl font-bold text-slate-900">
              TradePilot AI
            </h1>

            <p className="mt-2 text-slate-600">
              Portfolio intelligence dashboard
            </p>

          </div>

          <button
            type="button"
            onClick={() => void loadDashboard()}
            className="rounded-lg bg-slate-900 px-4 py-2 text-white"
          >
            Refresh
          </button>

        </div>


        {error && (

          <div className="mt-5 rounded-lg bg-red-50 p-4 text-red-700">
            {error}
          </div>

        )}


        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Invested
            </p>

            <p className="mt-2 text-2xl font-bold">
              ₹{money(
                analytics.total_invested
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Current Value
            </p>

            <p className="mt-2 text-2xl font-bold">
              ₹{money(
                analytics.current_value
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Total P/L
            </p>

            <p className="mt-2 text-2xl font-bold">
              {profitPositive ? "+" : ""}
              ₹{money(
                analytics.total_profit_loss
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5 shadow-sm">

            <p className="text-sm text-slate-500">
              Return
            </p>

            <p className="mt-2 text-2xl font-bold">
              {profitPositive ? "+" : ""}
              {analytics.total_return_percent.toFixed(2)}%
            </p>

          </div>

        </section>


        <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Realized P/L
            </p>

            <p className="mt-2 text-xl font-semibold">
              ₹{money(
                analytics.realized_profit_loss
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Unrealized P/L
            </p>

            <p className="mt-2 text-xl font-semibold">
              ₹{money(
                analytics.unrealized_profit_loss
              )}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Best Performer
            </p>

            <p className="mt-2 text-xl font-semibold">
              {analytics.best_performer ?? "-"}
            </p>

          </div>


          <div className="rounded-xl border bg-white p-5">

            <p className="text-sm text-slate-500">
              Worst Performer
            </p>

            <p className="mt-2 text-xl font-semibold">
              {analytics.worst_performer ?? "-"}
            </p>

          </div>

        </section>


        <section className="mt-8 rounded-xl border bg-white shadow-sm">

          <div className="border-b p-5">

            <h2 className="text-xl font-semibold">
              Holdings Performance
            </h2>

          </div>


          <div className="overflow-x-auto">

            <table className="w-full text-left text-sm">

              <thead className="bg-slate-50 text-slate-500">

                <tr>

                  <th className="px-5 py-3">
                    Symbol
                  </th>

                  <th className="px-5 py-3">
                    Quantity
                  </th>

                  <th className="px-5 py-3">
                    Invested
                  </th>

                  <th className="px-5 py-3">
                    Current
                  </th>

                  <th className="px-5 py-3">
                    P/L
                  </th>

                  <th className="px-5 py-3">
                    Return
                  </th>

                </tr>

              </thead>


              <tbody>

                {analytics.stocks.map(
                  (stock) => (

                    <tr
                      key={stock.symbol}
                      className="border-t"
                    >

                      <td className="px-5 py-4 font-semibold">
                        {stock.symbol}
                      </td>

                      <td className="px-5 py-4">
                        {stock.quantity}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(
                          stock.invested_amount
                        )}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(
                          stock.current_value
                        )}
                      </td>

                      <td className="px-5 py-4">
                        ₹{money(
                          stock.unrealized_profit_loss
                        )}
                      </td>

                      <td className="px-5 py-4">
                        {stock.unrealized_profit_loss_percent.toFixed(2)}%
                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        </section>


        <section className="mt-8 rounded-xl border bg-white shadow-sm">

          <div className="flex flex-col gap-4 border-b p-5 md:flex-row md:items-center md:justify-between">

            <div>

              <h2 className="text-xl font-semibold">
                Watchlist
              </h2>

              <p className="text-sm text-slate-500">
                Track stocks before you buy.
              </p>

            </div>


            <div className="flex gap-2">

              <input
                value={newSymbol}
                onChange={(event) =>
                  setNewSymbol(
                    event.target.value
                  )
                }
                placeholder="TCS"
                className="rounded-lg border px-3 py-2"
              />

              <button
                type="button"
                onClick={() => void addSymbol()}
                className="rounded-lg bg-slate-900 px-4 py-2 text-white"
              >
                Add
              </button>

            </div>

          </div>


          {watchlist.length === 0 ? (

            <div className="p-8 text-center text-slate-500">
              Your watchlist is empty.
            </div>

          ) : (

            <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-4">

              {watchlist.map(
                (item) => (

                  <div
                    key={item.id}
                    className="rounded-lg border p-4"
                  >

                    <div className="flex items-center justify-between">

                      <span className="font-semibold">
                        {item.symbol}
                      </span>

                      <button
                        type="button"
                        onClick={() =>
                          void removeSymbol(
                            item.id
                          )
                        }
                        className="text-xs text-red-600"
                      >
                        Remove
                      </button>

                    </div>

                    <p className="mt-3 text-xl font-bold">
                      ₹{money(item.price)}
                    </p>

                    <p className="mt-1 text-sm">
                      {item.change >= 0 ? "+" : ""}
                      {money(item.change)}
                      {" "}
                      (
                      {item.change_percent >= 0 ? "+" : ""}
                      {item.change_percent.toFixed(2)}%
                      )
                    </p>

                  </div>

                )
              )}

            </div>

          )}

        </section>

      </div>

    </main>
  );
}
'@

Set-Content `
    -Path $dashboardFile `
    -Value $dashboard `
    -Encoding UTF8

Write-Host "Dashboard upgraded." -ForegroundColor Green


# ============================================================
# 13. IMPORT VALIDATION
# ============================================================

Write-Host ""
Write-Host "[13/15] Validating new backend components..." -ForegroundColor Cyan

Push-Location $backend

try {

    & $python -c "from app.models.watchlist import Watchlist; from app.api.v1.analytics import router as analytics_router; from app.api.v1.watchlist import router as watchlist_router; print('Analytics import: PASS'); print('Watchlist import: PASS'); print('Analytics routes:', [(r.path, r.methods) for r in analytics_router.routes]); print('Watchlist routes:', [(r.path, r.methods) for r in watchlist_router.routes])"

    if ($LASTEXITCODE -ne 0) {
        throw "New component imports failed."
    }

}
finally {
    Pop-Location
}


# ============================================================
# 14. COMPLETE TEST SUITE
# ============================================================

Write-Host ""
Write-Host "[14/15] Running complete backend test suite..." -ForegroundColor Cyan

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


# ============================================================
# 15. GIT VALIDATION
# ============================================================

Write-Host ""
Write-Host "[15/15] Running Git validation..." -ForegroundColor Cyan

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host "git diff --check: PASS" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " TP-010 TO TP-012 COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Implemented:" -ForegroundColor Green
Write-Host "TP-010.1  - Realized P/L calculation"
Write-Host "TP-010.2  - Unrealized P/L"
Write-Host "TP-010.3  - Total return"
Write-Host "TP-010.4  - Per-stock analytics"
Write-Host "TP-010.5  - Best/worst performers"
Write-Host "TP-010.6  - Analytics API"
Write-Host "TP-010.7  - Analytics tests"
Write-Host ""
Write-Host "TP-011.1  - Watchlist model"
Write-Host "TP-011.2  - Watchlist API"
Write-Host "TP-011.3  - Add/remove stocks"
Write-Host "TP-011.4  - Live watchlist quotes"
Write-Host "TP-011.5  - Watchlist tests"
Write-Host ""
Write-Host "TP-012.1  - Dashboard P/L cards"
Write-Host "TP-012.2  - Holdings performance"
Write-Host "TP-012.3  - Watchlist dashboard"
Write-Host "TP-012.4  - Dashboard refresh"
Write-Host ""
Write-Host "No Git commit or push performed." -ForegroundColor Yellow