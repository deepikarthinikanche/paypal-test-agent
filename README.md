# PayAudit AI

PayAudit AI is an AI agent that audits a store's PayPal integration. It catches real bugs by checking what PayPal actually received, and explains each failure in plain English with a suggested fix.

Built for the PayPal AI Hackathon. Uses the PayPal Sandbox (no real money) and Google Gemini.

**Live demo:** https://payaudit-ai.onrender.com (no setup needed: open it and click **Run checks**)  
**Demo video:** [Watch the PayAudit AI demo on YouTube](https://youtu.be/2197nXnNKew)  
**Source code:** https://github.com/deepikarthinikanche/paypal-test-agent

> The live demo runs on a free Render plan, so the first load can take up to a minute while the server wakes up.

## Built with

- Python and FastAPI (demo store and live app)
- PayPal Sandbox REST APIs (OAuth 2.0, Orders v2, Payments v2)
- Google Gemini via the google-genai SDK (failure explanations)
- AG Grid Community (results table on the live page)
- Render (hosting)
- GitHub (source code, MIT license)

## The problem

Payment bugs are expensive and easy to miss. A checkout page can look fine while charging the wrong amount, or crash on bad input and leak provider errors to customers. Testing this by hand against PayPal is slow, and reading PayPal error responses is confusing.

## What it does

1. **Tests the store.** It sends checkout requests to a demo store, then asks PayPal directly what order was created and compares the amount to what the customer asked to pay. It also checks that bad input (zero or negative amounts) is rejected cleanly.
2. **Explains the failures.** Failed checks and the store's source code go to Gemini, which returns the cause and a suggested fix in plain English, with a corrected code snippet.
3. **Shows the result.** The live page (and a local dashboard) shows the score, every check, and the AI explanations.

The demo store ships with two planted bugs (switchable on and off) so you can watch the agent find them:

| Bug | What the customer sees | Root cause |
|---|---|---|
| Wrong amount | 19.99 USD is charged as 19.98 USD (1.15 becomes 1.14) | Float math truncates cents |
| Crash on bad input | HTTP 500 with PayPal's raw error text in the response | No input validation or error handling |

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
run_store_tests.py --request--> Demo store (FastAPI /checkout) --create order--> PayPal Sandbox
        |                                                                          |
        +------------- fetch the order and compare the amount <--------------------+
        |
        v
results/store_latest.json --> Gemini analyzer --> results/analysis.json --> results/dashboard.html
```

The live page (`web_app.py` and `static/index.html`) runs the same checks in-process and shows them in an AG Grid table.

## Live demo page

Open https://payaudit-ai.onrender.com, choose **Store bugs: on** or **off (fixed)**, and press **Run checks**. You get the score, a table of all six checks with the PayPal order IDs, and Gemini's explanation of every failure.

To run the live page on your own computer:
```bash
uvicorn web_app:app --port 8080
```
Then open http://127.0.0.1:8080. Repeat clicks within a minute reuse the last result, runs are limited to one at a time, and Gemini explanations are cached, so the page cannot be used to burn through quotas.

## Quick start (run it yourself)

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

### 4. Run the command-line demo (two terminals)

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

## Deploy to Render

1. Push this repo to GitHub (it includes `render.yaml`).
2. In Render, choose **New, Blueprint**, select the repo, and apply it.
3. When prompted, enter `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET` (sandbox values) and `GEMINI_API_KEY`. They are stored in Render, never in the repo.
4. Open the `onrender.com` URL once the deploy finishes. On the free plan the service sleeps when idle, so the first load can take up to a minute.

## Other scripts

| Script | Purpose |
|---|---|
| `first_call.py` | Checks your PayPal credentials: gets a token and creates an order |
| `payment_flow.py` | Full sandbox flow: create, buyer approves, capture, partial refund |
| `run_scenarios.py` | 11 API-level scenarios (invalid currency, missing fields, bad token and more) |
| `run_store_tests.py` | Tests the demo store's checkout over HTTP |
| `run_analyzer.py` | Sends failures to Gemini and writes `results/report.md` |
| `build_dashboard.py` | Builds `results/dashboard.html` |

## Project structure

```
agent/              PayPal client, API scenarios, Gemini analyzer
demo_store/         FastAPI store with switchable bugs
static/             live page (index.html, uses AG Grid)
web_app.py          live demo server
run_demo.py         one-command demo
render.yaml         Render deployment config
results/            generated results, report and dashboard (not committed)
```

## Notes

- Only the PayPal Sandbox is used. No real payments are made.
- Each store test creates a few sandbox orders. They are never captured.
- The demo store's bugs are planted on purpose. Gemini is shown the store's source code along with the failures, so it explains the cause from the results and the code.
- Gemini free-tier limits can change. If the analyzer reports a quota or model-name error, set `GEMINI_MODEL` in `.env` to a current model name.

## License

MIT. See [LICENSE](LICENSE).