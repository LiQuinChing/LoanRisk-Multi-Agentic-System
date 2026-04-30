# ============================================================
#  alert_system.py — Thread-safe real-time alert broadcaster
#
#  Agents call send_alert(app_id, alert) to push a message.
#  The Flask SSE endpoint reads from get_next_alert(app_id).
#  Each application gets its own isolated queue.
# ============================================================

import queue
import threading
from typing import Any, Dict, Optional

_queues: Dict[str, queue.Queue] = {}
_lock = threading.Lock()


def create_queue(app_id: str) -> None:
    """Create a new alert queue for an application pipeline run."""
    with _lock:
        _queues[app_id] = queue.Queue()


def send_alert(app_id: str, alert: Dict[str, Any]) -> None:
    """
    Push an alert dict into the queue for a given application.

    Called by agents during pipeline execution.  The Flask SSE
    endpoint drains this queue and streams events to the browser.

    Args:
        app_id: The unique application identifier.
        alert:  Dict with at minimum ``type``, ``title``, ``message``.
                Optional keys: ``severity``, ``suggestions``, ``agent``.
    """
    with _lock:
        q = _queues.get(app_id)
    if q:
        q.put(alert)


def get_next_alert(app_id: str, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
    """
    Pop the next alert for an application, blocking up to *timeout* seconds.

    Args:
        app_id:  Application identifier.
        timeout: Max seconds to wait for an alert (default 1 s).

    Returns:
        Alert dict, or ``None`` if nothing arrived within *timeout*.
    """
    with _lock:
        q = _queues.get(app_id)
    if not q:
        return None
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None


def remove_queue(app_id: str) -> None:
    """Remove the queue for a completed application (cleanup)."""
    with _lock:
        _queues.pop(app_id, None)


# ── Convenience alert constructors ───────────────────────────

def agent_started(app_id: str, agent_name: str, message: str) -> None:
    send_alert(app_id, {
        "type": "AGENT_START", "agent": agent_name,
        "title": f"{agent_name} started", "message": message,
        "severity": "info",
    })


def agent_completed(app_id: str, agent_name: str, message: str) -> None:
    send_alert(app_id, {
        "type": "AGENT_COMPLETE", "agent": agent_name,
        "title": f"{agent_name} complete", "message": message,
        "severity": "info",
    })


def agent_message(app_id: str, from_agent: str, to_agent: str, message: str) -> None:
    """Send an explicit inter-agent message visible on the UI."""
    send_alert(app_id, {
        "type": "AGENT_MESSAGE",
        "agent": from_agent,
        "title": f"{from_agent} → {to_agent}",
        "message": message,
        "severity": "info",
    })


def fraud_alert(app_id: str, description: str, suggestions: list) -> None:
    send_alert(app_id, {
        "type": "FRAUD_ALERT",
        "agent": "Fraud Detector",
        "title": "FRAUD ALERT — Inform Branch Manager",
        "message": description,
        "severity": "critical",
        "action": "Hold all banking activity for this customer until further notice.",
        "suggestions": suggestions,
    })


def credit_risk_alert(app_id: str, description: str, suggestions: list) -> None:
    send_alert(app_id, {
        "type": "CREDIT_RISK",
        "agent": "Financial Analyzer",
        "title": "Credit Risk Too High",
        "message": description,
        "severity": "high",
        "action": "Inform branch manager and discuss risk mitigation options with applicant.",
        "suggestions": suggestions,
    })


def web_search_alert(app_id: str, agent_name: str, what: str, result: str) -> None:
    send_alert(app_id, {
        "type": "WEB_SEARCH",
        "agent": agent_name,
        "title": f"Web lookup: {what}",
        "message": result,
        "severity": "info",
    })


def decision_alert(app_id: str, decision: str, reasoning: str, suggestions: list) -> None:
    sev = {"APPROVE": "success", "MANUAL_REVIEW": "warning", "REJECT": "error"}.get(decision, "info")
    send_alert(app_id, {
        "type": "FINAL_DECISION",
        "agent": "Decision Writer",
        "title": f"Final Decision: {decision}",
        "message": reasoning,
        "severity": sev,
        "suggestions": suggestions,
    })


def pipeline_complete(app_id: str, report_path: str) -> None:
    send_alert(app_id, {
        "type": "PIPELINE_COMPLETE",
        "title": "Assessment Complete",
        "message": "All agents have finished processing.",
        "severity": "info",
        "report_path": report_path,
    })
