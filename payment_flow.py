"""Full sandbox flow: create order -> buyer approves -> capture -> refund."""
from agent.paypal_client import PayPalClient, PayPalError

try:
    client = PayPalClient()

    order = client.create_order("10.00", "USD")
    print("Created order:", order["id"])
    approve = next(
        l["href"] for l in order["links"] if l["rel"] in ("approve", "payer-action")
    )
    print("\n1) Open this link in an incognito window:\n  ", approve)
    print("2) Log in with your sandbox PERSONAL (buyer) account and approve.")
    input("3) Press Enter here once you have approved the payment... ")

    captured = client.capture_order(order["id"])
    capture_id = client.capture_id_from(captured)
    print("\nCaptured. Status:", captured["status"], "| capture ID:", capture_id)

    refund = client.refund_capture(capture_id, "4.00", "USD")
    print("Partial refund of 4.00 USD -> status:", refund["status"], "| id:", refund["id"])
except (PayPalError, RuntimeError) as e:
    print("Failed:", e)
