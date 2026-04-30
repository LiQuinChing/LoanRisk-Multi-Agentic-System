# ============================================================
#  agents/agent1_validator.py  —  STUDENT 1 Agent
#  LangGraph node: Application Validator
# ============================================================

from langchain_ollama import OllamaLLM

import alert_system as alerts
from config import OLLAMA_MODEL
from logger_config import logger
from state import LoanState
from tools.tool1_db_reader import read_and_validate_application

SYSTEM_PROMPT = """You are a Loan Application Data Quality Officer at Ceylon National Bank.
Your ONLY task is to write a SHORT (2-3 sentence) plain-English summary of the
validation results for a loan application. Be factual and professional.
If there are no errors, confirm the data is complete and well-formed.
Do NOT make any credit decision. Do NOT invent information."""


def agent1_validate(state: LoanState) -> LoanState:
    """
    LangGraph node: validate the loan application data.

    Reads from SQLite DB (web mode) or JSON file (CLI mode),
    validates all fields, pushes real-time alerts to the UI,
    and sends an inter-agent message to Agent 2.
    """
    app_id = state.get("application_id", "")
    mode   = state.get("mode", "cli")

    logger.info("=" * 60)
    logger.info("AGENT 1 — Application Validator: starting")

    if app_id:
        alerts.agent_started(app_id, "Agent 1 — Validator",
                             "Reading application from database and validating fields...")

    # ── Call tool1 ─────────────────────────────────────────────
    try:
        if mode == "web" and app_id:
            result = read_and_validate_application(application_id=app_id)
        else:
            result = read_and_validate_application(file_path=state.get("application_path",""))
    except Exception as exc:
        logger.error(f"  Agent1 tool error: {exc}")
        if app_id:
            alerts.send_alert(app_id, {
                "type": "VALIDATION_FAIL", "agent": "Agent 1 — Validator",
                "title": "Application Read Failed",
                "message": str(exc), "severity": "error",
            })
        return {**state,
                "raw_application": {}, "validated_application": {},
                "validation_errors": [{"field":"file","issue":str(exc),"severity":"CRITICAL"}],
                "validation_summary": f"Fatal error: {exc}",
                "proceed_to_analysis": False}

    data   = result["data"]
    errors = result["errors"]
    valid  = result["is_valid"]

    logger.info(f"  is_valid={valid}  errors={result['error_count']}")

    # ── LLM summary ───────────────────────────────────────────
    err_text = "\n".join(f"  [{e['severity']}] {e['field']}: {e['issue']}" for e in errors) or "NONE"
    prompt = (f"{SYSTEM_PROMPT}\n\nApplicant: {data.get('applicant_name','Unknown')}\n"
              f"Validation errors:\n{err_text}\n\nWrite your 2-3 sentence summary:")
    summary = _llm(prompt, _fallback_summary(errors, data))

    # ── UI Alerts ─────────────────────────────────────────────
    if app_id:
        if valid:
            alerts.send_alert(app_id, {
                "type": "VALIDATION_OK", "agent": "Agent 1 — Validator",
                "title": "Validation Passed",
                "message": summary, "severity": "info",
            })
        else:
            critical = [e for e in errors if e["severity"] == "CRITICAL"]
            alerts.send_alert(app_id, {
                "type": "VALIDATION_FAIL", "agent": "Agent 1 — Validator",
                "title": f"Validation Failed — {len(critical)} Critical Error(s)",
                "message": summary, "severity": "error",
            })

        # Inter-agent message to Agent 2
        msg = (f"Application validated. Credit score: {data.get('credit_score','?')}. "
               f"Annual income: {data.get('annual_income','?'):,}. "
               f"{'No critical errors found.' if valid else 'CRITICAL ERRORS — do not proceed.'}")
        alerts.agent_message(app_id, "Agent 1 — Validator",
                             "Agent 2 — Financial Analyzer", msg)

        alerts.agent_completed(app_id, "Agent 1 — Validator",
                               f"Validation complete. Proceed: {valid}")

    logger.info(f"  proceed={valid}")
    logger.info("AGENT 1 — complete")

    return {**state,
            "raw_application":       data,
            "validated_application": data,
            "validation_errors":     errors,
            "validation_summary":    summary,
            "proceed_to_analysis":   valid,
            "agent_messages": state.get("agent_messages", []) + [{
                "from": "Agent1", "to": "Agent2",
                "message": f"Validation {'PASSED' if valid else 'FAILED'}. "
                           f"Errors: {result['error_count']}. Proceed: {valid}."
            }]}


def _llm(prompt: str, fallback: str) -> str:
    try:
        return OllamaLLM(model=OLLAMA_MODEL).invoke(prompt).strip()
    except Exception as e:
        logger.warning(f"  LLM unavailable: {e}")
        return fallback


def _fallback_summary(errors, data) -> str:
    name = data.get("applicant_name", "The applicant")
    if not errors:
        return (f"{name}'s application data is complete and passes all validation checks. "
                "All required fields are present with valid values. "
                "The application is ready for financial risk analysis.")
    critical = [e for e in errors if e.get("severity") == "CRITICAL"]
    fields   = ", ".join(e["field"] for e in critical[:3])
    return (f"{name}'s application has {len(critical)} critical validation error(s) "
            f"in: {fields}. These must be resolved before analysis can proceed.")
