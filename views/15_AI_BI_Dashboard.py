
import streamlit as st
import pandas as pd
from theme import inject_base_css, render_sidebar_brand, page_header, navigate_to
from registry import list_domains
from dashboard_engine import recommend_dashboard
import security_fabric as security

inject_base_css()
render_sidebar_brand()
page_header("AI/BI Dashboard", "Generate an executive KPI and visualization plan from the governed semantic model.")

if not security.is_configured():
    st.warning("Databricks is not configured. Publish a domain before generating its governed dashboard.")
    st.stop()

domains=list_domains()
if not domains:
    st.info("No published domains yet. Publish a semantic model first.")
    if st.button("Go to Data Onboarding →",type="primary"):
        navigate_to("Data Onboarding")
    st.stop()

names=[d.domain_name for d in domains]
active=st.selectbox("Active Domain",names,key="dashboard_domain_selector")
entry=next(d for d in domains if d.domain_name==active)
model=st.session_state.get("model")

st.markdown("### Dashboard intent")
c1,c2,c3=st.columns(3)
c1.metric("Published Measures",len(entry.measures or []))
c2.metric("Dimensions",len(entry.dimensions or []))
c3.metric("Fact Tables",len(getattr(entry,"fact_tables",[]) or [entry.fact_table]))

st.info("Dashboard recommendations are metadata-driven. Review the proposed KPIs and visuals before publishing a production dashboard.")

if model and model.domain_name==active:
    recs=recommend_dashboard(model)
else:
    # Build a lightweight model-like object from registry metadata.
    class M: pass
    m=M(); m.metrics=[type("Metric",(),{"name":x})() for x in (entry.measures or [])]; m.dimensions=entry.dimensions or []
    recs=recommend_dashboard(m)

kpis=[r for r in recs if r.visualization=="KPI"]
charts=[r for r in recs if r.visualization!="KPI"]

st.markdown("### Recommended executive KPIs")
cols=st.columns(min(4,max(1,len(kpis))))
for i,r in enumerate(kpis[:4]):
    cols[i].metric(r.title,"Governed measure")
    cols[i].caption(r.rationale)

st.markdown("### Recommended visualizations")
if charts:
    rows=[{"Visualization":r.visualization,"Title":r.title,"Measure":r.measure,"Dimension":r.dimension,"Why":r.rationale} for r in charts]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
else:
    st.caption("No dimension/measure combinations are currently available for chart recommendations.")

st.markdown("### Dashboard generation roadmap")
st.success("Current build: KPI + visualization recommendations are generated from published semantic metadata. Next execution layer: query the governed Metric View, render interactive charts, filters and narrative insights, then optionally publish the dashboard to Databricks AI/BI.")
