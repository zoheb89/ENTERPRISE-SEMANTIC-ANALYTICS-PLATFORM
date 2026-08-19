
import pandas as pd
from prep_engine import profile_raw, prepare_raw_files

def test_raw_data_prep():
    raw={"service_orders.csv":pd.DataFrame({
        " customer id ": [" C1 "]*12,
        "amount": ["$1,000"]*12,
        "service_date": ["2026-01-01"]*12,
        "notes": [" ok "]*12,
    })}
    findings=profile_raw(raw)
    assert findings
    cleaned, applied=prepare_raw_files(raw,findings)
    assert len(cleaned["service_orders.csv"]) == 1
    assert "customer_id" in cleaned["service_orders.csv"].columns
    assert cleaned["service_orders.csv"]["amount"].dtype.kind in "fi"
    assert applied
