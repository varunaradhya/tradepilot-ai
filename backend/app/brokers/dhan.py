from typing import Any

import httpx


class DhanAPIError(Exception):
    pass


class DhanClient:
    BASE_URL = "https://api.dhan.co/v2"

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        url = f"{self.BASE_URL}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access-token": self.access_token,
            "client-id": self.client_id,
        }
        try:
            response = httpx.request(method, url, headers=headers, json=json, timeout=20.0)
        except httpx.HTTPError as exc:
            raise DhanAPIError(f"Dhan connection failed: {exc}") from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            raise DhanAPIError(f"Dhan API returned {response.status_code}: {payload}")

        try:
            return response.json()
        except Exception as exc:
            raise DhanAPIError("Dhan returned invalid JSON.") from exc

    def profile(self):
        return self._request("GET", "/profile")

    def holdings(self):
        result = self._request("GET", "/holdings")
        return result or []

    def positions(self):
        result = self._request("GET", "/positions")
        return result or []

    def orders(self):
        result = self._request("GET", "/orders")
        return result or []

    def trades(self):
        result = self._request("GET", "/trades")
        return result or []

    def historical_daily(
        self,
        security_id: str,
        exchange_segment: str,
        instrument: str,
        from_date: str,
        to_date: str,
        oi: bool = False,
    ):
        return self._request(
            "POST",
            "/charts/historical",
            {
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": instrument,
                "expiryCode": 0,
                "oi": oi,
                "fromDate": from_date,
                "toDate": to_date,
            },
        )

    def historical_intraday(
        self,
        security_id: str,
        exchange_segment: str,
        instrument: str,
        interval: str,
        from_date: str,
        to_date: str,
        oi: bool = False,
    ):
        return self._request(
            "POST",
            "/charts/intraday",
            {
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": instrument,
                "interval": interval,
                "oi": oi,
                "fromDate": from_date,
                "toDate": to_date,
            },
        )
