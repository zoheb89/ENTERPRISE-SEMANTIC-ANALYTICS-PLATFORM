
import streamlit as st
import pandas as pd
from theme import inject_base_css, render_sidebar_brand, page_header, navigate_to
from prep_engine import profile_raw, prepare_raw_files, summary

inject_base_css()
render_sidebar_brand()
page_header("Data Preparation", "Profile raw data, identify quality issues, preview safe cleansing actions, then continue to semantic analysis.")

raw = st.session_state.get("raw_uploaded_files") or st.session_state.get("uploaded_files") or {}
if not raw:
    st.info("No source data loaded. Start with Data Onboarding.")
    if st.button("← Data Onboarding", type="primary"):
        navigate_to("Data Onboarding")
    st.stop()

findings = profile_raw(raw)
s = summary(raw, findings)
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Tables",s["tables"]); c2.metric("Rows",f"{s['rows']:,}"); c3.metric("Columns",s["columns"])
c4.metric("Quality Findings",s["findings"]); c5.metric("Warnings",s["warnings"])

st.markdown("### Raw-data quality profile")
st.caption("DataPrepAI does not assume the source is clean. It profiles the source first and makes explainable, deterministic recommendations.")

if findings:
    rows=[{
        "Table":f.table,"Issue":f.issue,"Severity":f.severity.title(),
        "Affected Rows":f.affected_rows,"Recommendation":f.recommendation
    } for f in findings]
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
else:
    st.success("No material preparation findings detected in the current source.")

with st.container(border=True):
    st.markdown("### Preparation policy")
    st.info("Safe actions are deterministic and previewable. DataPrepAI does not invent business values, silently delete non-duplicate records, or auto-approve semantic changes.")
    col1,col2=st.columns(2)
    with col1:
        if st.button("Preview Cleansing",use_container_width=True):
            cleaned, applied=prepare_raw_files(raw,findings)
            st.session_state.prepared_preview=cleaned
            st.session_state.prep_actions=applied
    with col2:
        if st.button("Apply Safe Cleansing",type="primary",use_container_width=True):
            cleaned, applied=prepare_raw_files(raw,findings)
            st.session_state.uploaded_files=cleaned
            st.session_state.prep_actions=applied
            st.session_state.data_prep_approved=True
            st.success(f"Applied {len(applied)} deterministic preparation actions. Semantic analysis will use the prepared data.")

if st.session_state.get("prep_actions"):
    with st.container(border=True):
        st.markdown("### Applied preparation actions")
        st.dataframe(pd.DataFrame(st.session_state.prep_actions),use_container_width=True,hide_index=True)

if st.session_state.get("prepared_preview"):
    with st.container(border=True):
        st.markdown("### Before / after preview")
        for name in list(raw)[:5]:
            a=raw[name].head(5); b=st.session_state.prepared_preview[name].head(5)
            st.markdown(f"**{name}**")
            left,right=st.columns(2)
            with left: st.caption("RAW"); st.dataframe(a,use_container_width=True,hide_index=True)
            with right: st.caption("PREPARED"); st.dataframe(b,use_container_width=True,hide_index=True)

st.divider()
c1,c2=st.columns(2)
with c1:
    if st.button("← Data Onboarding",use_container_width=True):
        navigate_to("Data Onboarding")
with c2:
    ready = bool(st.session_state.get("uploaded_files"))
    if st.button("Run Semantic AI Analysis →",type="primary",use_container_width=True,disabled=not ready):
        navigate_to("AI Analysis")
