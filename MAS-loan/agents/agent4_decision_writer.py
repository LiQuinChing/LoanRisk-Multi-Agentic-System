# ============================================================
#  agents/agent4_decision_writer.py  —  STUDENT 4 Agent
#  LangGraph node: Decision Writer
# ============================================================

from langchain_ollama import OllamaLLM

import alert_system as alerts
from config import OLLAMA_MODEL, REJECT_THRESHOLD, REPORTS_DIR, REVIEW_THRESHOLD
from logger_config import logger
from state import LoanState
from tools.tool4_report_writer import write_html_report

SYSTEM_PROMPT = """You are the Chief Credit Officer at Ceylon National Bank.
Write a formal, professional 3-4 sentence decision rationale for a loan application.
You will be given the financial risk score, fraud risk score, and the final decision.
Explain clearly why this decision was reached. Reference specific risk factors.
Be formal, factual, and empathetic. Do not start with the decision label."""


def agent4_write_decision(state: LoanState) -> LoanState:
    """
    LangGraph node: synthesise all risk scores into a final decision.

    Applies deterministic threshold rules, generates suggestions for
    the branch manager, writes the HTML report via tool4, and sends
    the final decision alert (+ pipeline complete signal) to the UI.
    """
    app_id      = state.get("application_id", "")
    fin_score   = float(state.get("financial_risk_score", 50))
    fraud_score = float(state.get("fraud_risk_score", 0))
    proceed     = state.get("proceed_to_analysis", True)
    app         = state.get("validated_application") or state.get("raw_application", {})

    logger.info("=" * 60)
    logger.info("AGENT 4 — Decision Writer: starting")

    if app_id:
        alerts.agent_started(app_id, "Agent 4 — Decision Writer",
                             "Synthesising all risk scores and generating final decision...")

    # ── Deterministic decision rules ──────────────────────────
    fraud_flags = state.get("fraud_flags", [])
    nic_hit  = any(f["flag_type"] == "blacklisted_national_id"   for f in fraud_flags)
    name_hit = any(f["flag_type"] == "blacklisted_name"           for f in fraud_flags)
    net_hit  = any(f["flag_type"] == "fraud_network_member"        for f in fraud_flags)

    if not proceed or nic_hit or name_hit or net_hit:
        decision = "REJECT"
        logger.info("  Decision: REJECT (blacklist hit or validation failure)")
    elif fraud_score >= REJECT_THRESHOLD or fin_score >= REJECT_THRESHOLD:
        decision = "REJECT"
    elif fraud_score >= REVIEW_THRESHOLD or fin_score >= REVIEW_THRESHOLD:
        decision = "MANUAL_REVIEW"
    else:
        decision = "APPROVE"

    logger.info(f"  fin={fin_score}  fraud={fraud_score}  → {decision}")

    # ── Build context-aware suggestions ───────────────────────
    suggestions = _build_suggestions(decision, fin_score, fraud_score,
                                     state, nic_hit, name_hit, net_hit)

    # ── LLM reasoning ─────────────────────────────────────────
    prompt = (f"{SYSTEM_PROMPT}\n\nApplicant: {app.get('applicant_name','Unknown')}\n"
              f"Loan: {app.get('loan_amount_requested',0):,.0f}\n"
              f"Financial Risk Score: {fin_score:.1f}/100 ({state.get('financial_risk_tier','')})\n"
              f"Fraud Risk Score: {fraud_score:.1f}/100 ({state.get('fraud_risk_level','')})\n"
              f"Fraud Flags: {len(fraud_flags)}\n"
              f"Blacklist Hits: NIC={nic_hit}, Name={name_hit}, Network={net_hit}\n"
              f"Final Decision: {decision}\n\nWrite your 3-4 sentence rationale:")
    reasoning = _llm(prompt, _fallback_reasoning(decision, fin_score, fraud_score, app))

    # ── Write HTML report (tool4) ─────────────────────────────
    report_data = {
        **app,
        "loan_amount":          app.get("loan_amount_requested", 0),
        "financial_metrics":    state.get("financial_metrics", {}),
        "financial_risk_tier":  state.get("financial_risk_tier", "UNKNOWN"),
        "fraud_flags":          fraud_flags,
        "fraud_risk_level":     state.get("fraud_risk_level", "UNKNOWN"),
        "final_decision":       decision,
        "decision_reasoning":   reasoning,
        "validation_summary":   state.get("validation_summary", ""),
        "suggestions":          suggestions,
    }
    try:
        report_path = write_html_report(report_data, output_dir=REPORTS_DIR)
        logger.info(f"  Report saved: {report_path}")
    except Exception as exc:
        logger.error(f"  Report write failed: {exc}")
        report_path = ""

    # ── UI Alerts ─────────────────────────────────────────────
    if app_id:
        alerts.decision_alert(app_id, decision, reasoning, suggestions)
        alerts.agent_completed(app_id, "Agent 4 — Decision Writer",
                               f"Decision: {decision}. Report saved.")
        alerts.pipeline_complete(app_id, report_path)

    logger.info("AGENT 4 — complete")

    return {**state,
            "final_decision":    decision,
            "decision_reasoning": reasoning,
            "suggestions":        suggestions,
            "report_path":        report_path}


def _build_suggestions(decision, fin_score, fraud_score, state,
                        nic_hit, name_hit, net_hit):
    suggs = []
    if decision == "APPROVE":
        suggs.append("Proceed with standard loan documentation and sign-off.")
        suggs.append("Conduct final KYC verification before disbursement.")
        if state.get("financial_risk_tier") == "MEDIUM":
            suggs.append("Set up quarterly repayment monitoring for this account.")
    elif decision == "MANUAL_REVIEW":
        if fin_score >= REVIEW_THRESHOLD:
            suggs.append("Request 6 months of bank statements to verify income.")
            suggs.append("Consider a co-applicant or guarantor with stronger financials.")
            suggs.append(
                f"Reduce loan amount to {float(state.get('validated_application',{}).get('property_value',0))*0.75:,.0f} "
                "(75% LTV) to improve the risk profile."
            )
            suggs.append("Collateral options: vehicle logbook, fixed deposit, or business assets.")
        if fraud_score >= REVIEW_THRESHOLD:
            suggs.append("Conduct in-person identity verification with original NIC.")
            suggs.append("Contact employer HR directly to verify employment details.")
        suggs.append("Escalate to Senior Credit Committee for final sign-off.")
    else:  # REJECT
        if nic_hit or name_hit:
            suggs.append("IMMEDIATE: Alert Compliance & Legal — blacklist match confirmed.")
            suggs.append("Do NOT disclose the reason for rejection to the applicant.")
            suggs.append("Preserve all submitted documents for law enforcement.")
        if net_hit:
            suggs.append("URGENT: Notify the Financial Intelligence Unit (FIU).")
        if not (nic_hit or name_hit or net_hit):
            suggs.append("Inform the applicant of the rejection in writing.")
            suggs.append("Suggest the applicant improves credit score and reduces existing debt before reapplying.")
            suggs.append("The applicant may reapply after 6 months with improved financials.")
    return suggs


def _llm(prompt, fallback):
    try:
        return OllamaLLM(model=OLLAMA_MODEL).invoke(prompt).strip()
    except Exception as e:
        logger.warning(f"  LLM fallback: {e}")
        return fallback


def _fallback_reasoning(decision, fin, fraud, app):
    name   = app.get("applicant_name", "The applicant")
    amount = app.get("loan_amount_requested", 0)
    if decision == "APPROVE":
        return (f"{name}'s application for {amount:,.0f} has been approved. "
                f"The financial risk score of {fin:.1f}/100 and fraud risk score of "
                f"{fraud:.1f}/100 both fall within acceptable thresholds. "
                "The applicant demonstrates adequate repayment capacity.")
    if decision == "MANUAL_REVIEW":
        return (f"{name}'s application for {amount:,.0f} requires manual review. "
                f"The financial risk score ({fin:.1f}/100) or fraud score ({fraud:.1f}/100) "
                "exceeds the automatic approval threshold. A senior officer should review.")
    return (f"{name}'s application for {amount:,.0f} has been declined. "
            f"The financial risk score ({fin:.1f}/100) and/or fraud risk score "
            f"({fraud:.1f}/100) exceed the bank's maximum risk tolerance. "
            "The applicant may reapply after addressing the identified risk factors.")
