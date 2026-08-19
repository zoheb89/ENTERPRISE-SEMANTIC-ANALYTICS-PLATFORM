
import streamlit as st
import pandas as pd
from theme import inject_base_css, render_sidebar_brand, page_header, navigate_to
from registry import list_domains
from dashboard_engine import (
    recommend_dashboard, query_dashboard_kpis, query_metric_view,
    query_distinct_dimension, dashboard_status, build_narrative
)
import security_fabric as security

inject_base_css()
render_sidebar_brand()
page_header(
    "AI/BI Dashboard",
    "Generate and execute an executive dashboard from the governed semantic model."
)

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
metric_view=getattr(entry,"metric_view",None) or getattr(entry,"metric_view_name",None)
if not metric_view:
    # Registry versions may expose the canonical name differently.
    metric_view=f"{entry.catalog}.{entry.schema}.mv_domain"

measures=list(entry.measures or [])
dimensions=[str(x) for x in (entry.dimensions or []) if str(x).lower()!="fact_type"]

st.markdown("### Governed dashboard source")
a,b,c,d=st.columns(4)
a.metric("Published Measures",len(measures))
b.metric("Dimensions",len(dimensions))
c.metric("Fact Tables",len(getattr(entry,"fact_tables",[]) or [getattr(entry,"fact_table","")]))
status=dashboard_status(metric_view)
d.metric("Metric View", "READY" if status["ready"] else "ERROR")

st.caption(f"All dashboard results are queried from the canonical Metric View: `{metric_view}`")
if not status["ready"]:
    st.error("The published Metric View could not be queried. Check Databricks permissions, warehouse availability, and the published Metric View definition.")
    st.code(status["message"])
    st.stop()

# ---- Dashboard recommendations ----
st.markdown("### 1. AI dashboard generation")
class M: pass
m=M()
m.metrics=[type("Metric",(),{"name":x})() for x in measures]
m.dimensions=dimensions
recs=recommend_dashboard(m)
kpis=[r for r in recs if r.visualization=="KPI"]
charts=[r for r in recs if r.visualization!="KPI"]

with st.container(border=True):
    st.markdown("**Dashboard blueprint generated from published semantic metadata**")
    st.write("Review the proposed KPIs and visualizations, then execute them against the governed Metric View.")
    if st.button("Generate Governed Dashboard",type="primary",use_container_width=True):
        st.session_state.dashboard_generated=True

if not st.session_state.get("dashboard_generated"):
    st.markdown("### Recommended visualizations")
    if charts:
        st.dataframe(pd.DataFrame([{
            "Visualization":r.visualization,"Title":r.title,"Measure":r.measure,
            "Dimension":r.dimension,"Why":r.rationale
        } for r in charts]),use_container_width=True,hide_index=True)
    st.info("Click **Generate Governed Dashboard** to execute the blueprint and render live KPIs and charts.")
    st.stop()

# ---- Interactive filters ----
st.markdown("### 2. Dashboard filters")
filter_dims=[]
for d in dimensions:
    dl=d.lower()
    if any(x in dl for x in ("date","timestamp","time","month")):
        continue
    # Avoid obviously high-cardinality IDs in the default filter strip.
    if dl.endswith("_id") or dl=="id":
        continue
    filter_dims.append(d)
filter_dims=filter_dims[:4]

active_filters={}
if filter_dims:
    fcols=st.columns(len(filter_dims))
    for i,d in enumerate(filter_dims):
        try:
            vals=query_distinct_dimension(metric_view,d,limit=100)
        except Exception:
            vals=[]
        options=["All"]+vals
        active_filters[d]=fcols[i].selectbox(d.replace("_"," ").title(),options,key=f"dash_filter_{d}")
else:
    st.caption("No low-cardinality governed dimensions were identified for the default filter strip.")

# ---- KPI execution ----
st.markdown("### 3. Executive KPIs")
try:
    kpi_df=query_dashboard_kpis(metric_view,measures[:4],active_filters)
    if kpi_df.empty:
        st.warning("No governed KPI results were returned for the selected filters.")
        kpi_values={}
    else:
        row=kpi_df.iloc[0].to_dict()
        kpi_values=row
        cols=st.columns(min(4,max(1,len(row))))
        for i,(name,value) in enumerate(row.items()):
            if pd.isna(value):
                display="—"
            elif isinstance(value,(int,float)):
                display=f"{value:,.2f}" if float(value)%1 else f"{value:,.0f}"
            else:
                display=str(value)
            cols[i].metric(str(name).replace("_"," ").title(),display)
except Exception as exc:
    st.error("KPI execution failed against the governed Metric View.")
    st.code(str(exc))
    st.stop()

# ---- Visualization execution ----
st.markdown("### 4. Interactive visualizations")
executed=0
for r in charts[:6]:
    try:
        df=query_metric_view(metric_view,r.measure,r.dimension,active_filters,limit=20)
        if df.empty:
            continue
        df=df.rename(columns={"dimension_value":r.dimension,"metric_value":r.measure})
        st.markdown(f"**{r.title}**")
        if r.visualization=="Line":
            # Native Streamlit chart keeps this dependency-light and interactive.
            st.line_chart(df.set_index(r.dimension)[r.measure])
        else:
            st.bar_chart(df.set_index(r.dimension)[r.measure])
        st.caption(f"Source: governed Metric View • {r.measure} grouped by {r.dimension}")
        executed += 1
    except Exception as exc:
        st.warning(f"{r.title} could not be rendered: {exc}")

if executed==0:
    st.warning("No visualizations returned data for the selected filters.")

# ---- Narrative ----
st.markdown("### 5. Governed narrative insight")
st.info(build_narrative(kpi_values,active_filters))

# ---- Dashboard lifecycle ----
st.markdown("### 6. Dashboard lifecycle")
with st.container(border=True):
    st.markdown("""
**Generated → Queried → Rendered → Reviewed → Publish**

The dashboard is generated from published semantic metadata, but its values are obtained by executing queries against the canonical Metric View. Raw uploaded files are not used as the dashboard's execution source.
""")
    st.caption("Databricks AI/BI publication can be added as the final lifecycle step using the Databricks Lakeview dashboard API; publishing requires appropriate workspace/dashboard and data permissions.")

st.divider()
c1,c2=st.columns(2)
with c1:
    if st.button("← Analytics",use_container_width=True):
        navigate_to("Analytics")
with c2:
    if st.button("Back to Semantic Model →",use_container_width=True):
        navigate_to("Business Model")
