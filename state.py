# ============================================================
#  state.py — Global shared state (LangGraph TypedDict)
# ============================================================

from typing import Any, Dict, List, TypedDict


class LoanState(TypedDict):
    # ── Routing ───────────────────────────────────────────────
    application_id:   str            # set by Flask or CLI
    application_path: str            # JSON path (CLI mode only)
    mode:             str            # "web" | "cli"

    # ── Inter-agent messages (agents write notes for each other)
    agent_messages: List[Dict[str, str]]  # [{from, to, message}]

    # ── Agent 1 — Application Validator ──────────────────────
    raw_application:       Dict[str, Any]
    validated_application: Dict[str, Any]
    validation_errors:     List[Dict[str, str]]
    validation_summary:    str
    proceed_to_analysis:   bool

    # ── Agent 2 — Financial Risk Analyzer ────────────────────
    financial_metrics:    Dict[str, float]
    financial_risk_score: float
    financial_risk_tier:  str
    financial_summary:    str
    market_rates:         Dict[str, Any]   # fetched from web

    # ── Agent 3 — Fraud Detector ──────────────────────────────
    fraud_flags:      List[Dict[str, Any]]
    fraud_risk_score: float
    fraud_risk_level: str
    fraud_summary:    str
    employer_web_check: str                # result of employer web lookup

    # ── Agent 4 — Decision Writer ─────────────────────────────
    final_decision:    str
    decision_reasoning: str
    suggestions:       List[str]           # actionable suggestions
    report_path:       str
