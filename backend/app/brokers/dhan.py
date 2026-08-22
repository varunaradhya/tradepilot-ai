from typing import Any
import random
import time

import httpx


class DhanAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DhanClient:
    BASE_URL = "https://api.dhan.co/v2"

    def __init__(self, client_id: str, access_token: str, max_retries: int = 5):
        self.client_id = client_id.strip()
        self.access_token = access_token.strip()
        self.max_retries = max(0, int(max_retries))

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None, *, include_client_id: bool = True) -> Any:
        headers = {"Accept": "application/json", "Content-Type": "application/json", "access-token": self.access_token}
        if include_client_id:
            headers["client-id"] = self.client_id
        for attempt in range(self.max_retries + 1):
            try:
                r = httpx.request(method, f"{self.BASE_URL}{path}", headers=headers, json=json, timeout=30.0)
            except httpx.RequestError as exc:
                if attempt >= self.max_retries:
                    raise DhanAPIError(f"Dhan connection failed after {attempt + 1} attempts: {exc}") from exc
                delay = min(20.0, 1.5 * (2 ** attempt)) + random.uniform(0, 0.5)
                print(f"Dhan connection retry {attempt + 1}/{self.max_retries} in {delay:.1f}s: {exc}", flush=True)
                time.sleep(delay)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                if attempt >= self.max_retries:
                    try: p = r.json()
                    except Exception: p = r.text
                    raise DhanAPIError(f"Dhan API returned {r.status_code} after {attempt + 1} attempts: {p}", r.status_code)
                retry_after = r.headers.get("Retry-After")
                try: delay = float(retry_after) if retry_after else min(20.0, 1.5 * (2 ** attempt))
                except ValueError: delay = min(20.0, 1.5 * (2 ** attempt))
                delay += random.uniform(0, 0.5)
                print(f"Dhan HTTP {r.status_code} retry {attempt + 1}/{self.max_retries} in {delay:.1f}s", flush=True)
                time.sleep(delay)
                continue
            if r.status_code >= 400:
                try: p = r.json()
                except Exception: p = r.text
                if r.status_code == 401:
                    raise DhanAPIError("Dhan authentication failed (401). The saved access token is invalid or expired. Reconnect Dhan with a fresh access token.", 401)
                raise DhanAPIError(f"Dhan API returned {r.status_code}: {p}", r.status_code)
            try: return r.json()
            except Exception as exc: raise DhanAPIError("Dhan returned invalid JSON.") from exc
        raise DhanAPIError("Dhan request failed unexpectedly.")

    def profile(self):
        # Dhan's profile endpoint authenticates with the access token; client-id is
        # required by market/trading endpoints but is not part of this contract.
        return self._request("GET", "/profile", include_client_id=False)

    def holdings(self): return self._request("GET", "/holdings") or []
    def positions(self): return self._request("GET", "/positions") or []
    def orders(self): return self._request("GET", "/orders") or []
    def trades(self): return self._request("GET", "/trades") or []

    def market_ltp(self, exchange_segment: str, security_ids: list[str]) -> dict[str, Any]:
        """Return real-time LTP snapshots without placing orders."""
        if not security_ids:
            return {"data": {}, "status": "success"}
        return self._request("POST", "/marketfeed/ltp", {exchange_segment: [int(x) for x in security_ids]})

    def market_ohlc(self, exchange_segment: str, security_ids: list[str]) -> dict[str, Any]:
        return self._request("POST", "/marketfeed/ohlc", {exchange_segment: [int(x) for x in security_ids]})

    def market_quote(self, exchange_segment: str, security_ids: list[str]) -> dict[str, Any]:
        """Return executable-side quote data (best bid/ask) for paper marking."""
        if not security_ids:
            return {"data": {}, "status": "success"}
        return self._request("POST", "/marketfeed/quote", {exchange_segment: [int(x) for x in security_ids]})

    def option_expiries(self, underlying_security_id: int, underlying_segment: str):
        return self._request("POST", "/optionchain/expirylist", {"UnderlyingScrip": underlying_security_id, "UnderlyingSeg": underlying_segment})

    def option_chain(self, underlying_security_id: int, underlying_segment: str, expiry: str):
        return self._request("POST", "/optionchain", {"UnderlyingScrip": underlying_security_id, "UnderlyingSeg": underlying_segment, "Expiry": expiry})

    def place_order(self, order: dict[str, Any]): return self._request("POST", "/orders", order)
    def get_order(self, order_id: str): return self._request("GET", f"/orders/{order_id}")
    def cancel_order(self, order_id: str): return self._request("DELETE", f"/orders/{order_id}")

    def pnl_exit(self, profit_value: float, loss_value: float, product_types: list[str] | None = None, enable_kill_switch: bool = True):
        return self._request("POST", "/pnlExit", {"profitValue": f"{profit_value:.2f}", "lossValue": f"{loss_value:.2f}", "productType": product_types or ["INTRADAY"], "enableKillSwitch": enable_kill_switch})

    def pnl_exit_status(self): return self._request("GET", "/pnlExit")
    def activate_kill_switch(self): return self._request("POST", "/killswitch?killSwitchStatus=ACTIVATE")
    def deactivate_kill_switch(self): return self._request("POST", "/killswitch?killSwitchStatus=DEACTIVATE")
    def kill_switch_status(self): return self._request("GET", "/killswitch")

    def historical_daily(self, security_id: str, exchange_segment: str, instrument: str, from_date: str, to_date: str, oi: bool = False, expiry_code: int = 0):
        return self._request("POST", "/charts/historical", {"securityId": security_id, "exchangeSegment": exchange_segment, "instrument": instrument, "expiryCode": expiry_code, "oi": oi, "fromDate": from_date, "toDate": to_date})

    def historical_intraday(self, security_id: str, exchange_segment: str, instrument: str, interval: str, from_date: str, to_date: str, oi: bool = False, expiry_code: int = 0):
        return self._request("POST", "/charts/intraday", {"securityId": security_id, "exchangeSegment": exchange_segment, "instrument": instrument, "interval": interval, "expiryCode": expiry_code, "oi": oi, "fromDate": from_date, "toDate": to_date})

    def rolling_option(self, security_id: str, expiry_flag: str, expiry_code: int, strike: str, option_type: str, from_date: str, to_date: str, interval: str = "5"):
        if expiry_code not in (0, 1, 2):
            raise ValueError("rolling option expiry_code must be 0/1/2 (0=current/near, 1=next, 2=far expiry)")
        payload = {"exchangeSegment": "NSE_FNO", "interval": interval, "securityId": security_id, "instrument": "OPTIDX", "expiryFlag": expiry_flag, "expiryCode": expiry_code, "strike": strike, "drvOptionType": option_type, "requiredData": ["open", "high", "low", "close", "iv", "volume", "strike", "oi", "spot"], "fromDate": from_date, "toDate": to_date}
        try:
            return self._request("POST", "/charts/rollingoption", payload)
        except DhanAPIError as exc:
            if expiry_code == 0 and "DH-905" in str(exc) and "expiryCode" in str(exc):
                fallback = dict(payload)
                fallback["expiryCode"] = 1
                return self._request("POST", "/charts/rollingoption", fallback)
            raise
