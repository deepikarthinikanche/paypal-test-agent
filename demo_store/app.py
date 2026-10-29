"""A tiny demo store with a /checkout endpoint backed by the PayPal Sandbox.

It ships with deliberate bugs so the test agent has something real to catch.
Run with bugs ON (default):   uvicorn demo_store.app:app --port 8000
Run with bugs OFF (fixed):    set DEMO_BUGS=off   (PowerShell: $env:DEMO_BUGS="off")
"""
import os
from decimal import ROUND_HALF_UP, Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.paypal_client import PayPalClient, PayPalError

app = FastAPI(title="Demo Store")
BUGS = os.getenv("DEMO_BUGS", "on").lower() == "on"
paypal = PayPalClient()


class CheckoutRequest(BaseModel):
    amount: float
    currency: str = "USD"


def format_amount(amount: float) -> str:
    if BUGS:
        # BUG 1: float math truncates cents. 19.99 * 100 = 1998.99999..., int() -> 1998,
        # so the customer is charged 19.98 instead of 19.99.
        cents = int(amount * 100)
        return f"{cents / 100:.2f}"
    # FIXED: use Decimal and round to the nearest cent.
    return str(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


@app.get("/health")
def health():
    return {"status": "ok", "bugs_enabled": BUGS}


@app.post("/checkout")
def checkout(req: CheckoutRequest):
    if not BUGS and req.amount <= 0:
        # FIXED: reject bad input with a clean 400 before calling PayPal.
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    try:
        order = paypal.create_order(format_amount(req.amount), req.currency)
    except PayPalError as e:
        if BUGS:
            # BUG 2: no error handling. Invalid input crashes into a 500 and
            # leaks PayPal's raw error to the customer.
            raise
        raise HTTPException(status_code=400, detail="Payment provider rejected the request")

    approve_url = next(
        (l["href"] for l in order.get("links", []) if l["rel"] in ("approve", "payer-action")),
        None,
    )
    return {"order_id": order["id"], "status": order["status"], "approve_url": approve_url}
