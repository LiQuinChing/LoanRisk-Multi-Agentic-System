import sqlite3
import pytest
from tools.tool3_fraud_db_query import query_fraud_database, _calculate_fraud_score

@pytest.fixture()
def test_db(tmp_path):
    db = str(tmp_path / "test.db")
    conn = sqlite3.connect(db)
    cur  = conn.cursor()
    cur.execute("CREATE TABLE blacklisted_national_ids(id INTEGER PRIMARY KEY,national_id TEXT UNIQUE,reason TEXT,case_number TEXT)")
    cur.execute("CREATE TABLE blacklisted_names(id INTEGER PRIMARY KEY,full_name TEXT UNIQUE,reason TEXT,case_number TEXT)")
    cur.execute("CREATE TABLE blacklisted_addresses(id INTEGER PRIMARY KEY,address_fragment TEXT UNIQUE,reason TEXT)")
    cur.execute("CREATE TABLE fraud_patterns(id INTEGER PRIMARY KEY,pattern_type TEXT,description TEXT,loan_to_income_min REAL,loan_to_income_max REAL,risk_weight REAL)")
    cur.execute("CREATE TABLE suspicious_employers(id INTEGER PRIMARY KEY,employer_name TEXT UNIQUE,reason TEXT)")
    cur.execute("CREATE TABLE fraud_network(id INTEGER PRIMARY KEY,national_id TEXT,full_name TEXT,phone TEXT,network_id TEXT,role TEXT,notes TEXT)")
    cur.execute("INSERT INTO blacklisted_national_ids VALUES(NULL,'199012345V','Fraud','CID/001')")
    cur.execute("INSERT INTO blacklisted_names VALUES(NULL,'Ruwan Kumara Dissanayake','Fraud','CID/002')")
    cur.execute("INSERT INTO blacklisted_addresses VALUES(NULL,'PO Box 9999','Known fraud address')")
    cur.execute("INSERT INTO fraud_patterns VALUES(NULL,'loan_to_income','Extreme ratio',10.0,9999.0,0.9)")
    cur.execute("INSERT INTO suspicious_employers VALUES(NULL,'Cash in Hand','No formal record')")
    cur.execute("INSERT INTO fraud_network VALUES(NULL,'199012345V','Ruwan Kumara Dissanayake','0771234567','NET-001','Ring leader','Test')")
    conn.commit(); conn.close()
    return db

CLEAN = {"application_id":"T001","applicant_name":"Nimal Perera","national_id":"200099998V",
         "address":"15 Main Street, Colombo","annual_income":2400000,
         "loan_amount_requested":7000000,"property_value":12000000,"employment_status":"full_time",
         "employer_name":"Bank of Ceylon","years_employed":6,"credit_score":740,"existing_monthly_debt":12000}

class TestClean:
    def test_no_flags(self, test_db):
        r = query_fraud_database(CLEAN, db_path=test_db)
        assert r["flag_count"] == 0
    def test_zero_score(self, test_db):
        assert query_fraud_database(CLEAN, db_path=test_db)["fraud_score"] == 0.0
    def test_low_level(self, test_db):
        assert query_fraud_database(CLEAN, db_path=test_db)["risk_level"] == "LOW"
    def test_result_keys(self, test_db):
        r = query_fraud_database(CLEAN, db_path=test_db)
        for k in ("flags","flag_count","fraud_score","risk_level","nic_hit","name_hit","network_hit"):
            assert k in r

class TestNICBlacklist:
    def test_nic_hit(self, test_db):
        bad = {**CLEAN, "national_id": "199012345V"}
        r = query_fraud_database(bad, db_path=test_db)
        assert r["nic_hit"] is True
    def test_nic_flag_type(self, test_db):
        bad = {**CLEAN, "national_id": "199012345V"}
        types = [f["flag_type"] for f in query_fraud_database(bad, db_path=test_db)["flags"]]
        assert "blacklisted_national_id" in types

class TestNameBlacklist:
    def test_name_hit(self, test_db):
        bad = {**CLEAN, "applicant_name": "Ruwan Kumara Dissanayake"}
        r = query_fraud_database(bad, db_path=test_db)
        assert r["name_hit"] is True

class TestAddressBlacklist:
    def test_address_flagged(self, test_db):
        bad = {**CLEAN, "address": "Sent to PO Box 9999 Colombo"}
        types = [f["flag_type"] for f in query_fraud_database(bad, db_path=test_db)["flags"]]
        assert "blacklisted_address" in types

class TestLoanRatio:
    def test_extreme_ratio_flagged(self, test_db):
        bad = {**CLEAN, "annual_income":1000000, "loan_amount_requested":25000000}
        types = [f["flag_type"] for f in query_fraud_database(bad, db_path=test_db)["flags"]]
        assert "suspicious_loan_to_income_ratio" in types

class TestSpecialRules:
    def test_unemployed_flagged(self, test_db):
        bad = {**CLEAN, "employment_status":"unemployed"}
        types = [f["flag_type"] for f in query_fraud_database(bad, db_path=test_db)["flags"]]
        assert "unemployed_applicant" in types
    def test_low_credit_flagged(self, test_db):
        bad = {**CLEAN, "credit_score":400}
        types = [f["flag_type"] for f in query_fraud_database(bad, db_path=test_db)["flags"]]
        assert "very_low_credit_score" in types

class TestDBErrors:
    def test_missing_db(self):
        with pytest.raises(FileNotFoundError):
            query_fraud_database(CLEAN, db_path="nonexistent/fraud.db")

class TestScoreCalc:
    def test_no_flags(self):     assert _calculate_fraud_score([]) == 0.0
    def test_high_flag(self):    assert _calculate_fraud_score([{"weight":0.9}]) > 50
    def test_max_100(self):      assert _calculate_fraud_score([{"weight":0.9}]*5) <= 100
    def test_returns_float(self): assert isinstance(_calculate_fraud_score([{"weight":0.5}]), float)
