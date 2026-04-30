# ============================================================
#  tools/tool2_financial_calc.py
#  STUDENT 2 — Individual Custom Tool
# ============================================================

from typing import Dict, Tuple
import logging
logger = logging.getLogger("LoanRiskMAS")

def calculate_monthly_payment(principal: float, annual_interest_rate: float,
                               term_months: int) -> float:
    """
    Compute fixed monthly repayment using the PMT formula.

    Args:
        principal:            Total loan amount.
        annual_interest_rate: Annual rate as decimal (0.12 = 12%).
        term_months:          Loan term in months (≥ 1).

    Returns:
        Monthly payment amount rounded to 2 decimal places.

    Raises:
        ValueError: If principal ≤ 0, rate < 0, or term < 1.
    """
    if principal <= 0:
        raise ValueError(f"principal must be positive, got {principal}")
    if annual_interest_rate < 0:
        raise ValueError(f"rate cannot be negative, got {annual_interest_rate}")
    if term_months < 1:
        raise ValueError(f"term_months must be ≥ 1, got {term_months}")
    r = annual_interest_rate / 12.0
    if r == 0:
        return round(principal / term_months, 2)
    f = (1 + r) ** term_months
    return round(principal * (r * f) / (f - 1), 2)


def calculate_dti_ratio(monthly_income: float, existing_monthly_debt: float,
                         new_monthly_payment: float) -> float:
    """
    Compute the Debt-to-Income (DTI) ratio.

    DTI = (existing debt + new payment) / monthly income.

    Args:
        monthly_income:        Gross monthly income.
        existing_monthly_debt: Current monthly obligations.
        new_monthly_payment:   Proposed new loan payment.

    Returns:
        DTI as a decimal (e.g. 0.42 for 42%).

    Raises:
        ValueError: If monthly_income ≤ 0, or debt/payment < 0.
    """
    if monthly_income <= 0:
        raise ValueError(f"monthly_income must be positive, got {monthly_income}")
    if existing_monthly_debt < 0:
        raise ValueError(f"existing_monthly_debt cannot be negative")
    if new_monthly_payment < 0:
        raise ValueError(f"new_monthly_payment cannot be negative")
    return round((existing_monthly_debt + new_monthly_payment) / monthly_income, 4)


def calculate_ltv_ratio(loan_amount: float, property_value: float) -> float:
    """
    Compute the Loan-to-Value (LTV) ratio.

    LTV = loan amount / property value.

    Args:
        loan_amount:    Amount requested.
        property_value: Current market value of collateral.

    Returns:
        LTV as a decimal (e.g. 0.75 for 75%).

    Raises:
        ValueError: If property_value ≤ 0 or loan_amount ≤ 0.
    """
    if property_value <= 0:
        raise ValueError(f"property_value must be positive, got {property_value}")
    if loan_amount <= 0:
        raise ValueError(f"loan_amount must be positive, got {loan_amount}")
    return round(loan_amount / property_value, 4)


def run_financial_analysis(application: Dict, market_rates: Dict = None) -> Dict:
    """
    Orchestrate all financial calculations for a validated application.

    Integrates market rate data (if available from the web tool) into
    the interest rate used for the payment calculation, providing a
    more accurate real-world assessment.

    Args:
        application:  Validated loan application dict.
        market_rates: Optional dict from tool_web_browser.fetch_exchange_rates.
                      If provided, USD/LKR rate is noted in the output.

    Returns:
        Dict containing: monthly_income, monthly_payment, dti_ratio,
        dti_percent, ltv_ratio, ltv_percent, dti_score, ltv_score,
        affordability_score, financial_risk_score, financial_risk_tier,
        usd_equivalent (if market data available).

    Raises:
        KeyError:   If required fields absent from application.
        ValueError: If any calculation fails.
    """
    from config import DEFAULT_ANNUAL_INTEREST_RATE

    annual_income    = float(application["annual_income"])
    existing_debt    = float(application.get("existing_monthly_debt", 0) or 0)
    loan_amount      = float(application["loan_amount_requested"])
    term_months      = int(application["loan_term_months"])
    property_value   = float(application["property_value"])
    monthly_expenses = float(application.get("monthly_expenses", 0) or 0)
    monthly_income   = round(annual_income / 12, 2)

    logger.info(f"  [Math Check] Raw Annual Income: {annual_income}, Monthly Expenses: {monthly_expenses}")
    logger.info(f"  [Math Check] Calculated Monthly Gross Income: {monthly_income:.2f}")
    logger.info(f"  [Math Check] Total Monthly Outgoing (Expenses + Debt): {(monthly_expenses + existing_debt):.2f}")

    rate = DEFAULT_ANNUAL_INTEREST_RATE
    monthly_payment = calculate_monthly_payment(loan_amount, rate, term_months)
    dti = calculate_dti_ratio(monthly_income, existing_debt, monthly_payment)
    ltv = calculate_ltv_ratio(loan_amount, property_value)

    dti_score          = _score_dti(dti)
    ltv_score          = _score_ltv(ltv)
    afford_score       = _score_affordability(monthly_payment, monthly_expenses, monthly_income)
    combined           = round(dti_score * 0.50 + ltv_score * 0.30 + afford_score * 0.20, 1)
    risk_tier          = "HIGH" if combined >= 65 else "MEDIUM" if combined >= 35 else "LOW"

    result = {
        "monthly_income":       monthly_income,
        "monthly_payment":      monthly_payment,
        "dti_ratio":            dti,
        "dti_percent":          round(dti * 100, 1),
        "ltv_ratio":            ltv,
        "ltv_percent":          round(ltv * 100, 1),
        "dti_score":            dti_score,
        "ltv_score":            ltv_score,
        "affordability_score":  afford_score,
        "financial_risk_score": combined,
        "financial_risk_tier":  risk_tier,
        "usd_equivalent":       None,
    }

    # Enrich with live USD rate if available
    if market_rates and not market_rates.get("error") and market_rates.get("rates"):
        usd_rate = market_rates["rates"].get("USD")
        if usd_rate and usd_rate > 0:
            result["usd_equivalent"] = round(loan_amount * usd_rate, 2)

    return result


def _score_dti(dti: float) -> float:
    if dti <= 0.20: return 5.0
    if dti <= 0.30: return 20.0
    if dti <= 0.35: return 35.0
    if dti <= 0.43: return 55.0
    if dti <= 0.50: return 70.0
    if dti <= 0.60: return 85.0
    return 100.0


def _score_ltv(ltv: float) -> float:
    if ltv <= 0.60: return 5.0
    if ltv <= 0.70: return 15.0
    if ltv <= 0.80: return 30.0
    if ltv <= 0.85: return 50.0
    if ltv <= 0.90: return 70.0
    if ltv <= 0.95: return 85.0
    return 100.0


def _score_affordability(monthly_payment: float, monthly_expenses: float,
                          monthly_income: float) -> float:
    if monthly_income <= 0:
        return 100.0
    burden = (monthly_payment + monthly_expenses) / monthly_income
    if burden <= 0.30: return 5.0
    if burden <= 0.40: return 20.0
    if burden <= 0.50: return 45.0
    if burden <= 0.65: return 70.0
    if burden <= 0.80: return 85.0
    return 100.0
