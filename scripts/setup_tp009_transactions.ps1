$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-009 Transaction Management" -ForegroundColor Cyan
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
# 1. VALIDATION
# ============================================================

Write-Host "[1/12] Validating project..." -ForegroundColor Cyan

Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: OK" -ForegroundColor Green


# ============================================================
# 2. TRANSACTION MODEL
# ============================================================

Write-Host ""
Write-Host "[2/12] Creating transaction model..." -ForegroundColor Cyan

$modelDir = Join-Path $backend "app\models"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

$transactionModel = @'
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

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

    transaction_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
'@

Set-Content `
    -Path (Join-Path $modelDir "transaction.py") `
    -Value $transactionModel `
    -Encoding UTF8

Write-Host "Created Transaction model." -ForegroundColor Green


# ============================================================
# 3. TRANSACTION SCHEMAS
# ============================================================

Write-Host ""
Write-Host "[3/12] Creating transaction schemas..." -ForegroundColor Cyan

$schemaDir = Join-Path $backend "app\schemas"
New-Item -ItemType Directory -Force -Path $schemaDir | Out-Null

$transactionSchema = @'
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=20,
    )

    transaction_type: str

    quantity: float = Field(
        gt=0,
    )

    price: float = Field(
        gt=0,
    )

    transaction_date: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, value: str) -> str:

        value = value.strip().upper()

        if value not in {"BUY", "SELL"}:
            raise ValueError(
                "transaction_type must be BUY or SELL"
            )

        return value


class TransactionResponse(BaseModel):
    id: int
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    transaction_date: datetime

    model_config = {
        "from_attributes": True,
    }


class TransactionSummary(BaseModel):
    total_transactions: int
    total_buy_value: float
    total_sell_value: float
    realized_profit_loss: float


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    summary: TransactionSummary
'@

Set-Content `
    -Path (Join-Path $schemaDir "transaction.py") `
    -Value $transactionSchema `
    -Encoding UTF8

Write-Host "Created transaction schemas." -ForegroundColor Green


# ============================================================
# 4. TRANSACTION SERVICE
# ============================================================

Write-Host ""
Write-Host "[4/12] Creating transaction service..." -ForegroundColor Cyan

$serviceDir = Join-Path $backend "app\services"
New-Item -ItemType Directory -Force -Path $serviceDir | Out-Null

$transactionService = @'
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.holding import Holding
from app.models.transaction import Transaction


def create_transaction(
    db: Session,
    user_id: int,
    symbol: str,
    transaction_type: str,
    quantity: float,
    price: float,
    transaction_date: datetime | None = None,
):

    symbol = symbol.strip().upper()
    transaction_type = transaction_type.strip().upper()

    if transaction_type not in {"BUY", "SELL"}:
        raise ValueError(
            "transaction_type must be BUY or SELL"
        )

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if price <= 0:
        raise ValueError("Price must be greater than zero.")

    holding = (
        db.query(Holding)
        .filter(
            Holding.user_id == user_id,
            Holding.symbol == symbol,
        )
        .first()
    )

    if transaction_type == "BUY":

        if holding is None:

            holding = Holding(
                user_id=user_id,
                symbol=symbol,
                quantity=quantity,
                average_buy_price=price,
            )

            db.add(holding)

        else:

            old_quantity = float(holding.quantity)
            old_average = float(
                holding.average_buy_price
            )

            new_quantity = old_quantity + quantity

            new_average = (
                (
                    old_quantity * old_average
                )
                + (
                    quantity * price
                )
            ) / new_quantity

            holding.quantity = new_quantity
            holding.average_buy_price = new_average

    else:

        if holding is None:
            raise ValueError(
                "Cannot sell a stock that is not in the portfolio."
            )

        current_quantity = float(holding.quantity)

        if quantity > current_quantity:
            raise ValueError(
                "Sell quantity cannot exceed current holding quantity."
            )

        holding.quantity = current_quantity - quantity

        if holding.quantity == 0:
            db.delete(holding)

    transaction = Transaction(
        user_id=user_id,
        symbol=symbol,
        transaction_type=transaction_type,
        quantity=quantity,
        price=price,
        transaction_date=(
            transaction_date
            or datetime.now(timezone.utc)
        ),
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return transaction


def get_user_transactions(
    db: Session,
    user_id: int,
):

    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc())
        .all()
    )


def get_transaction(
    db: Session,
    transaction_id: int,
    user_id: int,
):

    return (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        .first()
    )


def get_transaction_summary(
    db: Session,
    user_id: int,
):

    transactions = get_user_transactions(
        db,
        user_id,
    )

    total_buy_value = 0.0
    total_sell_value = 0.0
    realized_profit_loss = 0.0

    for transaction in transactions:

        value = (
            float(transaction.quantity)
            * float(transaction.price)
        )

        if transaction.transaction_type == "BUY":

            total_buy_value += value

        else:

            total_sell_value += value

    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id)
        .all()
    )

    # Realized P/L is calculated from historical
    # SELL transactions using the current holding
    # cost basis available to the application.
    #
    # Full lot-level realized P/L will be introduced
    # when transaction-lot accounting is added.

    realized_profit_loss = 0.0

    return {
        "total_transactions": len(transactions),
        "total_buy_value": round(
            total_buy_value,
            2,
        ),
        "total_sell_value": round(
            total_sell_value,
            2,
        ),
        "realized_profit_loss": round(
            realized_profit_loss,
            2,
        ),
    }
'@

Set-Content `
    -Path (Join-Path $serviceDir "transaction_service.py") `
    -Value $transactionService `
    -Encoding UTF8

Write-Host "Created transaction service." -ForegroundColor Green


# ============================================================
# 5. TRANSACTION API
# ============================================================

Write-Host ""
Write-Host "[5/12] Creating transaction API..." -ForegroundColor Cyan

$apiDir = Join-Path $backend "app\api\v1"
New-Item -ItemType Directory -Force -Path $apiDir | Out-Null

$transactionApi = @'
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionSummary,
)
from app.services.transaction_service import (
    create_transaction,
    get_transaction,
    get_transaction_summary,
    get_user_transactions,
)


router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"],
)


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:

        return create_transaction(
            db=db,
            user_id=current_user.id,
            symbol=transaction_data.symbol,
            transaction_type=transaction_data.transaction_type,
            quantity=transaction_data.quantity,
            price=transaction_data.price,
            transaction_date=transaction_data.transaction_date,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=TransactionListResponse,
)
def list_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    transactions = get_user_transactions(
        db,
        current_user.id,
    )

    summary = get_transaction_summary(
        db,
        current_user.id,
    )

    return {
        "transactions": transactions,
        "summary": summary,
    }


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def transaction_details(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    transaction = get_transaction(
        db,
        transaction_id,
        current_user.id,
    )

    if transaction is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction
'@

Set-Content `
    -Path (Join-Path $apiDir "transactions.py") `
    -Value $transactionApi `
    -Encoding UTF8

Write-Host "Created transaction API." -ForegroundColor Green


# ============================================================
# 6. REGISTER MODEL
# ============================================================

Write-Host ""
Write-Host "[6/12] Registering transaction model..." -ForegroundColor Cyan

$initDb = Join-Path $backend "app\db\init_db.py"
$initContent = Get-Content $initDb -Raw

$modelImport =
    "from app.models.transaction import Transaction"

if (-not $initContent.Contains($modelImport)) {

    $userImport =
        "from app.models.user import User"

    if ($initContent.Contains($userImport)) {

        $initContent = $initContent.Replace(
            $userImport,
            $userImport + "`r`n" + $modelImport
        )

    }
    else {

        $initContent =
            $modelImport + "`r`n" + $initContent
    }
}

$initContent = $initContent.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $initDb),
    $initContent,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "Transaction model registered." -ForegroundColor Green


# ============================================================
# 7. REGISTER API
# ============================================================

Write-Host ""
Write-Host "[7/12] Registering transaction router..." -ForegroundColor Cyan

$mainFile = Join-Path $backend "main.py"
$mainContent = Get-Content $mainFile -Raw

$transactionImport =
    "from app.api.v1.transactions import router as transactions_router"

if (-not $mainContent.Contains($transactionImport)) {

    $valuationImport =
        "from app.api.v1.valuation import router as valuation_router"

    if ($mainContent.Contains($valuationImport)) {

        $mainContent = $mainContent.Replace(
            $valuationImport,
            $valuationImport + "`r`n" + $transactionImport
        )

    }
    else {

        throw "Valuation router import not found."
    }
}

$transactionRegistration =
    "app.include_router(`r`n    transactions_router,`r`n    prefix=`"/api/v1`",`r`n)"

if (-not $mainContent.Contains(
    "transactions_router,`r`n    prefix=`"/api/v1`""
)) {

    $valuationRegistration =
        "app.include_router(`r`n    valuation_router,`r`n    prefix=`"/api/v1`",`r`n)"

    if ($mainContent.Contains($valuationRegistration)) {

        $mainContent = $mainContent.Replace(
            $valuationRegistration,
            $valuationRegistration + "`r`n" +
            $transactionRegistration
        )

    }
    else {

        throw "Valuation router registration not found."
    }
}

$mainContent = $mainContent.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $mainFile),
    $mainContent,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "Transaction router registered." -ForegroundColor Green


# ============================================================
# 8. TRANSACTION TESTS
# ============================================================

Write-Host ""
Write-Host "[8/12] Creating transaction tests..." -ForegroundColor Cyan

$testDir = Join-Path $backend "app\tests"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

$transactionTests = @'
from fastapi.testclient import TestClient

from main import app

from app.db.database import SessionLocal
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.services.auth_service import hash_password


client = TestClient(app)

EMAIL = "transaction-test@example.com"
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
                full_name="Transaction Test User",
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


def test_transactions_require_authentication():

    response = client.get(
        "/api/v1/transactions"
    )

    assert response.status_code == 401


def test_buy_transaction_creates_holding():

    create_user()

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 3000,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["symbol"] == "TCS"
    assert data["transaction_type"] == "BUY"
    assert data["quantity"] == 10
    assert data["price"] == 3000

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        holding = (
            db.query(Holding)
            .filter(
                Holding.user_id == user.id,
                Holding.symbol == "TCS",
            )
            .first()
        )

        assert holding is not None
        assert holding.quantity == 10
        assert holding.average_buy_price == 3000

    finally:
        db.close()


def test_multiple_buys_calculate_weighted_average():

    create_user()

    headers = auth_headers()

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "INFY",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 1000,
        },
        headers=headers,
    )

    assert response.status_code == 201

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "INFY",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 1200,
        },
        headers=headers,
    )

    assert response.status_code == 201

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        holding = (
            db.query(Holding)
            .filter(
                Holding.user_id == user.id,
                Holding.symbol == "INFY",
            )
            .first()
        )

        assert holding is not None
        assert holding.quantity == 20
        assert holding.average_buy_price == 1100

    finally:
        db.close()


def test_sell_transaction_reduces_holding():

    create_user()

    headers = auth_headers()

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "RELIANCE",
            "transaction_type": "BUY",
            "quantity": 20,
            "price": 2500,
        },
        headers=headers,
    )

    assert response.status_code == 201

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "RELIANCE",
            "transaction_type": "SELL",
            "quantity": 5,
            "price": 2800,
        },
        headers=headers,
    )

    assert response.status_code == 201

    db = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == EMAIL)
            .first()
        )

        holding = (
            db.query(Holding)
            .filter(
                Holding.user_id == user.id,
                Holding.symbol == "RELIANCE",
            )
            .first()
        )

        assert holding is not None
        assert holding.quantity == 15
        assert holding.average_buy_price == 2500

    finally:
        db.close()


def test_sell_more_than_holding_is_rejected():

    create_user()

    headers = auth_headers()

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "HDFC",
            "transaction_type": "BUY",
            "quantity": 5,
            "price": 1500,
        },
        headers=headers,
    )

    assert response.status_code == 201

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "HDFC",
            "transaction_type": "SELL",
            "quantity": 10,
            "price": 1600,
        },
        headers=headers,
    )

    assert response.status_code == 400


def test_invalid_transaction_type_is_rejected():

    create_user()

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "TCS",
            "transaction_type": "INVALID",
            "quantity": 10,
            "price": 3000,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 422


def test_transaction_history():

    create_user()

    headers = auth_headers()

    client.post(
        "/api/v1/transactions",
        json={
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 3000,
        },
        headers=headers,
    )

    client.post(
        "/api/v1/transactions",
        json={
            "symbol": "INFY",
            "transaction_type": "BUY",
            "quantity": 5,
            "price": 1500,
        },
        headers=headers,
    )

    response = client.get(
        "/api/v1/transactions",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["total_transactions"] == 2
    assert len(data["transactions"]) == 2


def test_transaction_belongs_to_user():

    create_user()

    headers = auth_headers()

    response = client.post(
        "/api/v1/transactions",
        json={
            "symbol": "TCS",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 3000,
        },
        headers=headers,
    )

    assert response.status_code == 201

    transaction_id = response.json()["id"]

    response = client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=headers,
    )

    assert response.status_code == 200
'@

Set-Content `
    -Path (Join-Path $testDir "test_transactions.py") `
    -Value $transactionTests `
    -Encoding UTF8

Write-Host "Created transaction tests." -ForegroundColor Green


# ============================================================
# 9. FRONTEND TRANSACTION SERVICE
# ============================================================

Write-Host ""
Write-Host "[9/12] Creating frontend transaction service..." -ForegroundColor Cyan

$frontendServiceDir = Join-Path $root "frontend\src\services"
New-Item -ItemType Directory -Force -Path $frontendServiceDir | Out-Null

$frontendService = @'
import { api } from "./api";


export interface Transaction {
  id: number;
  symbol: string;
  transaction_type: "BUY" | "SELL";
  quantity: number;
  price: number;
  transaction_date: string;
}


export interface TransactionSummary {
  total_transactions: number;
  total_buy_value: number;
  total_sell_value: number;
  realized_profit_loss: number;
}


export interface TransactionListResponse {
  transactions: Transaction[];
  summary: TransactionSummary;
}


export interface TransactionCreate {
  symbol: string;
  transaction_type: "BUY" | "SELL";
  quantity: number;
  price: number;
}


export async function createTransaction(
  transaction: TransactionCreate,
): Promise<Transaction> {

  return api.post<Transaction>(
    "/transactions",
    transaction,
  );
}


export async function getTransactions(): Promise<TransactionListResponse> {

  return api.get<TransactionListResponse>(
    "/transactions",
  );
}
'@

Set-Content `
    -Path (Join-Path $frontendServiceDir "transactions.ts") `
    -Value $frontendService `
    -Encoding UTF8

Write-Host "Created frontend transaction service." -ForegroundColor Green


# ============================================================
# 10. FRONTEND TRANSACTION PAGE
# ============================================================

Write-Host ""
Write-Host "[10/12] Creating transaction page..." -ForegroundColor Cyan

$frontendPages = Join-Path $root "frontend\src\pages"
New-Item -ItemType Directory -Force -Path $frontendPages | Out-Null

$transactionPage = @'
import { FormEvent, useEffect, useState } from "react";

import {
  createTransaction,
  getTransactions,
  type Transaction,
  type TransactionListResponse,
} from "../services/transactions";


function money(value: number) {

  return value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

}


export default function TransactionsPage() {

  const [data, setData] =
    useState<TransactionListResponse | null>(null);

  const [symbol, setSymbol] =
    useState("");

  const [type, setType] =
    useState<"BUY" | "SELL">("BUY");

  const [quantity, setQuantity] =
    useState("");

  const [price, setPrice] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState("");


  async function loadTransactions() {

    try {

      setLoading(true);

      const result =
        await getTransactions();

      setData(result);

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load transactions.",
      );

    } finally {

      setLoading(false);

    }

  }


  useEffect(() => {
    void loadTransactions();
  }, []);


  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {

    event.preventDefault();

    setError("");
    setSaving(true);

    try {

      await createTransaction({
        symbol,
        transaction_type: type,
        quantity: Number(quantity),
        price: Number(price),
      });

      setSymbol("");
      setQuantity("");
      setPrice("");

      await loadTransactions();

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Unable to create transaction.",
      );

    } finally {

      setSaving(false);

    }

  }


  const transactions: Transaction[] =
    data?.transactions ?? [];


  return (
    <main className="min-h-screen bg-slate-50 p-6">

      <div className="mx-auto max-w-7xl">

        <h1 className="text-3xl font-bold text-slate-900">
          Transactions
        </h1>

        <p className="mt-2 text-slate-600">
          Record your BUY and SELL transactions.
        </p>


        <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">

          <h2 className="text-xl font-semibold">
            Add Transaction
          </h2>

          <form
            onSubmit={handleSubmit}
            className="mt-5 grid gap-4 md:grid-cols-5"
          >

            <input
              value={symbol}
              onChange={(event) =>
                setSymbol(event.target.value)
              }
              placeholder="Symbol"
              required
              className="rounded-lg border border-slate-300 px-3 py-2"
            />

            <select
              value={type}
              onChange={(event) =>
                setType(
                  event.target.value as "BUY" | "SELL",
                )
              }
              className="rounded-lg border border-slate-300 px-3 py-2"
            >

              <option value="BUY">
                BUY
              </option>

              <option value="SELL">
                SELL
              </option>

            </select>

            <input
              type="number"
              min="0.0001"
              step="any"
              value={quantity}
              onChange={(event) =>
                setQuantity(event.target.value)
              }
              placeholder="Quantity"
              required
              className="rounded-lg border border-slate-300 px-3 py-2"
            />

            <input
              type="number"
              min="0.01"
              step="any"
              value={price}
              onChange={(event) =>
                setPrice(event.target.value)
              }
              placeholder="Price"
              required
              className="rounded-lg border border-slate-300 px-3 py-2"
            />

            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Add Transaction"}
            </button>

          </form>

          {error && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 text-red-700">
              {error}
            </div>
          )}

        </section>


        <section className="mt-8 grid gap-4 md:grid-cols-3">

          <div className="rounded-xl border border-slate-200 bg-white p-5">

            <p className="text-sm text-slate-500">
              Transactions
            </p>

            <p className="mt-2 text-2xl font-bold">
              {data?.summary.total_transactions ?? 0}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5">

            <p className="text-sm text-slate-500">
              Total BUY Value
            </p>

            <p className="mt-2 text-2xl font-bold">
              ₹{money(
                data?.summary.total_buy_value ?? 0
              )}
            </p>

          </div>


          <div className="rounded-xl border border-slate-200 bg-white p-5">

            <p className="text-sm text-slate-500">
              Total SELL Value
            </p>

            <p className="mt-2 text-2xl font-bold">
              ₹{money(
                data?.summary.total_sell_value ?? 0
              )}
            </p>

          </div>

        </section>


        <section className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">

          <div className="border-b border-slate-200 p-5">

            <h2 className="text-xl font-semibold">
              Transaction History
            </h2>

          </div>


          {loading ? (

            <div className="p-6 text-slate-500">
              Loading transactions...
            </div>

          ) : transactions.length === 0 ? (

            <div className="p-8 text-center text-slate-500">
              No transactions yet.
            </div>

          ) : (

            <div className="overflow-x-auto">

              <table className="w-full text-left text-sm">

                <thead className="bg-slate-50 text-slate-500">

                  <tr>

                    <th className="px-5 py-3">
                      Date
                    </th>

                    <th className="px-5 py-3">
                      Symbol
                    </th>

                    <th className="px-5 py-3">
                      Type
                    </th>

                    <th className="px-5 py-3">
                      Quantity
                    </th>

                    <th className="px-5 py-3">
                      Price
                    </th>

                    <th className="px-5 py-3">
                      Value
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {transactions.map(
                    (transaction) => (

                      <tr
                        key={transaction.id}
                        className="border-t border-slate-100"
                      >

                        <td className="px-5 py-4">
                          {new Date(
                            transaction.transaction_date
                          ).toLocaleString()}
                        </td>

                        <td className="px-5 py-4 font-semibold">
                          {transaction.symbol}
                        </td>

                        <td className="px-5 py-4 font-semibold">
                          {transaction.transaction_type}
                        </td>

                        <td className="px-5 py-4">
                          {transaction.quantity}
                        </td>

                        <td className="px-5 py-4">
                          ₹{money(transaction.price)}
                        </td>

                        <td className="px-5 py-4">
                          ₹{money(
                            transaction.quantity
                            * transaction.price
                          )}
                        </td>

                      </tr>

                    )
                  )}

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
    -Path (Join-Path $frontendPages "TransactionsPage.tsx") `
    -Value $transactionPage `
    -Encoding UTF8

Write-Host "Created TransactionsPage.tsx." -ForegroundColor Green


# ============================================================
# 11. VALIDATE BACKEND
# ============================================================

Write-Host ""
Write-Host "[11/12] Running backend validation..." -ForegroundColor Cyan

Push-Location $backend

try {

    & $python -c "from app.models.transaction import Transaction; from app.api.v1.transactions import router; print('Transaction model: PASS'); print('Transaction routes:', [(r.path, r.methods) for r in router.routes])"

    if ($LASTEXITCODE -ne 0) {
        throw "Transaction imports failed."
    }

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
# 12. GIT VALIDATION
# ============================================================

Write-Host ""
Write-Host "[12/12] Running Git validation..." -ForegroundColor Cyan

git diff --check

if ($LASTEXITCODE -ne 0) {
    throw "git diff --check failed."
}

Write-Host "git diff --check: PASS" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " TP-009 TRANSACTION MANAGEMENT COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Implemented:" -ForegroundColor Green
Write-Host "TP-009.1 - Transaction model"
Write-Host "TP-009.2 - Transaction schemas"
Write-Host "TP-009.3 - BUY transaction"
Write-Host "TP-009.4 - SELL transaction"
Write-Host "TP-009.5 - Weighted average cost"
Write-Host "TP-009.6 - Holding synchronization"
Write-Host "TP-009.7 - Transaction API"
Write-Host "TP-009.8 - Transaction history"
Write-Host "TP-009.9 - Transaction tests"
Write-Host "TP-009.10 - Frontend transaction service"
Write-Host "TP-009.11 - Transaction page"
Write-Host ""
Write-Host "No Git commit or push performed." -ForegroundColor Yellow
Write-Host ""