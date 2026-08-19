
import pandas as pd
from dashboard_engine import build_narrative, recommend_dashboard

def test_dashboard_recommendations_and_narrative():
    class M: pass
    M.metrics=[type("Metric",(),{"name":"total_cost"})(), type("Metric",(),{"name":"order_count"})()]
    M.dimensions=["dealer","service_date"]
    recs=recommend_dashboard(M)
    assert any(x.visualization=="KPI" for x in recs)
    assert any(x.visualization=="Bar" for x in recs)
    assert any(x.visualization=="Line" for x in recs)
    text=build_narrative({"total_cost":1184789.5,"order_count":130},{"dealer":"All"})
    assert "Total Cost" in text
    assert "1,184,789.50" in text
