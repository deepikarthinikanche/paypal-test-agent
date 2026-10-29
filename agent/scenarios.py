"""Scenario library.

Each scenario sends one request (or a short sequence) to the PayPal Sandbox and
states which HTTP status codes count as the CORRECT behaviour. The runner compares
what PayPal actually did against that expectation.
"""
from dataclasses import dataclass
from typing import Callable


def order_body(amount, currency, intent="CAPTURE"):
    body = {
        "purchase_units": [
            {"amount": {"currency_code": currency, "value": amount}}
        ]
    }
    if intent:
        body["intent"] = intent
    return body


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    expected: tuple  # HTTP status codes that count as correct behaviour
    run: Callable    # takes a PayPalClient, returns (status_code, body)


def _create(amount, currency, intent="CAPTURE"):
    def run(c):
        return c.request("POST", "/v2/checkout/orders", order_body(amount, currency, intent))
    return run


def _capture_unapproved(c):
    status, body = c.request("POST", "/v2/checkout/orders", order_body("10.00", "USD"))
    if status not in (200, 201):
        return status, body
    return c.request("POST", f"/v2/checkout/orders/{body['id']}/capture", {})


def _get_order_after_create(c):
    status, body = c.request("POST", "/v2/checkout/orders", order_body("10.00", "USD"))
    if status not in (200, 201):
        return status, body
    return c.request("GET", f"/v2/checkout/orders/{body['id']}")


def build_scenarios():
    return [
        Scenario("valid_order", "Create a valid order",
                 "10.00 USD order with intent CAPTURE should be created.",
                 (200, 201), _create("10.00", "USD")),
        Scenario("get_order_after_create", "Fetch an order right after creating it",
                 "A newly created order should be readable.",
                 (200,), _get_order_after_create),
        Scenario("zero_amount", "Order with zero amount",
                 "A 0.00 USD order should be rejected.",
                 (400, 422), _create("0.00", "USD")),
        Scenario("negative_amount", "Order with negative amount",
                 "A -5.00 USD order should be rejected.",
                 (400, 422), _create("-5.00", "USD")),
        Scenario("bad_currency", "Order with an invalid currency code",
                 "Currency code XYZ is not real and should be rejected.",
                 (400, 422), _create("10.00", "XYZ")),
        Scenario("too_many_decimals", "Amount with too many decimal places",
                 "10.999 USD has more precision than USD allows.",
                 (400, 422), _create("10.999", "USD")),
        Scenario("missing_intent", "Order with no intent",
                 "The intent field is required and should be enforced.",
                 (400, 422), _create("10.00", "USD", intent=None)),
        Scenario("capture_unapproved", "Capture an order the buyer never approved",
                 "Capturing before buyer approval must fail.",
                 (400, 422), _capture_unapproved),
        Scenario("get_missing_order", "Fetch an order that does not exist",
                 "A made-up order ID should return not found.",
                 (400, 404), lambda c: c.request("GET", "/v2/checkout/orders/DOESNOTEXIST123")),
        Scenario("refund_missing_capture", "Refund a capture that does not exist",
                 "Refunding a made-up capture ID should fail.",
                 (400, 404), lambda c: c.request("POST", "/v2/payments/captures/DOESNOTEXIST123/refund", {})),
        Scenario("invalid_token", "Call the API with an invalid access token",
                 "A bad token should return 401 Unauthorized.",
                 (401,), lambda c: c.request("GET", "/v2/checkout/orders/ANYID", auth=False)),
    ]
