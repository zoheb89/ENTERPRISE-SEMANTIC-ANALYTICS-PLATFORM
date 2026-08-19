
import pandas as pd
from prep_engine import profile_raw, prepare_raw_files, summary

def test_dirty_automotive_profile_detects_key_issues():
    raw = {
        "customers.csv": pd.DataFrame({
            " customer_id ": [" CUS-001 ", " CUS-001 "],
            "customer_name": ["Ananya Singh", "Ananya Singh"],
            "email": ["a@example.com", "a@example.com"],
            "phone": ["+91 98765 43210", "+91 98765 43210"],
            "status": ["Active", "Active"],
        }),
        "service_orders.csv": pd.DataFrame({
            "service_order_id": ["SO-001","SO-002","SO-003","SO-004","SO-005","SO-006"],
            "service_date": ["2026-01-05","05/02/2026","2026-02-18","31-02-2026",None,"2026-03-15"],
            "labor_cost": ["$12,500.50","8,750","₹15,200","$5,000","10,250.00","not available"],
            "status": ["Closed","closed","OPEN","Pending","closed","Closed"],
        }),
        "vehicles.csv": pd.DataFrame({
            "vehicle_id": ["VEH-001","VEH-002"],
            "manufacture_year": ["2022","20XX"],
            "active": ["Yes","TRUE"],
        }),
    }
    findings = profile_raw(raw)
    issues = " | ".join(f.issue for f in findings)
    assert ("Exact duplicate rows" in issues) or ("Duplicate rows after safe normalization" in issues)
    assert "Potential PII/PHI column: email" in issues
    assert "Potential PII/PHI column: phone" in issues
    assert "Invalid date/time values: service_date" in issues
    assert "Currency-formatted numeric values: labor_cost" in issues
    assert "Non-numeric values in numeric candidate: labor_cost" in issues
    assert "Invalid year values: manufacture_year" in issues
    assert "Inconsistent boolean representations: active" in issues
    assert len(findings) >= 8

def test_preparation_is_deterministic_and_removes_only_duplicates():
    raw = {"t.csv": pd.DataFrame({
        " customer_id ": [" C1 ", "C1"],
        "amount": ["$1,000", "$1,000"],
        "active": ["Yes", "Yes"],
    })}
    findings = profile_raw(raw)
    cleaned, actions = prepare_raw_files(raw, findings)
    assert len(cleaned["t.csv"]) == 1
    assert "customer_id" in cleaned["t.csv"].columns
    assert cleaned["t.csv"]["amount"].iloc[0] == 1000
    assert bool(cleaned["t.csv"]["active"].iloc[0]) is True
    assert any("Removed exact duplicates" in a["action"] for a in actions)
