# ============================================================
#  config.py — Central configuration
# ============================================================
OLLAMA_MODEL: str = "phi4-mini"          # change to phi4-mini if RAM is low

FRAUD_DB_PATH:    str = "data/fraud_patterns.db"
APP_DB_PATH:      str = "data/applications.db"
REPORTS_DIR:      str = "data/reports"
PENDING_DIR:      str = "data/pending"
LOGS_DIR:         str = "logs"

DEFAULT_ANNUAL_INTEREST_RATE: float = 0.12
MAX_ACCEPTABLE_DTI: float = 0.50
WARN_DTI:           float = 0.35
MAX_ACCEPTABLE_LTV: float = 0.90
WARN_LTV:           float = 0.80

REJECT_THRESHOLD: float = 75.0
REVIEW_THRESHOLD: float = 45.0

FLASK_PORT: int = 5000
FLASK_DEBUG: bool = True
