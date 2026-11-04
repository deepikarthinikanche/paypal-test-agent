"""Live demo server. Runs the store checks in-process and serves the dashboard.

Local:   uvicorn web_app:app --port 8080      then open http://127.0.0.1:8080
Render:  uvicorn web_app:app --host 0.0.0.0 --port $PORT
"""
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError

from agent.analyzer import explain_failures
from agent.paypal_client import PayPalError
from demo_store.app import CheckoutRequest, paypal, process_checkout

ROOT = Path(__file__).parent
app = FastAPI(title="PayAudit AI (live demo)")

CACHE_SECONDS = 60          # repeat clicks reuse a fresh result (protects the sandbox)
_run_lock = threading.Lock()  # one run at a time
_runs = {}                  # "on" / "off" -> (timestamp, result)
_explanations = {}          # (mode, failed ids) -> Gemini analysis

CHECKS = [
    ("exact_amount_10_00", "Charge exactly 10.00 USD", "amount", 10.00),
    ("exact_amount_19_99", "Charge exactly 19.99 USD", "amount", 19.99),
    ("exact_amount_1_15", "Charge exactly 1.15 USD", "amount", 1.15),
    ("negative_amount", "Reject a negative amount", "reject", -5.00),
    ("zero_amount", "Reject a zero amount", "reject", 0),
    ("missing_amount", "Reject a request with no amount", "missing", None),
]


def run_one(kind, amount, bugs):
    """Returns (passed, expected, actual, paypal_order_id)."""
    if kind == "amount":
        requested = f"{amount:.2f}"
        status, body = process_checkout(paypal, amount, "USD", bugs)
        if status != 200:
            return False, f"PayPal order for {requested} USD", f"HTTP {status}: {str(body)[:160]}", None
        order = paypal.get_order(body["order_id"])  # ask PayPal what it really received
        charged = order["purchase_units"][0]["amount"]["value"]
        return (charged == requested, f"PayPal order amount {requested} USD",
                f"PayPal order amount {charged} USD", body["order_id"])
    if kind == "reject":
        status, body = process_checkout(paypal, amount, "USD", bugs)
        return status == 400, "HTTP 400 (clean client error)", f"HTTP {status}: {str(body)[:160]}", None
    try:  # kind == "missing": the request model must refuse a body with no amount
        CheckoutRequest(**{"currency": "USD"})
        status = 200
    except ValidationError:
        status = 422
    return status == 422, "HTTP 422 (missing field rejected)", f"HTTP {status}", None


def run_checks(bugs):
    results = []
    for cid, name, kind, amount in CHECKS:
        try:
            passed, expected, actual, order_id = run_one(kind, amount, bugs)
        except Exception as e:  # keep going if one check hits a PayPal problem
            passed, expected, actual, order_id = False, "check to run", f"check crashed: {str(e)[:120]}", None
        results.append({"id": cid, "name": name, "expected": expected, "actual": actual,
                        "passed": passed, "order_id": order_id})
    ok = sum(r["passed"] for r in results)
    return {"bugs_enabled": bugs, "passed": ok, "total": len(results), "results": results,
            "ran_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}


def _mode(bugs):
    return "off" if str(bugs).lower() == "off" else "on"


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/run")
def api_run(bugs: str = "on"):
    mode = _mode(bugs)
    cached = _runs.get(mode)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return {**cached[1], "cached": True}
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="A run is already in progress. Try again in a few seconds.")
    try:
        result = run_checks(mode == "on")
        _runs[mode] = (time.time(), result)
        return {**result, "cached": False}
    except PayPalError as e:
        raise HTTPException(status_code=502, detail=f"PayPal sandbox error: {str(e)[:200]}")
    finally:
        _run_lock.release()


@app.post("/api/explain")
def api_explain(bugs: str = "on"):
    mode = _mode(bugs)
    run = _runs.get(mode)
    if not run:
        raise HTTPException(status_code=409, detail="Run the checks first.")
    failed = [r for r in run[1]["results"] if not r["passed"]]
    if not failed:
        return {"analysis": None}
    key = (mode, tuple(r["id"] for r in failed))
    if key in _explanations:  # same failures explained before: no new Gemini call
        return {"analysis": _explanations[key], "cached": True}
    source = (ROOT / "demo_store" / "app.py").read_text(encoding="utf-8")
    try:
        analysis = explain_failures(failed, source)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini error: {str(e)[:200]}")
    _explanations[key] = analysis
    return {"analysis": analysis, "cached": False}
