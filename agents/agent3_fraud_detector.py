# ============================================================
#  agents/agent3_fraud_detector.py  —  STUDENT 3 Agent
#  LangGraph node: Fraud Detector
# ============================================================

from langchain_ollama import OllamaLLM

import alert_system as alerts
from config import FRAUD_DB_PATH, OLLAMA_MODEL
from logger_config import logger
from state import LoanState
from tools.tool3_fraud_db_query import query_fraud_database
from tools.tool_web_browser import search_employer_web

SYSTEM_PROMPT = """You are a Fraud Risk Analyst at Ceylon National Bank.
Write a SHORT (3-4 sentence) fraud risk assessment for a loan application.
You will receive the fraud flags detected by our automated system.
Be professional. Explain the significance of each flag clearly.
Do NOT make a final loan decision — only assess the fraud risk."""


def agent3_detect_fraud(state: LoanState) -> LoanState:
    """
    LangGraph node: run comprehensive fraud detection.

    Queries the local SQLite fraud database (tool3) AND does a live
    employer web lookup (tool_web_browser). Sends critical fraud
    alerts to the UI when HIGH-severity flags are found.
    Sends inter-agent message to Agent 4 with combined risk summary.
    """
    app_id = state.get("application_id", "")
    app    = state.get("validated_application") or state.get("raw_application", {})

    logger.info("=" * 60)
    logger.info("AGENT 3 — Fraud Detector: starting")

    if app_id:
        alerts.agent_started(app_id, "Agent 3 — Fraud Detector",
                             "Querying fraud database and verifying employer online...")

    # ── Web tool: employer verification ───────────────────────
    employer_name    = app.get("employer_name", "Unknown")
    employer_check   = search_employer_web(employer_name)
    employer_web_txt = ""
    if employer_check.get("found"):
        employer_web_txt = f"Employer found online: {employer_check['abstract'][:120]}"
        logger.info(f"  Employer web check: FOUND — {employer_check['abstract'][:60]}")
    elif employer_check.get("error"):
        employer_web_txt = f"Web lookup failed: {employer_check['error']}"
        logger.warning(f"  Employer web check failed: {employer_check['error']}")
    else:
        employer_web_txt = f"No public record found for employer: '{employer_name}'"
        logger.info("  Employer web check: NOT FOUND in public records")

    if app_id:
        alerts.web_search_alert(app_id, "Agent 3 — Fraud Detector",
                                f"Employer: {employer_name}", employer_web_txt)

    # ── Tool3: fraud DB query ─────────────────────────────────
    try:
        fraud = query_fraud_database(app, db_path=FRAUD_DB_PATH)
        flags       = fraud["flags"]
        fraud_score = fraud["fraud_score"]
        risk_level  = fraud["risk_level"]
        nic_hit     = fraud["nic_hit"]
        name_hit    = fraud["name_hit"]
        net_hit     = fraud["network_hit"]
        logger.info(f"  Flags={fraud['flag_count']}  Score={fraud_score}  "
                    f"Level={risk_level}  NIC={nic_hit}  Name={name_hit}  Network={net_hit}")
        for f in flags:
            logger.warning(f"  FLAG [{f['severity']}]: {f['description'][:80]}")
    except FileNotFoundError as exc:
        logger.error(f"  Fraud DB missing: {exc}")
        if app_id:
            alerts.send_alert(app_id, {
                "type": "FRAUD_DB_ERROR", "agent": "Agent 3 — Fraud Detector",
                "title": "Fraud Database Unavailable",
                "message": str(exc), "severity": "high",
            })
        return {**state, "fraud_flags": [], "fraud_risk_score": 50.0,
                "fraud_risk_level": "MEDIUM",
                "fraud_summary": "Fraud database unavailable — manual review required.",
                "employer_web_check": employer_web_txt}

    # ── LLM narrative ─────────────────────────────────────────
    flags_text = "\n".join(
        f"  [{f['severity']}] {f['flag_type']}: {f['description']}" for f in flags
    ) or "  No fraud flags detected."
    prompt = (f"{SYSTEM_PROMPT}\n\nApplicant: {app.get('applicant_name','Unknown')}\n"
              f"NIC: {app.get('national_id','Not provided')}\n"
              f"Fraud flags ({len(flags)} found):\n{flags_text}\n"
              f"Employer web check: {employer_web_txt}\n"
              f"Fraud Score: {fraud_score}/100  Level: {risk_level}\n\n"
              f"Write your fraud risk assessment:")
    summary = _llm(prompt, _fallback_summary(flags, fraud_score, risk_level, app))

    # ── UI Alerts ─────────────────────────────────────────────
    if app_id:
        if risk_level == "HIGH" or nic_hit or name_hit or net_hit:
            suggs = []
            if nic_hit or name_hit:
                suggs.append("Do NOT proceed — applicant is on the fraud blacklist.")
                suggs.append("Escalate immediately to the Compliance & Legal department.")
                suggs.append("Preserve all documents provided by the applicant for investigation.")
            if net_hit:
                suggs.append("Alert the Financial Intelligence Unit (FIU) — fraud network involvement.")
                suggs.append("Do not disclose investigation to the applicant.")
            suggs.append("Hold all banking activity for this customer until further notice.")
            suggs.append("Notify branch manager and document the incident with timestamp.")

            alerts.fraud_alert(
                app_id,
                f"Possible fraud detected! "
                f"{'NIC matched blacklist. ' if nic_hit else ''}"
                f"{'Name matched blacklist. ' if name_hit else ''}"
                f"{'Linked to known fraud network! ' if net_hit else ''}"
                f"Fraud score: {fraud_score:.1f}/100. "
                f"{len(flags)} flag(s) found.",
                suggs
            )
        elif risk_level == "MEDIUM":
            alerts.send_alert(app_id, {
                "type": "FRAUD_MEDIUM", "agent": "Agent 3 — Fraud Detector",
                "title": "Elevated Fraud Risk — Verify Manually",
                "message": f"{len(flags)} suspicious indicator(s) found. Score: {fraud_score:.1f}/100.",
                "severity": "warning",
            })
        else:
            alerts.send_alert(app_id, {
                "type": "FRAUD_CLEAR", "agent": "Agent 3 — Fraud Detector",
                "title": "No Fraud Indicators Detected",
                "message": f"All fraud checks passed. Score: {fraud_score:.1f}/100.",
                "severity": "info",
            })

        # Inter-agent message to Agent 4
        prev_messages = state.get("agent_messages", [])
        fin_score = state.get("financial_risk_score", 0)
        msg = (f"Fraud score={fraud_score:.1f}/100 ({risk_level}). "
               f"Financial score={fin_score:.1f}/100. "
               f"NIC match={nic_hit}, Name match={name_hit}, Network={net_hit}. "
               f"Total flags={len(flags)}. Please generate final decision.")
        alerts.agent_message(app_id, "Agent 3 — Fraud Detector",
                             "Agent 4 — Decision Writer", msg)
        alerts.agent_completed(app_id, "Agent 3 — Fraud Detector",
                               f"Score={fraud_score:.1f}, Level={risk_level}, Flags={len(flags)}")

    logger.info(f"  summary: {summary[:80]}...")
    logger.info("AGENT 3 — complete")

    return {**state,
            "fraud_flags":        flags,
            "fraud_risk_score":   fraud_score,
            "fraud_risk_level":   risk_level,
            "fraud_summary":      summary,
            "employer_web_check": employer_web_txt,
            "agent_messages": state.get("agent_messages", []) + [{
                "from": "Agent3", "to": "Agent4",
                "message": f"Fraud score={fraud_score:.1f}  Level={risk_level}  Flags={len(flags)}"
            }]}


def _llm(prompt, fallback):
    try:
        return OllamaLLM(model=OLLAMA_MODEL).invoke(prompt).strip()
    except Exception as e:
        logger.warning(f"  LLM fallback: {e}")
        return fallback


def _fallback_summary(flags, score, level, app):
    name = app.get("applicant_name", "The applicant")
    if not flags:
        return (f"No fraud indicators detected for {name}. "
                f"All database checks returned clean results. "
                f"Fraud risk level: {level} (score: {score:.1f}/100).")
    high = [f for f in flags if f.get("severity") == "HIGH"]
    return (f"Fraud analysis detected {len(flags)} indicator(s) for {name}: "
            f"{len(high)} HIGH severity. "
            f"{'NIC or name matched the fraud blacklist. ' if high else ''}"
            f"Overall fraud risk: {level} (score: {score:.1f}/100). "
            "Immediate manual verification is required.")
