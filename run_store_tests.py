"""Test the demo store's /checkout endpoint, then verify what PayPal actually received.

1. Start the store in another terminal:  uvicorn demo_store.app:app --port 8000
2. Run this file:                         python run_store_tests.py
"""
import json
import os
from datetime import datetime, timezone

import httpx

from agent.paypal_client import PayPalClient

STORE_URL = os.getenv("STORE_URL", "http://127.0.0.1:8000")


def post_checkout(payload):
    r = httpx.post(f"{STORE_URL}/checkout", json=payload, timeout=60)
    try:
        body = r.json()
    except ValueError:
        body = r.text
    return r.status_code, body


def check_amount(paypal, amount):
    """The order PayPal received must match the amount the customer asked to pay."""
    requested = f"{amount:.2f}"
    status, body = post_checkout({"amount": amount, "currency": "USD"})
    if status != 200:
        return False, f"HTTP 200 and a PayPal order for {requested} USD", f"HTTP {status}: {str(body)[:200]}"
    order = paypal.get_order(body["order_id"])
    charged = order["purchase_units"][0]["amount"]["value"]
    return (
        charged == requested,
        f"PayPal order amount {requested} USD",
        f"PayPal order amount {charged} USD",
    )


def check_rejects(amount):
    """Bad input must be rejected with a clean 400, not a server crash."""
    status, body = post_checkout({"amount": amount, "currency": "USD"})
    return status == 400, "HTTP 400 (clean client error)", f"HTTP {status}: {str(body)[:200]}"


def check_missing_amount():
    status, body = post_checkout({"currency": "USD"})
    return status == 422, "HTTP 422 (missing field rejected)", f"HTTP {status}"


def build_checks(paypal):
    return [
        ("exact_amount_10_00", "Charge exactly 10.00 USD", "Baseline: a round amount.",
         lambda: check_amount(paypal, 10.00)),
        ("exact_amount_19_99", "Charge exactly 19.99 USD", "Customer is charged the amount shown.",
         lambda: check_amount(paypal, 19.99)),
        ("exact_amount_1_15", "Charge exactly 1.15 USD", "Another amount that is tricky for float math.",
         lambda: check_amount(paypal, 1.15)),
        ("negative_amount", "Reject a negative amount", "Invalid input should give a clean 400.",
         lambda: check_rejects(-5.00)),
        ("zero_amount", "Reject a zero amount", "Invalid input should give a clean 400.",
         lambda: check_rejects(0)),
        ("missing_amount", "Reject a request with no amount", "Missing fields should give 422.",
         check_missing_amount),
    ]


def main():
    try:
        health = httpx.get(f"{STORE_URL}/health", timeout=10).json()
    except httpx.HTTPError:
        print(f"Cannot reach the store at {STORE_URL}.")
        print("Start it in another terminal:  uvicorn demo_store.app:app --port 8000")
        return
    print("Store is up. Bugs enabled:", health.get("bugs_enabled"), "\n")

    paypal = PayPalClient()
    results = []
    for cid, name, description, fn in build_checks(paypal):
        try:
            passed, expected, actual = fn()
            error = None
        except Exception as e:
            passed, expected, actual, error = False, "check to run", "check crashed", str(e)
        results.append({
            "id": cid, "name": name, "description": description,
            "expected": expected, "actual": actual, "passed": passed, "exception": error,
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        if not passed:
            print(f"       expected: {expected}\n       actual:   {actual}")

    ok = sum(r["passed"] for r in results)
    print(f"\n{ok}/{len(results)} checks passed")

    os.makedirs("results", exist_ok=True)
    with open("results/store_latest.json", "w", encoding="utf-8") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "bugs_enabled": health.get("bugs_enabled"),
            "passed": ok, "total": len(results), "results": results,
        }, f, indent=2)
    print("Saved results/store_latest.json")


if __name__ == "__main__":
    main()
