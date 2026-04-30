# ============================================================
#  db_setup.py — Creates and seeds all databases
#  Run once: python db_setup.py
# ============================================================

import sqlite3
from pathlib import Path

from logger_config import logger
from database import init_application_db
from config import FRAUD_DB_PATH


def create_fraud_database(db_path: str = FRAUD_DB_PATH) -> None:
    """
    Create and seed the fraud-detection SQLite database.

    Tables created:
        blacklisted_national_ids  — known fraudster NICs
        blacklisted_names         — known fraudster full names
        blacklisted_addresses     — known fraud addresses
        fraud_patterns            — loan-to-income ratio rules
        suspicious_employers      — unverifiable employers
        fraud_network             — linked fraud groups

    Args:
        db_path: Path where the .db file will be created.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # ── National ID blacklist ─────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklisted_national_ids (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id  TEXT NOT NULL UNIQUE,
            reason       TEXT,
            case_number  TEXT,
            added_date   TEXT DEFAULT (date('now'))
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO blacklisted_national_ids (national_id, reason, case_number) VALUES (?,?,?)",
        [
            ("199012345V",    "Convicted bank fraud — 3 counts",          "CID/2023/0451"),
            ("198567890123",  "Identity theft suspect — under investigation","CID/2024/0112"),
            ("200123456789",  "Synthetic identity fraud — loan stacking",  "CID/2024/0789"),
            ("197845678V",    "Money laundering — linked to fraud ring",   "CID/2022/1823"),
            ("199534521V",    "Multiple loan defaults — 6 banks",          "CID/2023/0992"),
            ("198012378901",  "Forged employment documents",               "CID/2024/0341"),
        ],
    )

    # ── Full name blacklist ───────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklisted_names (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name   TEXT NOT NULL UNIQUE,
            reason      TEXT,
            case_number TEXT
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO blacklisted_names (full_name, reason, case_number) VALUES (?,?,?)",
        [
            ("Ruwan Kumara Dissanayake",  "Bank fraud conviction 2023",          "CID/2023/0451"),
            ("Thilak Bandara Rajapaksa",  "Multiple loan defaults — 5 banks",    "CID/2023/0992"),
            ("Sanduni Malsha Perera",     "Identity fraud — NIC forged",         "CID/2024/0112"),
            ("Pradeep Chaminda Jayaweera","Fraudulent property valuation",        "CID/2022/1201"),
            ("Nilmini Chathurika Mendis", "Loan application forgery",            "CID/2024/0341"),
        ],
    )

    # ── Blacklisted addresses ─────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklisted_addresses (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            address_fragment TEXT NOT NULL UNIQUE,
            reason           TEXT
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO blacklisted_addresses (address_fragment, reason) VALUES (?,?)",
        [
            ("PO Box 9999",        "Known fraud mail-drop"),
            ("No Fixed Abode",     "No permanent address"),
            ("c/o Cash Loans Ltd", "Loan-stacking intermediary"),
            ("Abandoned Warehouse","Industrial address, not residential"),
        ],
    )

    # ── Loan-to-income ratio fraud patterns ───────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fraud_patterns (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type         TEXT NOT NULL,
            description          TEXT,
            loan_to_income_min   REAL,
            loan_to_income_max   REAL,
            risk_weight          REAL DEFAULT 1.0
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO fraud_patterns (pattern_type,description,loan_to_income_min,loan_to_income_max,risk_weight) VALUES (?,?,?,?,?)",
        [
            ("loan_to_income", "Extreme: loan > 15x annual income",   15.0, 9999.0, 1.0),
            ("loan_to_income", "Very high: loan 10–15x annual income", 10.0,  15.0, 0.75),
            ("loan_to_income", "High: loan 7–10x annual income",        7.0,  10.0, 0.50),
        ],
    )

    # ── Suspicious employers ──────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suspicious_employers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_name TEXT NOT NULL UNIQUE,
            reason        TEXT
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO suspicious_employers (employer_name, reason) VALUES (?,?)",
        [
            ("Cash in Hand",          "No formal employment record"),
            ("Self Employed Unknown", "Unverifiable income source"),
            ("Freelance Misc",        "Vague employer, income hard to verify"),
            ("ABC Holdings Ltd",      "Shell company — no verifiable business activity"),
            ("Quick Cash Solutions",  "Unlicensed money lender"),
        ],
    )

    # ── Fraud network (linked fraud groups) ───────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fraud_network (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id  TEXT,
            full_name    TEXT,
            phone        TEXT,
            network_id   TEXT,
            role         TEXT,
            notes        TEXT
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO fraud_network (national_id, full_name, phone, network_id, role, notes) VALUES (?,?,?,?,?,?)",
        [
            ("199012345V",   "Ruwan Kumara Dissanayake", "0771234567", "NET-001", "Ring leader",   "Controls 6 fake identities"),
            ("198567890123", "Asanka Pradeep Silva",     "0779876543", "NET-001", "ID forger",     "Forged NICs for ring"),
            ("200123456789", "Chamara Bandara Wijesinghe","0712345678","NET-001", "Mule",          "Receives loan proceeds"),
            ("199534521V",   "Thilak Bandara Rajapaksa", "0777654321", "NET-002", "Organizer",    "Coordinates applications"),
            ("198012378901", "Nilmini Chathurika Mendis","0754321098", "NET-002", "Accomplice",   "Provides false references"),
        ],
    )

    conn.commit()
    conn.close()
    logger.info(f"Fraud database ready at: {db_path}")
    print(f"[OK] Fraud database ready at: {db_path}")


if __name__ == "__main__":
    # Initialize both databases
    init_application_db()
    print("[OK] Application database ready at: data/applications.db")
    create_fraud_database()
    print("\n[OK] All databases initialized. You can now run: python app.py")
