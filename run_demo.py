"""One command for the whole demo: test the store, explain failures with Gemini,
build the dashboard, and open it in your browser.

1. Start the store in another terminal:  uvicorn demo_store.app:app --port 8000
2. Run:                                  python run_demo.py
"""
import os
import webbrowser

import httpx

import build_dashboard
import run_analyzer
import run_store_tests


def store_is_up():
    try:
        httpx.get(f"{run_store_tests.STORE_URL}/health", timeout=5)
        return True
    except httpx.HTTPError:
        return False


def main():
    if not store_is_up():
        print(f"Cannot reach the store at {run_store_tests.STORE_URL}.")
        print("Start it in another terminal first:")
        print("  uvicorn demo_store.app:app --port 8000")
        return

    print("=== Step 1 of 3: testing the store ===")
    run_store_tests.main()
    print("\n=== Step 2 of 3: AI analysis (Gemini) ===")
    run_analyzer.main()
    print("\n=== Step 3 of 3: building the dashboard ===")
    build_dashboard.main()

    path = os.path.abspath("results/dashboard.html")
    if os.path.exists(path):
        webbrowser.open("file:///" + path.replace("\\", "/"))
        print("\nOpened the dashboard in your browser.")


if __name__ == "__main__":
    main()