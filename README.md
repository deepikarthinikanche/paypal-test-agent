# PayPal Test Agent
An AI agent that tests a store's PayPal integration, catches real bugs by checking what PayPal actually received, and explains each failure in plain English with a suggested fix.

Built for the PayPal AI Hackathon. Uses the PayPal Sandbox (no real money) and Google Gemini.

**Demo video:** _(link added at submission)_

## The problem

Payment bugs are expensive and easy to miss. A checkout page can look fine while charging the wrong amount, or crash on bad input and leak provider errors to customers. Testing this by hand against PayPal is slow, and reading PayPal error responses is confusing.

## What it does

1. **Tests the store.** It sends checkout requests to a demo store, then asks PayPal directly what order was created and compares the amount to what the customer asked to pay. It also checks that bad input (zero or negative amounts) is rejected cleanly.
2. **Explains the failures.** Failed checks and the store's source code go to Gemini, which returns the cause and a suggested fix in plain English, with a corrected code snippet.
3. **Shows the result.** A dashboard page shows the score, the AI explanations and every check.

The demo store ships with two planted bugs (switchable on and off) so you can watch the agent find them:

| Bug | What the customer sees | Root cause |
|---|---|---|
| Wrong amount | 19.99 USD is charged as 19.98 USD (1.15 becomes 1.14) | Float math truncates cents |
| Crash on bad input | HTTP 500 with a leaked provider error | No input validation |

With bugs ON, 2 of 6 checks pass. With bugs OFF (fixed), 6 of 6 pass.

## How it uses PayPal and AI

**PayPal Sandbox REST APIs**
- OAuth 2.0 access tokens
- Orders v2: create, get and capture an order
- Payments v2: refund a capture

**Gemini (google-genai SDK)**
- Reads the failed checks and the store's source code
- Returns structured JSON: summary, severity, cause, fix and code snippet per finding

## How it works

```
run_store_tests.py ──request──▶ Demo store (FastAPI /checkout) ──create order──▶ PayPal Sandbox
        │                                                                          │
        └────────────── fetch the order and compare the amount ◀───────────────────┘
        │
        ▼
results/store_latest.json ──▶ Gemini analyzer ──▶ results/analysis.json ──▶ results/dashboard.html
```

## Quick start

### Prerequisites
- Python 3.10 or newer
- A free PayPal developer account at https://developer.paypal.com
- A Gemini API key from https://aistudio.google.com/apikey (the free tier is enough)

### 1. PayPal sandbox setup
1. In the developer dashboard, go to **Testing Tools, Sandbox Accounts** and create a **Business** account and a **Personal** account, both with country **United States**.
2. Go to **Apps and Credentials**, make sure **Sandbox** is selected, and create an app of type **Merchant** linked to the US business account.
3. Copy the app's **Client ID** and **Secret**.

> Use sandbox credentials only. During development, sandbox accounts set to India gave a generic checkout error, while US accounts worked.

### 2. Install
```bash
git clone https://github.com/deepikarthinikanche/paypal-test-agent.git
cd paypal-test-agent
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### 3. Configure
Copy `.env.example` to `.env` and fill it in:
```
PAYPAL_CLIENT_ID=your sandbox client id
PAYPAL_SECRET=your sandbox secret
GEMINI_API_KEY=your gemini api key
```
`.env` is git-ignored. Never commit it.

### 4. Run the demo (two terminals)

**Terminal 1: start the demo store with the bugs ON**
```powershell
$env:DEMO_BUGS="on"                      # PowerShell
uvicorn demo_store.app:app --port 8000
```
On macOS or Linux: `DEMO_BUGS=on uvicorn demo_store.app:app --port 8000`

**Terminal 2: run the whole pipeline**
```bash
python run_demo.py
```
It tests the store, asks Gemini to explain the failures, builds `results/dashboard.html` and opens it in your browser.

### 5. See the fixed version
Stop the store with Ctrl+C, restart it with bugs OFF, and run the demo again. All 6 checks pass.
```powershell
$env:DEMO_BUGS="off"
uvicorn demo_store.app:app --port 8000
```

## Other scripts

| Script | Purpose |
|---|---|
| `first_call.py` | Checks your PayPal credentials: gets a token and creates an order |
| `payment_flow.py` | Full sandbox flow: create, buyer approves, capture, partial refund |
| `run_scenarios.py` | 11 API-level scenarios (invalid currency, missing fields, bad token and more) |
| `run_store_tests.py` | Tests the demo store's checkout |
| `run_analyzer.py` | Sends failures to Gemini and writes `results/report.md` |
| `build_dashboard.py` | Builds `results/dashboard.html` |

## Project structure

```
agent/              PayPal client, scenarios, Gemini analyzer
demo_store/         FastAPI store with switchable bugs
results/            generated results, report and dashboard
run_demo.py         one-command demo
```

## Notes

- Only the PayPal Sandbox is used. No real payments are made.
- Each store test creates a few sandbox orders. They are never captured.
- Gemini free-tier limits can change. If the analyzer reports a quota or model-name error, set `GEMINI_MODEL` in `.env` to a current model name.

## License

MIT. See [LICENSE](LICENSE).