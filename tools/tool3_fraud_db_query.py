# ============================================================
#  tools/tool3_fraud_db_query.py
#  STUDENT 3 — Individual Custom Tool
#
#  Queries the fraud database for NIC, name, address,
#  employer, loan-ratio, and fraud-network matches.
# ============================================================

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def query_fraud_database(application: Dict[str, Any],
                          db_path: str = "data/fraud_patterns.db") -> Dict[str, Any]:
    """
    Run a comprehensive fraud check against the local SQLite fraud database.

    Performs six independent checks:
        1. National ID (NIC) blacklist lookup.
        2. Full-name blacklist lookup (case-insensitive substring match).
        3. Blacklisted address fragment check.
        4. Loan-to-income ratio pattern match.
        5. Suspicious employer name check.
        6. Fraud network membership lookup.

    Each detected issue is returned as a structured flag dict so that
    Agent 3's LLM can generate a human-readable summary without
    re-running database logic.

    Args:
        application: Validated loan-application dict.  Checked keys:
            ``national_id``, ``applicant_name``, ``address``,
            ``annual_income``, ``loan_amount_requested``,
            ``employer_name``, ``employment_status``,
            ``years_employed``, ``credit_score``.
        db_path:     Path to the SQLite fraud database file.

    Returns:
        Dict with:
            ``"flags"``      – list of flag dicts (flag_type, description,
                               severity, weight),
            ``"flag_count"`` – int,
            ``"fraud_score"``– float 0–100,
            ``"risk_level"`` – "LOW" | "MEDIUM" | "HIGH",
            ``"nic_hit"``    – bool (True if NIC found in blacklist),
            ``"name_hit"``   – bool (True if name found in blacklist),
            ``"network_hit"``– bool (True if part of known fraud network).

    Raises:
        FileNotFoundError: If *db_path* does not exist.
        sqlite3.DatabaseError: If a SQL query fails.
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"Fraud database not found at '{db_path}'. Run python db_setup.py first."
        )

    flags: List[Dict[str, Any]] = []
    nic_hit = name_hit = network_hit = False

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur  = conn.cursor()

        # ── Check 1: National ID ──────────────────────────────
        nic = str(application.get("national_id", "") or "").strip()
        if nic:
            cur.execute(
                "SELECT reason, case_number FROM blacklisted_national_ids WHERE national_id = ?",
                (nic,)
            )
            row = cur.fetchone()
            if row:
                nic_hit = True
                flags.append({
                    "flag_type":   "blacklisted_national_id",
                    "description": (
                        f"NIC {nic} appears in the fraud blacklist. "
                        f"Reason: {row['reason']}. Case: {row['case_number']}"
                    ),
                    "severity": "HIGH",
                    "weight":   1.0,
                })

        # ── Check 2: Full name ────────────────────────────────
        name = str(application.get("applicant_name", "") or "").strip().lower()
        if name:
            cur.execute("SELECT full_name, reason, case_number FROM blacklisted_names")
            for row in cur.fetchall():
                if row["full_name"].lower() in name or name in row["full_name"].lower():
                    name_hit = True
                    flags.append({
                        "flag_type":   "blacklisted_name",
                        "description": (
                            f"Applicant name matches blacklisted entry: "
                            f"'{row['full_name']}'. Reason: {row['reason']}. "
                            f"Case: {row['case_number']}"
                        ),
                        "severity": "HIGH",
                        "weight":   0.95,
                    })

        # ── Check 3: Address ──────────────────────────────────
        address = str(application.get("address", "") or "").lower()
        cur.execute("SELECT address_fragment, reason FROM blacklisted_addresses")
        for row in cur.fetchall():
            if row["address_fragment"].lower() in address:
                flags.append({
                    "flag_type":   "blacklisted_address",
                    "description": (
                        f"Address matches blacklisted fragment "
                        f"'{row['address_fragment']}': {row['reason']}"
                    ),
                    "severity": "HIGH",
                    "weight":   1.0,
                })

        # ── Check 4: Loan-to-income ratio ─────────────────────
        income = float(application.get("annual_income") or 1)
        loan   = float(application.get("loan_amount_requested") or 0)
        ratio  = loan / income if income > 0 else 0
        cur.execute("""
            SELECT description, risk_weight FROM fraud_patterns
            WHERE pattern_type='loan_to_income'
              AND ? >= loan_to_income_min AND ? < loan_to_income_max
        """, (ratio, ratio))
        row = cur.fetchone()
        if row:
            flags.append({
                "flag_type":   "suspicious_loan_to_income_ratio",
                "description": (
                    f"Loan-to-income ratio is {ratio:.1f}× "
                    f"({loan:,.0f} / {income:,.0f}). {row['description']}"
                ),
                "severity": "HIGH" if row["risk_weight"] >= 0.75 else "MEDIUM",
                "weight":   row["risk_weight"],
            })

        # ── Check 5: Employer ─────────────────────────────────
        employer = str(application.get("employer_name", "") or "").strip().lower()
        cur.execute("SELECT employer_name, reason FROM suspicious_employers")
        for row in cur.fetchall():
            if row["employer_name"].lower() in employer or employer in row["employer_name"].lower():
                flags.append({
                    "flag_type":   "suspicious_employer",
                    "description": (
                        f"Employer '{application.get('employer_name')}' "
                        f"flagged: {row['reason']}"
                    ),
                    "severity": "MEDIUM",
                    "weight":   0.6,
                })

        # ── Check 6: Fraud network ────────────────────────────
        conditions, params = [], []
        if nic:
            conditions.append("national_id = ?")
            params.append(nic)
        if name:
            conditions.append("LOWER(full_name) LIKE ?")
            params.append(f"%{name}%")

        if conditions:
            cur.execute(
                f"SELECT * FROM fraud_network WHERE {' OR '.join(conditions)}",
                params
            )
            net_row = cur.fetchone()
            if net_row:
                network_hit = True
                flags.append({
                    "flag_type":   "fraud_network_member",
                    "description": (
                        f"Applicant is linked to fraud network {net_row['network_id']} "
                        f"(role: {net_row['role']}). {net_row['notes']}"
                    ),
                    "severity": "HIGH",
                    "weight":   1.0,
                })

        # ── Extra rule-based checks ───────────────────────────
        emp_status    = str(application.get("employment_status", "") or "")
        years_employed = float(application.get("years_employed") or 0)
        credit_score  = int(application.get("credit_score") or 700)

        if emp_status == "unemployed" and loan > 0:
            flags.append({
                "flag_type":   "unemployed_applicant",
                "description": "Applicant declared as unemployed but is applying for a loan.",
                "severity":    "HIGH",
                "weight":      0.9,
            })
        if years_employed < 0.5 and emp_status == "full_time":
            flags.append({
                "flag_type":   "very_new_employment",
                "description": (
                    f"Claims full-time employment but only {years_employed:.1f} years tenure."
                ),
                "severity": "MEDIUM",
                "weight":   0.5,
            })
        if credit_score < 500:
            flags.append({
                "flag_type":   "very_low_credit_score",
                "description": f"Credit score {credit_score} — critically low (below 500).",
                "severity":    "HIGH",
                "weight":      0.85,
            })

        conn.close()

    except sqlite3.DatabaseError as exc:
        raise sqlite3.DatabaseError(f"Failed to query fraud DB '{db_path}': {exc}") from exc

    fraud_score = _calculate_fraud_score(flags)
    risk_level  = "HIGH" if fraud_score >= 60 else "MEDIUM" if fraud_score >= 30 else "LOW"

    return {
        "flags":       flags,
        "flag_count":  len(flags),
        "fraud_score": fraud_score,
        "risk_level":  risk_level,
        "nic_hit":     nic_hit,
        "name_hit":    name_hit,
        "network_hit": network_hit,
    }


def _calculate_fraud_score(flags: List[Dict[str, Any]]) -> float:
    """
    Aggregate flag weights into a 0–100 fraud risk score using an
    exponential compounding model.

    Args:
        flags: List of flag dicts with a ``"weight"`` key (0.0–1.0).

    Returns:
        Rounded fraud risk score between 0.0 and 100.0.
    """
    if not flags:
        return 0.0
    remaining = 1.0
    for flag in flags:
        remaining *= (1.0 - float(flag.get("weight", 0.5)))
    return round(min((1.0 - remaining) * 100.0, 100.0), 1)
