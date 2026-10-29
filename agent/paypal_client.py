"""Minimal PayPal Sandbox client: auth + orders."""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

SANDBOX_URL = "https://api-m.sandbox.paypal.com"


class PayPalError(Exception):
    """Raised when PayPal returns an error response."""


class PayPalClient:
    def __init__(self, client_id=None, secret=None):
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID")
        self.secret = secret or os.getenv("PAYPAL_SECRET")
        if not self.client_id or not self.secret:
            raise RuntimeError(
                "Missing PAYPAL_CLIENT_ID or PAYPAL_SECRET. "
                "Copy .env.example to .env and fill it in."
            )
        self._token = None
        self._http = httpx.Client(base_url=SANDBOX_URL, timeout=30)

    @staticmethod
    def _check(resp):
        if resp.status_code >= 400:
            raise PayPalError(f"{resp.status_code}: {resp.text}")
        return resp.json()

    def get_token(self):
        resp = self._http.post(
            "/v1/oauth2/token",
            auth=(self.client_id, self.secret),
            data={"grant_type": "client_credentials"},
        )
        self._token = self._check(resp)["access_token"]
        return self._token

    def _headers(self):
        if not self._token:
            self.get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def create_order(self, amount="10.00", currency="USD"):
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {"amount": {"currency_code": currency, "value": amount}}
            ],
        }
        resp = self._http.post("/v2/checkout/orders", json=body, headers=self._headers())
        return self._check(resp)

    def get_order(self, order_id):
        resp = self._http.get(f"/v2/checkout/orders/{order_id}", headers=self._headers())
        return self._check(resp)

    def capture_order(self, order_id):
        """Capture an order. The buyer must have approved it first."""
        resp = self._http.post(
            f"/v2/checkout/orders/{order_id}/capture",
            json={},
            headers=self._headers(),
        )
        return self._check(resp)

    @staticmethod
    def capture_id_from(order):
        """Pull the capture ID out of a captured order response."""
        return order["purchase_units"][0]["payments"]["captures"][0]["id"]

    def refund_capture(self, capture_id, amount=None, currency="USD"):
        """Refund a capture. Leave amount empty for a full refund."""
        body = {}
        if amount is not None:
            body = {"amount": {"currency_code": currency, "value": amount}}
        resp = self._http.post(
            f"/v2/payments/captures/{capture_id}/refund",
            json=body,
            headers=self._headers(),
        )
        return self._check(resp)
