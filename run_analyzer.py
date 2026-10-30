"""Read the latest store test results and ask Gemini to explain the failures.

Run after:  python run_store_tests.py   (with the store's bugs ON)
Then:       python run_analyzer.py
"""
import json
import os

from agent.analyzer import explain_failures, render_markdown

RESULTS = "results/store_latest.json"
SOURCE = "demo_store/app.py"


def main():
    if not os.path.exists(RESULTS):
        print(f"{RESULTS} not found. Run python run_store_tests.py first.")
        return
    with open(RESULTS, encoding="utf-8") as f:
        run = json.load(f)

    failed = [r for r in run["results"] if not r["passed"]]
    if not failed:
        print(f"All {run['total']} checks passed, so there is nothing to analyze.")
        print("To see the analyzer work, restart the store with bugs ON and rerun the tests.")
        return

    with open(SOURCE, encoding="utf-8") as f:
        source = f.read()

    print(f"{len(failed)} failed checks. Asking Gemini to explain them...")
    try:
        analysis = explain_failures(failed, source)
    except Exception as e:
        print("Analysis failed:", e)
        return

    os.makedirs("results", exist_ok=True)
    with open("results/analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    with open("results/report.md", "w", encoding="utf-8") as f:
        f.write(render_markdown(analysis, run))

    print("\n" + analysis.get("summary", "") + "\n")
    for i, finding in enumerate(analysis["findings"], 1):
        print(f"{i}. [{finding.get('severity', '?')}] {finding.get('title')}")
        print("   Fix:", finding.get("suggested_fix"))
    print("\nSaved results/analysis.json and results/report.md")


if __name__ == "__main__":
    main()
