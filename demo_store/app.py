"""A tiny demo store with a /checkout endpoint backed by the PayPal Sandbox.

Default mode:    uvicorn demo_store.app:app --port 8000
Corrected mode:  set DEMO_BUGS=off   (PowerShell: $env:DEMO_BUGS="off")
"""
import os
from decimal import ROUND_HALF_UP, Decimal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent.paypal_client import PayPalClient, PayPalError

app = FastAPI(title="Demo Store")
BUGS = os.getenv("DEMO_BUGS", "on").lower() == "on"
paypal = PayPalClient()


class CheckoutRequest(BaseModel):
    amount: float
    currency: str = "USD"


def format_amount(amount: float, bugs: bool) -> str:
    if bugs:
        # Convert dollars to cents.
        cents = int(amount * 100)
        return f"{cents / 100:.2f}"
    # Exact decimal arithmetic, rounded to the nearest cent.
    return str(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def process_checkout(client, amount: float, currency: str, bugs: bool):
    """Create a PayPal order for a checkout. Returns (http_status, body)."""
    if not bugs and amount <= 0:
        # Reject invalid amounts before calling the payment provider.
        return 400, {"detail": "Amount must be greater than zero"}

    try:
        order = client.create_order(format_amount(amount, bugs), currency)
    except PayPalError as e:
        if bugs:
            # The provider rejected the order.
            return 500, {"detail": f"Unhandled error: {e}"}
        return 400, {"detail": "Payment provider rejected the request"}

    approve_url = next(
        (l["href"] for l in order.get("links", []) if l["rel"] in ("approve", "payer-action")),
        None,
    )
    return 200, {"order_id": order["id"], "status": order["status"], "approve_url": approve_url}


@app.get("/health")
def health():
    return {"status": "ok", "bugs_enabled": BUGS}


@app.post("/checkout")
def checkout(req: CheckoutRequest):
    status, body = process_checkout(paypal, req.amount, req.currency, BUGS)
    return JSONResponse(status_code=status, content=body)