import pytest
from tools.tool2_financial_calc import (
    calculate_monthly_payment, calculate_dti_ratio,
    calculate_ltv_ratio, run_financial_analysis,
)

APP = {"annual_income":1800000,"monthly_expenses":45000,"loan_amount_requested":8000000,
       "loan_term_months":240,"property_value":12000000,"existing_monthly_debt":15000}

class TestMonthlyPayment:
    def test_known_value(self):
        assert abs(calculate_monthly_payment(100000, 0.12, 12) - 8884.88) < 1.0
    def test_zero_rate(self):
        assert calculate_monthly_payment(120000, 0.0, 12) == 10000.0
    def test_negative_principal(self):
        with pytest.raises(ValueError): calculate_monthly_payment(-1, 0.12, 12)
    def test_zero_term(self):
        with pytest.raises(ValueError): calculate_monthly_payment(100000, 0.12, 0)
    def test_negative_rate(self):
        with pytest.raises(ValueError): calculate_monthly_payment(100000, -0.1, 12)

class TestDTI:
    def test_correct(self):
        assert abs(calculate_dti_ratio(10000, 1500, 2000) - 0.35) < 0.001
    def test_zero_debt(self):
        assert abs(calculate_dti_ratio(10000, 0, 3000) - 0.30) < 0.001
    def test_zero_income(self):
        with pytest.raises(ValueError): calculate_dti_ratio(0, 1000, 2000)
    def test_negative_debt(self):
        with pytest.raises(ValueError): calculate_dti_ratio(10000, -500, 2000)

class TestLTV:
    def test_correct(self):
        assert abs(calculate_ltv_ratio(800000, 1000000) - 0.80) < 0.001
    def test_zero_property(self):
        with pytest.raises(ValueError): calculate_ltv_ratio(500000, 0)
    def test_zero_loan(self):
        with pytest.raises(ValueError): calculate_ltv_ratio(0, 1000000)
    def test_above_one(self):
        assert calculate_ltv_ratio(1200000, 1000000) > 1.0

class TestFullAnalysis:
    def test_required_keys(self):
        r = run_financial_analysis(APP)
        for k in ("monthly_income","monthly_payment","dti_ratio","ltv_ratio",
                  "financial_risk_score","financial_risk_tier"):
            assert k in r
    def test_score_range(self):
        assert 0 <= run_financial_analysis(APP)["financial_risk_score"] <= 100
    def test_high_dti_tier(self):
        bad = {**APP, "existing_monthly_debt": 200000}
        assert run_financial_analysis(bad)["financial_risk_tier"] in ("MEDIUM","HIGH")
    def test_missing_field(self):
        with pytest.raises(KeyError):
            run_financial_analysis({k:v for k,v in APP.items() if k!="annual_income"})
    def test_usd_equivalent_none_without_rates(self):
        r = run_financial_analysis(APP)
        assert r["usd_equivalent"] is None
