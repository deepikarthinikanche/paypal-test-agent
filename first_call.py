"""Run this first to confirm your PayPal sandbox setup works."""
from agent.paypal_client import PayPalClient, PayPalError

try:
    client = PayPalClient()
    client.get_token()
    print("Step 1 OK: got an access token")

    order = client.create_order("10.00", "USD")
    print("Step 2 OK: created order", order["id"], "| status:", order["status"])
    for link in order.get("links", []):
        if link["rel"] in ("approve", "payer-action"):
            print("Buyer approval link:", link["href"])
except (PayPalError, RuntimeError) as e:
    print("Failed:", e)
