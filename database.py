# ============================================================
#  database.py — Loan application storage (SQLite)
#
#  Stores applications submitted via the web UI.
#  Agent 1 reads from this DB via tool1_db_reader.
# ============================================================

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from config import APP_DB_PATH


def _connect() -> sqlite3.Connection:
    Path(APP_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(APP_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_application_db() -> None:
    """Create the loan_applications table if it does not exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS loan_applications (
            application_id       TEXT PRIMARY KEY,
            applicant_name       TEXT NOT NULL,
            national_id          TEXT,
            phone_number         TEXT,
            address              TEXT,
            annual_income        REAL,
            monthly_expenses     REAL,
            existing_monthly_debt REAL,
            loan_amount_requested REAL,
            loan_term_months     INTEGER,
            loan_purpose         TEXT,
            property_value       REAL,
            employment_status    TEXT,
            employer_name        TEXT,
            years_employed       REAL,
            credit_score         INTEGER,
            status               TEXT DEFAULT 'PENDING',
            final_decision       TEXT,
            report_path          TEXT,
            submitted_at         TEXT,
            completed_at         TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_application(form_data: Dict[str, Any]) -> str:
    """
    Persist a loan application from the web form to the database.

    Generates a unique application ID, timestamps the record, and
    inserts all form fields.  Returns the generated application ID.

    Args:
        form_data: Dict of form field names to values (strings from
                   Flask request.form).

    Returns:
        The generated ``application_id`` string (e.g. ``LOAN-20240120-A1B2``).
    """
    app_id = f"LOAN-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    conn = _connect()
    conn.execute("""
        INSERT INTO loan_applications (
            application_id, applicant_name, national_id, phone_number,
            address, annual_income, monthly_expenses, existing_monthly_debt,
            loan_amount_requested, loan_term_months, loan_purpose,
            property_value, employment_status, employer_name,
            years_employed, credit_score, submitted_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        app_id,
        form_data.get("applicant_name", ""),
        form_data.get("national_id", ""),
        form_data.get("phone_number", ""),
        form_data.get("address", ""),
        _f(form_data.get("annual_income")),
        _f(form_data.get("monthly_expenses")),
        _f(form_data.get("existing_monthly_debt")),
        _f(form_data.get("loan_amount_requested")),
        _i(form_data.get("loan_term_months")),
        form_data.get("loan_purpose", ""),
        _f(form_data.get("property_value")),
        form_data.get("employment_status", ""),
        form_data.get("employer_name", ""),
        _f(form_data.get("years_employed")),
        _i(form_data.get("credit_score")),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()
    return app_id


def get_application(app_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a loan application by its ID.

    Args:
        app_id: The application identifier string.

    Returns:
        Dict of application fields, or ``None`` if not found.
    """
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM loan_applications WHERE application_id = ?", (app_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_status(app_id: str, status: str, decision: str = "", report_path: str = "") -> None:
    """Update the processing status and final decision of an application."""
    conn = _connect()
    conn.execute("""
        UPDATE loan_applications
        SET status = ?, final_decision = ?, report_path = ?, completed_at = ?
        WHERE application_id = ?
    """, (status, decision, report_path, datetime.now().isoformat(), app_id))
    conn.commit()
    conn.close()


def _f(v) -> Optional[float]:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _i(v) -> Optional[int]:
    try:
        return int(float(v)) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None
