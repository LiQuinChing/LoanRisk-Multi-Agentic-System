# ============================================================
#  tools/tool1_db_reader.py
#  STUDENT 1 — Individual Custom Tool
#
#  Reads a loan application from the SQLite applications database
#  (web UI mode) OR from a JSON file (CLI mode), then validates
#  the data against the banking schema.
# ============================================================

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from config import APP_DB_PATH

REQUIRED_FIELDS: Dict[str, type] = {
    "applicant_name":        str,
    "annual_income":         (int, float),
    "monthly_expenses":      (int, float),
    "loan_amount_requested": (int, float),
    "loan_term_months":      int,
    "loan_purpose":          str,
    "property_value":        (int, float),
    "employment_status":     str,
    "employer_name":         str,
    "years_employed":        (int, float),
    "existing_monthly_debt": (int, float),
    "credit_score":          int,
    "address":               str,
}

FIELD_RANGES: Dict[str, Tuple[float, float]] = {
    "annual_income":         (1,         1_000_000_000),
    "loan_amount_requested": (1,         2_000_000_000),
    "loan_term_months":      (6,         480),
    "credit_score":          (300,       900),
    "property_value":        (1,         5_000_000_000),
    "years_employed":        (0,         60),
    "existing_monthly_debt": (0,         100_000_000),
    "monthly_expenses":      (0,         100_000_000),
}


def read_and_validate_application(
    application_id: str = "",
    file_path: str = "",
) -> Dict[str, Any]:
    """
    Read a loan application from the database or a JSON file and
    perform full schema validation.

    When *application_id* is provided the function reads from the
    SQLite applications database (web UI mode).  When *file_path* is
    provided it reads from a JSON file on disk (CLI mode).

    Validation layers:
        1. Required-field presence and correct Python type.
        2. Numeric value within acceptable business ranges.
        3. Cross-field logical consistency check.

    Args:
        application_id: The unique ID of an application stored in the
            SQLite applications database (``data/applications.db``).
            Pass an empty string to use *file_path* instead.
        file_path:      Absolute or relative path to a ``.json`` loan
            application file.  Ignored when *application_id* is set.

    Returns:
        Dict with keys:
            ``"data"``          – the application dict (or {} on failure),
            ``"errors"``        – list of ``{field, issue, severity}`` dicts,
            ``"is_valid"``      – True when zero CRITICAL errors found,
            ``"error_count"``   – total errors,
            ``"critical_count"``– CRITICAL errors only.

    Raises:
        ValueError:       If neither *application_id* nor *file_path* given.
        FileNotFoundError: If *file_path* does not exist.
        sqlite3.Error:    If the database cannot be read.
    """
    if not application_id and not file_path:
        raise ValueError("Provide either application_id or file_path.")

    # ── Load data ──────────────────────────────────────────────
    if application_id:
        data = _load_from_db(application_id)
    else:
        data = _load_from_file(file_path)

    errors: List[Dict[str, str]] = []

    # ── Required-field & type checks ──────────────────────────
    for field, expected in REQUIRED_FIELDS.items():
        val = data.get(field)
        if val is None or val == "":
            errors.append({"field": field, "issue": "Required field missing or empty.",
                           "severity": "CRITICAL"})
            continue
        if not isinstance(val, expected):
            try:
                # attempt type coercion (DB stores everything as text/real)
                if expected == int:
                    data[field] = int(float(str(val)))
                elif expected == (int, float):
                    data[field] = float(str(val))
            except (ValueError, TypeError):
                errors.append({"field": field,
                               "issue": f"Expected {expected}, got {type(val).__name__}.",
                               "severity": "CRITICAL"})

    # ── Range checks ──────────────────────────────────────────
    for field, (lo, hi) in FIELD_RANGES.items():
        if field in data and data[field] is not None:
            try:
                v = float(data[field])
                if not (lo <= v <= hi):
                    errors.append({"field": field,
                                   "issue": f"Value {v:,.2f} outside range [{lo:,.0f}–{hi:,.0f}].",
                                   "severity": "CRITICAL"})
            except (TypeError, ValueError):
                pass

    critical = sum(1 for e in errors if e["severity"] == "CRITICAL")
    return {
        "data":           data,
        "errors":         errors,
        "is_valid":       critical == 0,
        "error_count":    len(errors),
        "critical_count": critical,
    }


def _load_from_db(application_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(APP_DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM loan_applications WHERE application_id = ?",
        (application_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Application '{application_id}' not found in database.")
    d = dict(row)
    d.setdefault("application_id", application_id)
    return d


def _load_from_file(file_path: str) -> Dict[str, Any]:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)
