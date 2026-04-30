# ============================================================
#  agents/agent2_financial_analyzer.py  —  STUDENT 2 Agent
#  LangGraph node: Financial Risk Analyzer
# ============================================================

from langchain_ollama import OllamaLLM

import alert_system as alerts
from config import OLLAMA_MODEL
from logger_config import logger
from state import LoanState
from tools.tool2_financial_calc import run_financial_analysis
from tools.tool_web_browser import fetch_exchange_rates
import json

SYSTEM_PROMPT = """You are a Senior Credit Analyst at Ceylon National Bank.
Write a SHORT (3-4 sentence) financial risk narrative interpreting the computed
metrics. Focus on DTI ratio, LTV ratio, and overall affordability.
Do NOT make a final decision. Be factual and professional."""


def agent2_analyze_financials(state: LoanState) -> LoanState:
    """
    LangGraph node: compute financial risk and fetch live market rates.

    Uses tool2 for calculations and tool_web_browser for live LKR
    exchange rates. Sends a credit risk alert to the UI if DTI > 50%.
    Sends an inter-agent message to Agent 3.
    """
    app_id = state.get("application_id", "")
    app    = state.get("validated_application") or state.get("raw_application", {})

    logger.info("=" * 60)
    logger.info("AGENT 2 — Financial Analyzer: starting")

    logger.info(f"  Incoming State Payload: {json.dumps(app, indent=2)}")

    if app_id:
        alerts.agent_started(app_id, "Agent 2 — Financial Analyzer",
                             "Fetching live market rates and computing financial metrics...")

    # ── Web tool: fetch live exchange rates ───────────────────
    logger.info("  Fetching live exchange rates from web...")
    market_rates = fetch_exchange_rates("LKR")
    if market_rates.get("error"):
        logger.warning(f"  Exchange rate fetch failed: {market_rates['error']}")
    else:
        usd_rate = market_rates["rates"].get("USD", 0)
        logger.info(f"  Live rate: 1 LKR = {usd_rate:.6f} USD")
        if app_id:
            alerts.web_search_alert(
                app_id, "Agent 2 — Financial Analyzer",
                "LKR/USD exchange rate",
                f"1 LKR = {usd_rate:.6f} USD  (source: open.er-api.com)"
                if usd_rate else "Rate data unavailable — using offline fallback."
            )

    # ── Tool2: financial calculations ─────────────────────────
    try:
        metrics = run_financial_analysis(app, market_rates=market_rates)
        logger.info(f"  DTI={metrics['dti_percent']}%  LTV={metrics['ltv_percent']}%  "
                    f"Score={metrics['financial_risk_score']}  Tier={metrics['financial_risk_tier']}")
    except (KeyError, ValueError) as exc:
        logger.error(f"  Tool2 error: {exc}")
        fallback = {"monthly_income":0,"monthly_payment":0,"dti_ratio":0,"dti_percent":0,
                    "ltv_ratio":0,"ltv_percent":0,"dti_score":50,"ltv_score":50,
                    "affordability_score":50,"financial_risk_score":50,"financial_risk_tier":"MEDIUM"}
        return {**state, "financial_metrics": fallback,
                "financial_risk_score": 50.0, "financial_risk_tier": "MEDIUM",
                "financial_summary": f"Financial analysis error: {exc}",
                "market_rates": market_rates}

    # ── LLM narrative ─────────────────────────────────────────
    prompt = (f"{SYSTEM_PROMPT}\n\nApplicant: {app.get('applicant_name','Unknown')}\n"
              f"Loan: {app.get('loan_amount_requested',0):,.0f}  "
              f"Income: {app.get('annual_income',0):,.0f}\n"
              f"DTI: {metrics['dti_percent']:.1f}%  LTV: {metrics['ltv_percent']:.1f}%  "
              f"Score: {metrics['financial_risk_score']:.1f}/100  "
              f"Tier: {metrics['financial_risk_tier']}\n\nWrite your financial risk narrative:")
    summary = _llm(prompt, _fallback_summary(metrics, app))

    # ── UI Alerts ─────────────────────────────────────────────
    if app_id:
        # Credit risk alert if high
        if metrics["financial_risk_tier"] == "HIGH":
            suggs = [
                "Request additional collateral (vehicle, business assets) to reduce LTV.",
                "Consider a co-applicant or guarantor with higher income.",
                f"Reduce the loan amount to below {app.get('property_value',0)*0.75:,.0f} (75% LTV).",
                "Propose a shorter loan term to reduce total interest exposure.",
                "Verify all income sources — request 6 months bank statements.",
            ]
            alerts.credit_risk_alert(app_id,
                f"DTI ratio is {metrics['dti_percent']:.1f}% and LTV is {metrics['ltv_percent']:.1f}%. "
                f"Financial risk score: {metrics['financial_risk_score']:.1f}/100. "
                "This exceeds our standard lending thresholds.", suggs)
        else:
            alerts.send_alert(app_id, {
                "type": "FINANCIAL_RESULT", "agent": "Agent 2 — Financial Analyzer",
                "title": f"Financial Risk: {metrics['financial_risk_tier']}",
                "message": (f"DTI={metrics['dti_percent']:.1f}%  "
                            f"LTV={metrics['ltv_percent']:.1f}%  "
                            f"Score={metrics['financial_risk_score']:.1f}/100"),
                "severity": "warning" if metrics["financial_risk_tier"]=="MEDIUM" else "info",
            })

        # Inter-agent message to Agent 3
        msg = (f"Financial risk score: {metrics['financial_risk_score']:.1f}/100 "
               f"({metrics['financial_risk_tier']}). DTI={metrics['dti_percent']:.1f}%, "
               f"LTV={metrics['ltv_percent']:.1f}%. Please cross-check with fraud database.")
        alerts.agent_message(app_id, "Agent 2 — Financial Analyzer",
                             "Agent 3 — Fraud Detector", msg)
        alerts.agent_completed(app_id, "Agent 2 — Financial Analyzer",
                               f"Score={metrics['financial_risk_score']:.1f}, Tier={metrics['financial_risk_tier']}")

    logger.info(f"  summary: {summary[:80]}...")
    logger.info("AGENT 2 — complete")

    return {**state,
            "financial_metrics":    metrics,
            "financial_risk_score": metrics["financial_risk_score"],
            "financial_risk_tier":  metrics["financial_risk_tier"],
            "financial_summary":    summary,
            "market_rates":         market_rates,
            "agent_messages": state.get("agent_messages", []) + [{
                "from": "Agent2", "to": "Agent3",
                "message": f"Financial score={metrics['financial_risk_score']:.1f}  "
                           f"Tier={metrics['financial_risk_tier']}"
            }]}


def _llm(prompt, fallback):
    try:
        return OllamaLLM(model=OLLAMA_MODEL).invoke(prompt).strip()
    except Exception as e:
        logger.warning(f"  LLM fallback: {e}")
        return fallback


def _fallback_summary(m, app):
    name = app.get("applicant_name", "The applicant")
    dti  = m.get("dti_percent", 0)
    ltv  = m.get("ltv_percent", 0)
    s    = m.get("financial_risk_score", 0)
    t    = m.get("financial_risk_tier", "UNKNOWN")
    return (f"{name} presents a DTI of {dti:.1f}% and LTV of {ltv:.1f}%. "
            f"Financial risk score is {s:.1f}/100, placing this in the {t} tier.")
