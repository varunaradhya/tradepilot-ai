$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " TradePilot AI - TP-007 Market Data MVP" -ForegroundColor Cyan
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

Write-Host "[1/12] Validating project..." -ForegroundColor Cyan
Write-Host "Repository: OK" -ForegroundColor Green
Write-Host "Python: OK" -ForegroundColor Green


# ============================================================
# 2. Create market schemas
# ============================================================

Write-Host ""
Write-Host "[2/12] Creating market data schemas..." -ForegroundColor Cyan

$schemasDir = Join-Path $backend "app\schemas"
New-Item -ItemType Directory -Force -Path $schemasDir | Out-Null

$marketSchema = @'
from datetime import datetime

from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    symbol: str
    name: str | None = None
    currency: str | None = None
    exchange: str | None = None
    price: float
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    market_time: datetime | None = None


class HistoricalPrice(BaseModel):
    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


class HistoryResponse(BaseModel):
    symbol: str
    currency: str | None = None
    interval: str
    range: str
    data: list[HistoricalPrice]
'@

Set-Content `
    -Path (Join-Path $schemasDir "market.py") `
    -Value $marketSchema `
    -Encoding UTF8

Write-Host "Created app\schemas\market.py" -ForegroundColor Green


# ============================================================
# 3. Create provider abstraction
# ============================================================

Write-Host ""
Write-Host "[3/12] Creating market data provider..." -ForegroundColor Cyan

$providersDir = Join-Path $backend "app\providers"
New-Item -ItemType Directory -Force -Path $providersDir | Out-Null

$providerInit = @'
'@

Set-Content `
    -Path (Join-Path $providersDir "__init__.py") `
    -Value $providerInit `
    -Encoding UTF8

$providerCode = @'
from dataclasses import dataclass
from datetime import datetime

import httpx


class MarketDataProviderError(Exception):
    """Raised when a market-data provider cannot return valid data."""


@dataclass
class QuoteData:
    symbol: str
    name: str | None
    currency: str | None
    exchange: str | None
    price: float
    previous_close: float | None
    change: float | None
    change_percent: float | None
    market_time: datetime | None


@dataclass
class HistoricalData:
    symbol: str
    currency: str | None
    interval: str
    range: str
    data: list[dict]


class YahooFinanceProvider:
    """Yahoo Finance chart-data provider.

    The provider is isolated behind this class so it can be replaced
    later by Dhan or another production market-data provider.
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def _get_chart(self, symbol: str, range_: str, interval: str) -> dict:
        symbol = symbol.strip().upper()

        if not symbol:
            raise MarketDataProviderError("Symbol is required")

        url = f"{self.BASE_URL}/{symbol}"

        try:
            response = httpx.get(
                url,
                params={
                    "range": range_,
                    "interval": interval,
                    "includePrePost": "false",
                    "events": "div,splits",
                },
                timeout=self.timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPError as exc:
            raise MarketDataProviderError(
                f"Market data provider request failed: {exc}"
            ) from exc

        except ValueError as exc:
            raise MarketDataProviderError(
                "Market data provider returned invalid JSON"
            ) from exc

        chart = payload.get("chart", {})
        error = chart.get("error")

        if error:
            description = error.get("description") or "Unknown provider error"
            raise MarketDataProviderError(description)

        results = chart.get("result") or []

        if not results:
            raise MarketDataProviderError(
                f"No market data found for symbol {symbol}"
            )

        return results[0]

    def get_quote(self, symbol: str) -> QuoteData:
        result = self._get_chart(symbol, "1d", "1d")

        meta = result.get("meta", {})

        price = meta.get("regularMarketPrice")

        if price is None:
            raise MarketDataProviderError(
                f"Current price unavailable for {symbol.upper()}"
            )

        previous_close = meta.get("previousClose")

        change = None
        change_percent = None

        if previous_close is not None:
            change = price - previous_close

            if previous_close != 0:
                change_percent = (change / previous_close) * 100

        market_time = None

        if meta.get("regularMarketTime"):
            market_time = datetime.fromtimestamp(
                meta["regularMarketTime"]
            )

        return QuoteData(
            symbol=meta.get("symbol") or symbol.upper(),
            name=meta.get("shortName") or meta.get("longName"),
            currency=meta.get("currency"),
            exchange=meta.get("exchangeName"),
            price=float(price),
            previous_close=(
                float(previous_close)
                if previous_close is not None
                else None
            ),
            change=change,
            change_percent=change_percent,
            market_time=market_time,
        )

    def get_history(
        self,
        symbol: str,
        range_: str = "1mo",
        interval: str = "1d",
    ) -> HistoricalData:

        result = self._get_chart(symbol, range_, interval)

        meta = result.get("meta", {})
        timestamps = result.get("timestamp") or []

        indicators = result.get("indicators", {})
        quotes = indicators.get("quote") or [{}]
        quote = quotes[0]

        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []

        data = []

        for index, timestamp in enumerate(timestamps):

            def value(values):
                if index >= len(values):
                    return None
                return values[index]

            data.append(
                {
                    "timestamp": datetime.fromtimestamp(timestamp),
                    "open": value(opens),
                    "high": value(highs),
                    "low": value(lows),
                    "close": value(closes),
                    "volume": value(volumes),
                }
            )

        return HistoricalData(
            symbol=meta.get("symbol") or symbol.upper(),
            currency=meta.get("currency"),
            interval=interval,
            range=range_,
            data=data,
        )
'@

Set-Content `
    -Path (Join-Path $providersDir "market_data.py") `
    -Value $providerCode `
    -Encoding UTF8

Write-Host "Created Yahoo Finance provider." -ForegroundColor Green


# ============================================================
# 4. Create market service
# ============================================================

Write-Host ""
Write-Host "[4/12] Creating market data service..." -ForegroundColor Cyan

$servicesDir = Join-Path $backend "app\services"
New-Item -ItemType Directory -Force -Path $servicesDir | Out-Null

$serviceCode = @'
from app.providers.market_data import (
    HistoricalData,
    MarketDataProviderError,
    QuoteData,
    YahooFinanceProvider,
)

_provider = YahooFinanceProvider()


def get_quote(symbol: str) -> QuoteData:
    return _provider.get_quote(symbol)


def get_history(
    symbol: str,
    range_: str = "1mo",
    interval: str = "1d",
) -> HistoricalData:
    return _provider.get_history(
        symbol=symbol,
        range_=range_,
        interval=interval,
    )


__all__ = [
    "get_quote",
    "get_history",
    "MarketDataProviderError",
]
'@

Set-Content `
    -Path (Join-Path $servicesDir "market_service.py") `
    -Value $serviceCode `
    -Encoding UTF8

Write-Host "Created app\services\market_service.py" -ForegroundColor Green


# ============================================================
# 5. Create market API
# ============================================================

Write-Host ""
Write-Host "[5/12] Creating market API..." -ForegroundColor Cyan

$apiDir = Join-Path $backend "app\api\v1"
New-Item -ItemType Directory -Force -Path $apiDir | Out-Null

$apiCode = @'
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.market import HistoryResponse, QuoteResponse
from app.services.market_service import (
    MarketDataProviderError,
    get_history,
    get_quote,
)

router = APIRouter(
    prefix="/market",
    tags=["Market Data"],
)


@router.get(
    "/quote/{symbol}",
    response_model=QuoteResponse,
)
def market_quote(symbol: str):
    try:
        quote = get_quote(symbol)

    except MarketDataProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return QuoteResponse(
        symbol=quote.symbol,
        name=quote.name,
        currency=quote.currency,
        exchange=quote.exchange,
        price=quote.price,
        previous_close=quote.previous_close,
        change=quote.change,
        change_percent=quote.change_percent,
        market_time=quote.market_time,
    )


@router.get(
    "/history/{symbol}",
    response_model=HistoryResponse,
)
def market_history(
    symbol: str,
    range_: str = Query(
        default="1mo",
        alias="range",
    ),
    interval: str = Query(
        default="1d",
    ),
):
    allowed_ranges = {
        "1d",
        "5d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max",
    }

    allowed_intervals = {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }

    if range_ not in allowed_ranges:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid range",
        )

    if interval not in allowed_intervals:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid interval",
        )

    try:
        history = get_history(
            symbol=symbol,
            range_=range_,
            interval=interval,
        )

    except MarketDataProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return HistoryResponse(
        symbol=history.symbol,
        currency=history.currency,
        interval=history.interval,
        range=history.range,
        data=history.data,
    )
'@

Set-Content `
    -Path (Join-Path $apiDir "market.py") `
    -Value $apiCode `
    -Encoding UTF8

Write-Host "Created app\api\v1\market.py" -ForegroundColor Green


# ============================================================
# 6. Register market router
# ============================================================

Write-Host ""
Write-Host "[6/12] Registering market API..." -ForegroundColor Cyan

$mainFile = Join-Path $backend "main.py"
$mainContent = Get-Content $mainFile -Raw

$marketImport =
    "from app.api.v1.market import router as market_router"

if (-not $mainContent.Contains($marketImport)) {

    $usersImport =
        "from app.api.v1.users import router as users_router"

    if (-not $mainContent.Contains($usersImport)) {
        throw "Could not find users router import in main.py."
    }

    $mainContent = $mainContent.Replace(
        $usersImport,
        $usersImport + "`r`n" + $marketImport
    )
}

$marketRegistration =
    "app.include_router(`r`n    market_router,`r`n    prefix=`"/api/v1`",`r`n)"

if (-not $mainContent.Contains("market_router")) {
    throw "Market router import/registration could not be prepared."
}

if (-not $mainContent.Contains("market_router,`r`n    prefix")) {

    $portfolioRegistration =
        "app.include_router(`r`n    portfolio_router,`r`n    prefix=`"/api/v1`",`r`n)"

    if ($mainContent.Contains($portfolioRegistration)) {

        $mainContent = $mainContent.Replace(
            $portfolioRegistration,
            $portfolioRegistration + "`r`n" + $marketRegistration
        )

    }
    else {

        throw "Could not find portfolio router registration in main.py."
    }
}

$mainContent = $mainContent.TrimEnd() + "`r`n"

[System.IO.File]::WriteAllText(
    (Resolve-Path $mainFile),
    $mainContent,
    (New-Object System.Text.UTF8Encoding($false))
)

Write-Host "Market router registered." -ForegroundColor Green


# ============================================================
# 7. Create market tests
# ============================================================

Write-Host ""
Write-Host "[7/12] Creating market-data tests..." -ForegroundColor Cyan

$testDir = Join-Path $backend "app\tests"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

$testCode = @'
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def fake_quote(symbol):
    from app.providers.market_data import QuoteData

    return QuoteData(
        symbol=symbol.upper(),
        name="Test Company",
        currency="USD",
        exchange="TEST",
        price=100.0,
        previous_close=95.0,
        change=5.0,
        change_percent=5.2631578947,
        market_time=datetime(2026, 1, 1, 10, 0, 0),
    )


def fake_history(symbol, range_="1mo", interval="1d"):
    from app.providers.market_data import HistoricalData

    return HistoricalData(
        symbol=symbol.upper(),
        currency="USD",
        interval=interval,
        range=range_,
        data=[
            {
                "timestamp": datetime(2026, 1, 1),
                "open": 95.0,
                "high": 102.0,
                "low": 94.0,
                "close": 100.0,
                "volume": 100000,
            }
        ],
    )


@patch("app.api.v1.market.get_quote", side_effect=fake_quote)
def test_get_market_quote(mock_quote):
    response = client.get("/api/v1/market/quote/AAPL")

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "AAPL"
    assert data["price"] == 100.0
    assert data["previous_close"] == 95.0
    assert data["change"] == 5.0

    mock_quote.assert_called_once_with("AAPL")


@patch("app.api.v1.market.get_history", side_effect=fake_history)
def test_get_market_history(mock_history):
    response = client.get(
        "/api/v1/market/history/AAPL"
        "?range=1mo&interval=1d"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "AAPL"
    assert data["range"] == "1mo"
    assert data["interval"] == "1d"
    assert len(data["data"]) == 1
    assert data["data"][0]["close"] == 100.0

    mock_history.assert_called_once_with(
        symbol="AAPL",
        range_="1mo",
        interval="1d",
    )


def test_invalid_market_range():
    response = client.get(
        "/api/v1/market/history/AAPL"
        "?range=invalid&interval=1d"
    )

    assert response.status_code == 422


def test_invalid_market_interval():
    response = client.get(
        "/api/v1/market/history/AAPL"
        "?range=1mo&interval=invalid"
    )

    assert response.status_code == 422


@patch("app.api.v1.market.get_quote")
def test_market_provider_error_returns_404(mock_quote):
    from app.services.market_service import MarketDataProviderError

    mock_quote.side_effect = MarketDataProviderError(
        "No market data found"
    )

    response = client.get("/api/v1/market/quote/INVALID")

    assert response.status_code == 404
    assert response.json()["detail"] == "No market data found"
'@

Set-Content `
    -Path (Join-Path $testDir "test_market.py") `
    -Value $testCode `
    -Encoding UTF8

Write-Host "Created market-data tests." -ForegroundColor Green


# ============================================================
# 8. Create frontend market service
# ============================================================

Write-Host ""
Write-Host "[8/12] Creating frontend market integration..." -ForegroundColor Cyan

$frontendServices = Join-Path $root "frontend\src\services"
$frontendPages = Join-Path $root "frontend\src\pages"

New-Item -ItemType Directory -Force -Path $frontendServices | Out-Null
New-Item -ItemType Directory -Force -Path $frontendPages | Out-Null

$frontendService = @'
import { api } from "./api";

export interface Quote {
  symbol: string;
  name: string | null;
  currency: string | null;
  exchange: string | null;
  price: number;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  market_time: string | null;
}

export interface HistoricalPrice {
  timestamp: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface HistoryResponse {
  symbol: string;
  currency: string | null;
  interval: string;
  range: string;
  data: HistoricalPrice[];
}

export async function getQuote(symbol: string): Promise<Quote> {
  return api.get<Quote>(`/market/quote/${encodeURIComponent(symbol)}`);
}

export async function getHistory(
  symbol: string,
  range = "1mo",
  interval = "1d",
): Promise<HistoryResponse> {
  return api.get<HistoryResponse>(
    `/market/history/${encodeURIComponent(symbol)}?range=${range}&interval=${interval}`,
  );
}
'@

Set-Content `
    -Path (Join-Path $frontendServices "market.ts") `
    -Value $frontendService `
    -Encoding UTF8


# ============================================================
# 9. Create Market page
# ============================================================

$marketPage = @'
import { useState } from "react";
import { getQuote, type Quote } from "../services/market";

export default function MarketPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search() {
    const normalized = symbol.trim().toUpperCase();

    if (!normalized) {
      setError("Enter a stock symbol.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await getQuote(normalized);
      setQuote(result);
    } catch (err) {
      setQuote(null);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load market data.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-bold text-slate-900">
          Market Data
        </h1>

        <p className="mt-2 text-slate-600">
          Search a stock symbol and view its latest market price.
        </p>

        <div className="mt-6 flex gap-3">
          <input
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                void search();
              }
            }}
            placeholder="AAPL"
            className="rounded-lg border border-slate-300 bg-white px-4 py-3 uppercase outline-none focus:border-slate-500"
          />

          <button
            type="button"
            onClick={() => void search()}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-5 py-3 font-medium text-white disabled:opacity-50"
          >
            {loading ? "Loading..." : "Search"}
          </button>
        </div>

        {error && (
          <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            {error}
          </div>
        )}

        {quote && (
          <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-slate-500">
                  {quote.exchange ?? "Market"}
                </p>

                <h2 className="mt-1 text-2xl font-bold text-slate-900">
                  {quote.symbol}
                </h2>

                {quote.name && (
                  <p className="mt-1 text-slate-500">
                    {quote.name}
                  </p>
                )}
              </div>

              <div className="text-right">
                <p className="text-3xl font-bold text-slate-900">
                  {quote.price.toFixed(2)}
                </p>

                {quote.change_percent !== null && (
                  <p className="mt-1 text-sm text-slate-600">
                    {quote.change_percent >= 0 ? "+" : ""}
                    {quote.change_percent.toFixed(2)}%
                  </p>
                )}
              </div>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-sm text-slate-500">
                  Previous Close
                </p>
                <p className="mt-1 font-semibold">
                  {quote.previous_close?.toFixed(2) ?? "-"}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-500">
                  Change
                </p>
                <p className="mt-1 font-semibold">
                  {quote.change !== null
                    ? `${quote.change >= 0 ? "+" : ""}${quote.change.toFixed(2)}`
                    : "-"}
                </p>
              </div>

              <div>
                <p className="text-sm text-slate-500">
                  Currency
                </p>
                <p className="mt-1 font-semibold">
                  {quote.currency ?? "-"}
                </p>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
'@

Set-Content `
    -Path (Join-Path $frontendPages "MarketPage.tsx") `
    -Value $marketPage `
    -Encoding UTF8

Write-Host "Created frontend market page." -ForegroundColor Green


# ============================================================
# 10. Update App navigation
# ============================================================

Write-Host ""
Write-Host "[10/12] Updating frontend navigation..." -ForegroundColor Cyan

$appFile = Join-Path $root "frontend\src\App.tsx"

if (Test-Path $appFile) {

    $appContent = Get-Content $appFile -Raw

    if (-not $appContent.Contains("MarketPage")) {

        $appContent = @'
import MarketPage from "./pages/MarketPage";

export default function App() {
  return <MarketPage />;
}
'@

        Set-Content `
            -Path $appFile `
            -Value $appContent `
            -Encoding UTF8

        Write-Host "Frontend now uses MarketPage." -ForegroundColor Green

    }
    else {

        Write-Host "MarketPage already referenced." -ForegroundColor Yellow
    }

}
else {

    Write-Host "App.tsx not found; frontend page was still created." -ForegroundColor Yellow
}


# ============================================================
# 11. Validate imports + run complete tests
# ============================================================

Write-Host ""
Write-Host "[11/12] Running backend validation..." -ForegroundColor Cyan

Push-Location $backend

try {

    & $python -c "from app.api.v1.market import router; print('Market router routes:', [(r.path, r.methods) for r in router.routes])"

    if ($LASTEXITCODE -ne 0) {
        throw "Market router import failed."
    }

    & $python -m pytest

    if ($LASTEXITCODE -ne 0) {
        throw "Backend test suite failed."
    }

}
finally {
    Pop-Location
}

Write-Host "Backend validation: PASS" -ForegroundColor Green


# ============================================================
# 12. Git validation
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
Write-Host " TP-007 MARKET DATA MVP COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Implemented:" -ForegroundColor Green
Write-Host "  TP-007.1 Market data provider abstraction"
Write-Host "  TP-007.2 Yahoo Finance provider"
Write-Host "  TP-007.3 Quote API"
Write-Host "  TP-007.4 Historical OHLCV API"
Write-Host "  TP-007.5 Market-data service"
Write-Host "  TP-007.6 API validation"
Write-Host "  TP-007.7 Market-data tests"
Write-Host "  TP-007.8 Frontend market service"
Write-Host "  TP-007.9 Market page"
Write-Host ""
Write-Host "No Git commit or push performed." -ForegroundColor Yellow
Write-Host ""