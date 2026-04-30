# ============================================================
#  app.py — Ceylon National Bank Loan Assessment Web App
#
#  Run:  python app.py
#  Open: http://localhost:5000
# ============================================================

import json
import threading
from pathlib import Path

from flask import Flask, Response, redirect, render_template, request, url_for

import alert_system as alerts
from config import FLASK_DEBUG, FLASK_PORT, REPORTS_DIR
from database import get_application, init_application_db, save_application, update_status
from logger_config import logger
from main import run_assessment

app = Flask(__name__)
app.secret_key = "ceylon-national-bank-2024"

# ── Ensure directories exist ───────────────────────────────────
Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
Path("logs").mkdir(exist_ok=True)


# ── Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    """Show the loan application form."""
    return render_template("index.html")


@app.route("/apply", methods=["POST"])
def apply():
    """
    Receive submitted loan form, save to DB, start pipeline in
    background thread, then redirect to the live processing page.
    """
    form_data = request.form.to_dict()
    app_id    = save_application(form_data)
    logger.info(f"New application submitted: {app_id}")

    # Create SSE queue BEFORE starting thread
    alerts.create_queue(app_id)

    # Run pipeline in background so Flask can serve SSE immediately
    thread = threading.Thread(
        target=_run_pipeline,
        args=(app_id,),
        daemon=True,
    )
    thread.start()

    return redirect(url_for("processing", app_id=app_id))


@app.route("/processing/<app_id>")
def processing(app_id):
    """Show the real-time processing dashboard."""
    application = get_application(app_id)
    if not application:
        return "Application not found", 404
    return render_template("processing.html", app=application, app_id=app_id)


@app.route("/stream/<app_id>")
def stream(app_id):
    """
    Server-Sent Events endpoint.  Streams alert dicts as JSON
    to the browser as agents produce them.  Closes when
    PIPELINE_COMPLETE is received.
    """
    def event_generator():
        while True:
            alert = alerts.get_next_alert(app_id, timeout=1.0)
            if alert is None:
                # Heartbeat keeps connection alive
                yield "data: {\"type\":\"HEARTBEAT\"}\n\n"
                continue
            yield f"data: {json.dumps(alert)}\n\n"
            if alert.get("type") == "PIPELINE_COMPLETE":
                break
        alerts.remove_queue(app_id)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":      "keep-alive",
        },
    )


@app.route("/report/<app_id>")
def report(app_id):
    """Serve the generated HTML report inline in the browser."""
    application = get_application(app_id)
    if not application or not application.get("report_path"):
        return "Report not yet available. Please wait for processing to complete.", 404
    rp = Path(application["report_path"])
    if not rp.exists():
        return "Report file not found on disk.", 404
    return rp.read_text(encoding="utf-8")


# ── Background pipeline runner ─────────────────────────────────

def _run_pipeline(app_id: str) -> None:
    """Run the LangGraph pipeline in a background thread."""
    try:
        update_status(app_id, "PROCESSING")
        result = run_assessment(application_id=app_id, mode="web")
        decision    = result.get("final_decision", "UNKNOWN")
        report_path = result.get("report_path", "")
        update_status(app_id, "COMPLETE", decision, report_path)
        logger.info(f"Pipeline done for {app_id}: {decision}")
    except Exception as exc:
        logger.error(f"Pipeline error for {app_id}: {exc}")
        update_status(app_id, "ERROR")
        alerts.send_alert(app_id, {
            "type":    "PIPELINE_ERROR",
            "title":   "System Error",
            "message": str(exc),
            "severity": "error",
        })
        alerts.pipeline_complete(app_id, "")


# ── Entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    init_application_db()
    print("\n" + "═" * 55)
    print("  Ceylon National Bank — Loan Assessment System")
    print(f"  Open your browser at: http://localhost:{FLASK_PORT}")
    print("═" * 55 + "\n")
    app.run(
        debug=FLASK_DEBUG,
        threaded=True,
        port=FLASK_PORT,
        use_reloader=False,   # reloader breaks background threads
    )
