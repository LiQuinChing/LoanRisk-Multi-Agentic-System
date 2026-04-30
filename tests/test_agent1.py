import json, os, tempfile
import pytest
from tools.tool1_db_reader import read_and_validate_application

VALID = {
    "application_id": "LOAN-TEST-001", "applicant_name": "Priya Fernando",
    "annual_income": 1800000, "monthly_expenses": 45000,
    "loan_amount_requested": 8000000, "loan_term_months": 240,
    "loan_purpose": "home_purchase", "property_value": 12000000,
    "employment_status": "full_time", "employer_name": "Dialog Axiata PLC",
    "years_employed": 4.5, "existing_monthly_debt": 15000,
    "credit_score": 720, "address": "42 Galle Road, Colombo 03",
}

def _tmp(data):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, f); f.close(); return f.name

def _rm(p):
    try: os.unlink(p)
    except: pass

class TestValidApplication:
    def test_valid_passes(self):
        p = _tmp(VALID)
        try:
            r = read_and_validate_application(file_path=p)
            assert r["is_valid"] is True
        finally: _rm(p)

    def test_returns_data(self):
        p = _tmp(VALID)
        try:
            r = read_and_validate_application(file_path=p)
            assert r["data"]["applicant_name"] == "Priya Fernando"
        finally: _rm(p)

    def test_result_keys(self):
        p = _tmp(VALID)
        try:
            r = read_and_validate_application(file_path=p)
            for k in ("data","errors","is_valid","error_count","critical_count"):
                assert k in r
        finally: _rm(p)

class TestMissingFields:
    def test_missing_name(self):
        bad = {k:v for k,v in VALID.items() if k!="applicant_name"}
        p = _tmp(bad)
        try:
            r = read_and_validate_application(file_path=p)
            assert r["is_valid"] is False
        finally: _rm(p)

    def test_missing_income(self):
        bad = {k:v for k,v in VALID.items() if k!="annual_income"}
        p = _tmp(bad)
        try:
            r = read_and_validate_application(file_path=p)
            fields = [e["field"] for e in r["errors"]]
            assert "annual_income" in fields
        finally: _rm(p)

class TestRanges:
    def test_negative_income(self):
        bad = {**VALID, "annual_income": -1}
        p = _tmp(bad); r = read_and_validate_application(file_path=p); _rm(p)
        assert r["is_valid"] is False

    def test_credit_score_low(self):
        bad = {**VALID, "credit_score": 100}
        p = _tmp(bad); r = read_and_validate_application(file_path=p); _rm(p)
        assert r["is_valid"] is False

    def test_credit_score_high(self):
        bad = {**VALID, "credit_score": 999}
        p = _tmp(bad); r = read_and_validate_application(file_path=p); _rm(p)
        assert r["is_valid"] is False

class TestFileErrors:
    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            read_and_validate_application(file_path="nonexistent_xyz.json")

    def test_no_args_raises(self):
        with pytest.raises(ValueError):
            read_and_validate_application()
