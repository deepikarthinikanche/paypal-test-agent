"""Run every scenario against the PayPal Sandbox and save the results."""
import json
import os
from datetime import datetime, timezone

from agent.paypal_client import PayPalClient
from agent.scenarios import build_scenarios


def error_summary(body):
    """Pull the useful bits out of a PayPal error response."""
    if not isinstance(body, dict):
        return {"raw": str(body)[:200]}
    issues = [
        d.get("issue") for d in body.get("details", []) if isinstance(d, dict)
    ]
    return {
        "error_name": body.get("name") or body.get("error"),
        "message": body.get("message") or body.get("error_description"),
        "issues": issues,
    }


def main():
    client = PayPalClient()
    results = []

    for s in build_scenarios():
        try:
            status, body = s.run(client)
            error = None
        except Exception as e:  # network problems, bad JSON, etc.
            status, body, error = None, None, str(e)

        passed = status in s.expected
        results.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "expected_status": list(s.expected),
            "actual_status": status,
            "passed": passed,
            "paypal_response": error_summary(body) if status and status >= 400 else {},
            "exception": error,
        })
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {s.name}  (expected {s.expected}, got {status})")

    total = len(results)
    ok = sum(r["passed"] for r in results)
    print(f"\n{ok}/{total} scenarios behaved as expected")

    os.makedirs("results", exist_ok=True)
    out = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "passed": ok,
        "total": total,
        "results": results,
    }
    with open("results/latest.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Saved results/latest.json")


if __name__ == "__main__":
    main()
