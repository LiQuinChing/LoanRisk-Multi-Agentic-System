# ============================================================
#  tools/tool4_report_writer.py
#  STUDENT 4 — Individual Custom Tool
# ============================================================

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def write_html_report(report_data: Dict[str, Any],
                      output_dir: str = "data/reports") -> str:
    """
    Generate and save a professional HTML loan risk assessment report.

    Includes applicant summary, financial metrics, fraud flags,
    branch manager action items, LLM decision reasoning, and
    a colour-coded decision banner with actionable suggestions.

    Args:
        report_data: Dict containing all assessment results.
            Mandatory keys: ``application_id``, ``applicant_name``,
            ``final_decision``.
            Optional but used: ``financial_metrics``, ``fraud_flags``,
            ``decision_reasoning``, ``suggestions``,
            ``financial_risk_tier``, ``fraud_risk_level``.
        output_dir: Directory for the output HTML file.

    Returns:
        Absolute path string of the saved HTML file.

    Raises:
        KeyError:  If a mandatory key is missing from report_data.
        IOError:   If the file cannot be written.
        OSError:   If the output directory cannot be created.
    """
    for key in ("application_id", "applicant_name", "final_decision"):
        if key not in report_data:
            raise KeyError(f"report_data missing required key: '{key}'")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    app_id    = str(report_data["application_id"]).replace("/", "-")
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = Path(output_dir) / f"loan_report_{app_id}_{ts}.html"
    html      = _render(report_data, ts)
    file_path.write_text(html, encoding="utf-8")
    return str(file_path.resolve())


def _dc(decision: str) -> Dict[str, str]:
    m = {
        "APPROVE":       {"bg":"#d1fae5","border":"#059669","text":"#065f46","label":"APPROVED"},
        "MANUAL_REVIEW": {"bg":"#fef3c7","border":"#d97706","text":"#92400e","label":"MANUAL REVIEW"},
        "REJECT":        {"bg":"#fee2e2","border":"#dc2626","text":"#7f1d1d","label":"REJECTED"},
    }
    return m.get(decision, m["MANUAL_REVIEW"])


def _badge(tier: str) -> str:
    c = {"LOW":("#d1fae5","#065f46"),"MEDIUM":("#fef3c7","#92400e"),"HIGH":("#fee2e2","#7f1d1d")}
    bg, tx = c.get(tier.upper(), ("#f3f4f6","#374151"))
    return f'<span style="background:{bg};color:{tx};padding:2px 10px;border-radius:9999px;font-size:12px;font-weight:600">{tier}</span>'


def _flags_html(flags: List[Dict[str, Any]]) -> str:
    if not flags:
        return '<p style="color:#065f46;background:#d1fae5;padding:10px 14px;border-radius:6px;margin:0">No fraud flags detected.</p>'
    rows = ""
    for f in flags:
        sev = f.get("severity","MEDIUM")
        c   = "#7f1d1d" if sev=="HIGH" else "#92400e"
        rows += f'<li style="margin-bottom:8px;color:{c}"><strong>[{sev}]</strong> {f.get("description","")}</li>'
    return f'<ul style="margin:0;padding-left:18px">{rows}</ul>'


def _suggestions_html(suggestions: List[str]) -> str:
    if not suggestions:
        return ""
    items = "".join(f"<li style='margin-bottom:6px'>{s}</li>" for s in suggestions)
    return f"""
    <div style="background:#eff6ff;border-left:4px solid #3b82f6;border-radius:0 8px 8px 0;padding:14px 18px;margin-top:16px">
      <strong style="color:#1e40af;font-size:13px">BRANCH MANAGER — Suggested Actions</strong>
      <ul style="margin:10px 0 0;padding-left:18px;font-size:13px;color:#1e3a8a;line-height:1.7">{items}</ul>
    </div>"""


def _render(d: Dict[str, Any], ts: str) -> str:
    decision = str(d.get("final_decision","MANUAL_REVIEW"))
    dc       = _dc(decision)
    fin      = d.get("financial_metrics", {})
    flags    = d.get("fraud_flags", [])
    suggs    = d.get("suggestions", [])
    fin_tier = str(d.get("financial_risk_tier","UNKNOWN"))
    fr_level = str(d.get("fraud_risk_level","UNKNOWN"))
    reason   = d.get("decision_reasoning","No reasoning provided.")
    val_sum  = d.get("validation_summary","")
    usd_eq   = fin.get("usd_equivalent")

    usd_row = ""
    if usd_eq:
        usd_row = f"<tr><td>USD Equivalent (live rate)</td><td>USD {usd_eq:,.2f}</td></tr>"

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Loan Risk Report — {d.get('application_id','')}</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;background:#f0f4f8;color:#111827;margin:0;padding:24px}}
.wrap{{max-width:900px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;border:1px solid #e2e8f0}}
.hdr{{background:#1a3a6b;color:#fff;padding:22px 32px;display:flex;align-items:center;gap:16px}}
.hdr h1{{margin:0;font-size:20px;font-weight:600}}.hdr p{{margin:4px 0 0;font-size:12px;opacity:.7}}
.body{{padding:28px 32px}}
.banner{{padding:20px 24px;border-radius:10px;text-align:center;margin-bottom:24px;
         background:{dc['bg']};border:2px solid {dc['border']}}}
.banner h2{{margin:0;font-size:28px;color:{dc['text']};letter-spacing:.5px}}
.banner p{{margin:8px 0 0;font-size:13px;color:{dc['text']};opacity:.85}}
.sec{{margin-bottom:24px}}.sec h3{{font-size:12px;font-weight:600;color:#6b7280;
text-transform:uppercase;letter-spacing:.7px;border-bottom:1px solid #f3f4f6;
padding-bottom:7px;margin:0 0 12px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td{{padding:8px 12px;border-bottom:1px solid #f9fafb}}
td:first-child{{color:#6b7280;width:55%}}td:last-child{{font-weight:500}}
tr:last-child td{{border:none}}
.reason{{background:#f8fafc;border-left:3px solid #3b82f6;padding:14px 18px;
border-radius:0 8px 8px 0;font-size:13px;line-height:1.7;color:#374151}}
.ftr{{background:#f3f4f6;padding:12px 32px;font-size:11px;color:#9ca3af;
display:flex;justify-content:space-between}}
</style></head><body>
<div class="wrap">
<div class="hdr">
  <div>
    <h1>Ceylon National Bank — Loan Risk Report</h1>
    <p>Application: {d.get('application_id','')} &nbsp;|&nbsp; {datetime.now().strftime('%d %B %Y, %H:%M')}</p>
  </div>
</div>
<div class="body">

<div class="banner">
  <h2>{dc['label']}</h2>
  <p>Financial Risk: {_badge(fin_tier)} &nbsp;&nbsp; Fraud Risk: {_badge(fr_level)}</p>
</div>

<div class="sec"><h3>Applicant Summary</h3>
<table>
<tr><td>Applicant Name</td><td>{d.get('applicant_name','')}</td></tr>
<tr><td>National ID</td><td>{d.get('national_id','Not provided')}</td></tr>
<tr><td>Loan Requested</td><td>{float(d.get('loan_amount', d.get('loan_amount_requested',0))):,.0f}</td></tr>
<tr><td>Loan Purpose</td><td>{d.get('loan_purpose','')}</td></tr>
<tr><td>Term</td><td>{d.get('loan_term_months','')} months</td></tr>
<tr><td>Employment</td><td>{d.get('employment_status','')}</td></tr>
<tr><td>Annual Income</td><td>{float(d.get('annual_income',0)):,.0f}</td></tr>
<tr><td>Credit Score</td><td>{d.get('credit_score','')}</td></tr>
{usd_row}
</table></div>

<div class="sec"><h3>Financial Risk Analysis</h3>
<table>
<tr><td>Monthly Income</td><td>{fin.get('monthly_income',0):,.0f}</td></tr>
<tr><td>Estimated Monthly Payment</td><td>{fin.get('monthly_payment',0):,.0f}</td></tr>
<tr><td>Debt-to-Income Ratio (DTI)</td><td>{fin.get('dti_percent',0):.1f}%</td></tr>
<tr><td>Loan-to-Value Ratio (LTV)</td><td>{fin.get('ltv_percent',0):.1f}%</td></tr>
<tr><td>Financial Risk Score</td><td>{fin.get('financial_risk_score',0):.1f} / 100</td></tr>
<tr><td>Financial Risk Tier</td><td>{_badge(fin_tier)}</td></tr>
</table>
{(f'<p style="font-size:12px;color:#6b7280;margin:8px 0 0">{val_sum}</p>') if val_sum else ''}
</div>

<div class="sec"><h3>Fraud Detection ({len(flags)} flag{'s' if len(flags)!=1 else ''} found)</h3>
{_flags_html(flags)}
</div>

<div class="sec"><h3>Decision Reasoning</h3>
<div class="reason">{reason}</div>
{_suggestions_html(suggs)}
</div>

</div>
<div class="ftr">
  <span>Ceylon National Bank — Internal Loan Assessment System</span>
  <span>CONFIDENTIAL — For authorised staff only</span>
</div>
</div></body></html>"""
