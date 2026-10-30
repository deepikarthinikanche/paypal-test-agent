"""Build results/dashboard.html from the latest test results and the AI analysis.

Run after:  python run_store_tests.py   and   python run_analyzer.py
Then open:  results/dashboard.html   (double-click it, no server needed)
"""
import html
import json
import os

RESULTS = "results/store_latest.json"
ANALYSIS = "results/analysis.json"
OUT = "results/dashboard.html"


def esc(value):
    return html.escape("" if value is None else str(value))


def check_rows(results):
    rows = []
    for r in results:
        cls = "pass" if r["passed"] else "fail"
        label = "PASS" if r["passed"] else "FAIL"
        rows.append(
            f'<tr><td><span class="badge {cls}">{label}</span></td>'
            f'<td>{esc(r["name"])}</td><td>{esc(r.get("expected"))}</td>'
            f'<td>{esc(r.get("actual"))}</td></tr>'
        )
    return "\n".join(rows)


def finding_cards(analysis, all_ok=False):
    if not analysis and all_ok:
        return '<p class="muted">All checks passed, so there is nothing to analyze.</p>'
    if not analysis:
        return (
            '<p class="muted">No AI analysis yet. Run <code>python run_analyzer.py</code>, '
            "then rebuild this page.</p>"
        )
    cards = []
    for i, f in enumerate(analysis.get("findings", []), 1):
        sev = str(f.get("severity", "low")).lower()
        sev_cls = sev if sev in ("high", "medium", "low") else "low"
        code = f.get("code_fix")
        code_html = f"<pre><code>{esc(code.strip())}</code></pre>" if code else ""
        cards.append(
            f"""<article class="card">
  <div class="card-head"><h3>{i}. {esc(f.get("title"))}</h3>
  <span class="badge {sev_cls}">{esc(sev)}</span></div>
  <p class="ids">Failed checks: {esc(", ".join(f.get("check_ids", [])))}</p>
  <h4>What happened</h4><p>{esc(f.get("what_happened"))}</p>
  <h4>Likely cause</h4><p>{esc(f.get("likely_cause"))}</p>
  <h4>Suggested fix</h4><p>{esc(f.get("suggested_fix"))}</p>
  {code_html}
</article>"""
        )
    return "\n".join(cards)


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PayPal Test Agent: Results</title>
<style>
:root { --bg:#f7f8fa; --panel:#fff; --text:#16202a; --muted:#5b6b7a; --line:#dfe4ea;
  --good:#1a7f4b; --good-bg:#e3f4ea; --bad:#b3261e; --bad-bg:#fbe7e5;
  --warn:#8a5a00; --warn-bg:#fdf1d8; --accent:#0b57d0; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#12171d; --panel:#1b222a; --text:#e8edf2; --muted:#9aa8b5; --line:#2b3540;
    --good:#6fd29b; --good-bg:#17382a; --bad:#ff8a80; --bad-bg:#3d1f1d;
    --warn:#f2c46b; --warn-bg:#3a2e12; --accent:#8ab4f8; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text);
  font:15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width:920px; margin:0 auto; padding:32px 20px 64px; }
h1 { margin:0 0 4px; font-size:26px; }
h2 { margin:36px 0 12px; font-size:19px; }
h3 { margin:0; font-size:16px; } h4 { margin:14px 0 2px; font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.04em; }
p { margin:4px 0; } .muted, .ids { color:var(--muted); font-size:13px; }
.score { display:flex; gap:16px; align-items:center; background:var(--panel);
  border:1px solid var(--line); border-radius:12px; padding:20px; margin-top:20px; flex-wrap:wrap; }
.big { font-size:40px; font-weight:700; line-height:1; }
.big.ok { color:var(--good); } .big.bad { color:var(--bad); }
.badge { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }
.badge.pass, .badge.low { background:var(--good-bg); color:var(--good); }
.badge.fail, .badge.high { background:var(--bad-bg); color:var(--bad); }
.badge.medium { background:var(--warn-bg); color:var(--warn); }
.summary { background:var(--panel); border-left:4px solid var(--accent); padding:14px 16px; border-radius:8px; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px; margin:14px 0; }
.card-head { display:flex; justify-content:space-between; gap:12px; align-items:center; }
pre { background:var(--bg); border:1px solid var(--line); border-radius:8px; padding:12px; overflow-x:auto; font-size:13px; }
.table-wrap { overflow-x:auto; background:var(--panel); border:1px solid var(--line); border-radius:12px; }
table { width:100%; border-collapse:collapse; min-width:560px; }
th, td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); vertical-align:top; font-size:14px; }
th { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
tr:last-child td { border-bottom:0; }
code { font-family: ui-monospace, Consolas, monospace; }
</style></head>
<body><main>
<h1>PayPal Test Agent</h1>
<p class="muted">Run at %%RUN_AT%% &middot; store bugs %%BUGS%%</p>

<section class="score">
  <div class="big %%SCORE_CLASS%%">%%PASSED%% / %%TOTAL%%</div>
  <div><strong>checks passed</strong><br><span class="muted">Each check calls the demo store, then asks PayPal what it actually received.</span></div>
</section>

<h2>AI analysis</h2>
%%SUMMARY%%
%%FINDINGS%%

<h2>All checks</h2>
<div class="table-wrap"><table>
<thead><tr><th>Result</th><th>Check</th><th>Expected</th><th>Actual</th></tr></thead>
<tbody>
%%ROWS%%
</tbody></table></div>
</main></body></html>
"""


def main():
    if not os.path.exists(RESULTS):
        print(f"{RESULTS} not found. Run python run_store_tests.py first.")
        return
    with open(RESULTS, encoding="utf-8") as f:
        run = json.load(f)

    analysis = None
    if os.path.exists(ANALYSIS):
        with open(ANALYSIS, encoding="utf-8") as f:
            analysis = json.load(f)

    if analysis and analysis.get("analyzed_run_at") != run.get("run_at"):
        analysis = None  # stale: it explains an older test run

    summary = ""
    if analysis and analysis.get("summary"):
        summary = f'<p class="summary">{esc(analysis["summary"])}</p>'

    all_ok = run["passed"] == run["total"]
    page = (
        TEMPLATE.replace("%%RUN_AT%%", esc(run.get("run_at", "unknown")))
        .replace("%%BUGS%%", "ON" if run.get("bugs_enabled") else "OFF (fixed)")
        .replace("%%SCORE_CLASS%%", "ok" if all_ok else "bad")
        .replace("%%PASSED%%", esc(run["passed"]))
        .replace("%%TOTAL%%", esc(run["total"]))
        .replace("%%SUMMARY%%", summary)
        .replace("%%FINDINGS%%", finding_cards(analysis, all_ok))
        .replace("%%ROWS%%", check_rows(run["results"]))
    )
    os.makedirs("results", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Saved {OUT}. Open it in your browser.")


if __name__ == "__main__":
    main()