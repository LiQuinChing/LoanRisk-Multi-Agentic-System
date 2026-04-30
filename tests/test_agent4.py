import pytest
from pathlib import Path
from tools.tool4_report_writer import write_html_report

BASE = {
    "application_id":"LOAN-TEST-999","applicant_name":"Chamara Bandara",
    "loan_amount":5000000,"loan_amount_requested":5000000,"loan_purpose":"home_purchase",
    "loan_term_months":180,"employment_status":"full_time","annual_income":1200000,
    "credit_score":710,"national_id":"200099998V",
    "financial_metrics":{"monthly_income":100000,"monthly_payment":54642,
                         "dti_ratio":0.43,"dti_percent":43.0,"ltv_ratio":0.77,
                         "ltv_percent":77.0,"financial_risk_score":48.5},
    "financial_risk_tier":"MEDIUM","fraud_flags":[],"fraud_risk_level":"LOW",
    "final_decision":"APPROVE","suggestions":["Conduct final KYC verification."],
    "decision_reasoning":"Applicant demonstrates adequate repayment capacity.",
    "validation_summary":"All fields validated successfully.",
}

class TestFileCreation:
    def test_file_created(self, tmp_path):
        p = write_html_report(BASE, str(tmp_path))
        assert Path(p).exists()
    def test_returns_string(self, tmp_path):
        assert isinstance(write_html_report(BASE, str(tmp_path)), str)
    def test_html_extension(self, tmp_path):
        assert write_html_report(BASE, str(tmp_path)).endswith(".html")
    def test_not_empty(self, tmp_path):
        p = write_html_report(BASE, str(tmp_path))
        assert Path(p).stat().st_size > 500
    def test_creates_nested_dir(self, tmp_path):
        p = write_html_report(BASE, str(tmp_path / "a" / "b"))
        assert Path(p).exists()

class TestContent:
    def _html(self, tmp_path): return Path(write_html_report(BASE, str(tmp_path))).read_text(encoding="utf-8")
    def test_name_present(self, tmp_path):     assert "Chamara Bandara" in self._html(tmp_path)
    def test_app_id_present(self, tmp_path):   assert "LOAN-TEST-999"   in self._html(tmp_path)
    def test_decision_present(self, tmp_path): assert "APPROVED"        in self._html(tmp_path)
    def test_dti_present(self, tmp_path):      assert "43.0"            in self._html(tmp_path)
    def test_suggestion(self, tmp_path):       assert "KYC"             in self._html(tmp_path)
    def test_reasoning(self, tmp_path):        assert "repayment capacity" in self._html(tmp_path)

class TestDecisionColors:
    def _html(self, tmp_path, dec):
        return Path(write_html_report({**BASE,"final_decision":dec}, str(tmp_path))).read_text(encoding="utf-8")
    def test_approve_green(self, tmp_path):  assert "#059669" in self._html(tmp_path,"APPROVE")
    def test_reject_red(self, tmp_path):     assert "#dc2626" in self._html(tmp_path,"REJECT")
    def test_review_amber(self, tmp_path):   assert "#d97706" in self._html(tmp_path,"MANUAL_REVIEW")

class TestFraudFlags:
    def test_flags_shown(self, tmp_path):
        data = {**BASE,"fraud_flags":[{"flag_type":"blacklisted_national_id",
                "description":"NIC found in fraud blacklist.","severity":"HIGH"}]}
        html = Path(write_html_report(data, str(tmp_path))).read_text(encoding="utf-8")
        assert "fraud blacklist" in html
    def test_no_flags_clean_msg(self, tmp_path):
        html = Path(write_html_report({**BASE,"fraud_flags":[]}, str(tmp_path))).read_text(encoding="utf-8")
        assert "No fraud flags" in html

class TestMissingKeys:
    def test_missing_app_id(self, tmp_path):
        with pytest.raises(KeyError): write_html_report({k:v for k,v in BASE.items() if k!="application_id"}, str(tmp_path))
    def test_missing_name(self, tmp_path):
        with pytest.raises(KeyError): write_html_report({k:v for k,v in BASE.items() if k!="applicant_name"}, str(tmp_path))
    def test_missing_decision(self, tmp_path):
        with pytest.raises(KeyError): write_html_report({k:v for k,v in BASE.items() if k!="final_decision"}, str(tmp_path))
