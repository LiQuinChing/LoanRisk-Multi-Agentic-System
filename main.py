# ============================================================
#  main.py — LangGraph orchestration (CLI + Web mode)
# ============================================================

import sys
from pathlib import Path

from langgraph.graph import END, StateGraph

from agents.agent1_validator        import agent1_validate
from agents.agent2_financial_analyzer import agent2_analyze_financials
from agents.agent3_fraud_detector   import agent3_detect_fraud
from agents.agent4_decision_writer  import agent4_write_decision
from logger_config import logger
from state import LoanState


def route_after_validation(state: LoanState) -> str:
    if state.get("proceed_to_analysis", True):
        logger.info("  Route: validation passed → financial analysis")
        return "analyze_financials"
    logger.info("  Route: validation failed → skip to decision")
    return "write_decision"


def build_graph():
    g = StateGraph(LoanState)
    g.add_node("validate",           agent1_validate)
    g.add_node("analyze_financials", agent2_analyze_financials)
    g.add_node("detect_fraud",       agent3_detect_fraud)
    g.add_node("write_decision",     agent4_write_decision)
    g.set_entry_point("validate")
    g.add_conditional_edges("validate", route_after_validation,
                            {"analyze_financials": "analyze_financials",
                             "write_decision":     "write_decision"})
    g.add_edge("analyze_financials", "detect_fraud")
    g.add_edge("detect_fraud",       "write_decision")
    g.add_edge("write_decision",     END)
    return g.compile()


def run_assessment(application_path: str = "",
                   application_id: str  = "",
                   mode: str = "cli") -> LoanState:
    """Run the full pipeline. Used by both CLI and Flask."""
    initial: LoanState = {
        "application_id":      application_id,
        "application_path":    application_path,
        "mode":                mode,
        "agent_messages":      [],
        "raw_application":     {},
        "validated_application": {},
        "validation_errors":   [],
        "validation_summary":  "",
        "proceed_to_analysis": True,
        "financial_metrics":   {},
        "financial_risk_score": 0.0,
        "financial_risk_tier": "",
        "financial_summary":   "",
        "market_rates":        {},
        "fraud_flags":         [],
        "fraud_risk_score":    0.0,
        "fraud_risk_level":    "",
        "fraud_summary":       "",
        "employer_web_check":  "",
        "final_decision":      "",
        "decision_reasoning":  "",
        "suggestions":         [],
        "report_path":         "",
    }
    logger.info("Pipeline starting")
    result = build_graph().invoke(initial)
    logger.info(f"Pipeline complete — Decision: {result.get('final_decision')}")
    return result


if __name__ == "__main__":
    app_file = sys.argv[1] if len(sys.argv) > 1 else "data/sample_application.json"
    if not Path(app_file).exists():
        print(f"ERROR: File not found: {app_file}"); sys.exit(1)

    result = run_assessment(application_path=app_file)

    print("\n" + "═"*60)
    print("  ASSESSMENT COMPLETE")
    print("═"*60)
    app = result.get("validated_application") or {}
    print(f"  Applicant  : {app.get('applicant_name','Unknown')}")
    print(f"  Fin. Score : {result.get('financial_risk_score',0):.1f}/100")
    print(f"  Fraud Score: {result.get('fraud_risk_score',0):.1f}/100")
    print(f"  Flags      : {len(result.get('fraud_flags',[]))}")
    print(f"  DECISION   : {result.get('final_decision','UNKNOWN')}")
    print(f"  Report     : {result.get('report_path','not saved')}")
    print("═"*60)
