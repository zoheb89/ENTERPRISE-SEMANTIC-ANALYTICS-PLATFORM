import streamlit as st
import pandas as pd
from data_engine import load_uploaded_files, prepare_files
import numpy as np

from theme import inject_base_css, render_sidebar_brand, page_header

inject_base_css()
render_sidebar_brand()

page_header("Data Onboarding", "Upload files, or try a sample domain — no Databricks knowledge required")

if "domain_name" not in st.session_state:
    st.session_state.domain_name = ""
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}


def load_sample_domain(choice: str) -> dict:
    rng = np.random.default_rng(11)
    if choice == "Healthcare":
        hospitals = pd.DataFrame({"hospital_id": range(1, 6), "hospital_name": [f"Hospital {c}" for c in "ABCDE"]})
        doctors = pd.DataFrame({"doctor_id": range(1, 26), "doctor_name": [f"Dr. {i}" for i in range(1, 26)], "hospital_id": rng.integers(1, 6, 25)})
        patients = pd.DataFrame({"patient_id": range(1, 201), "patient_name": [f"Patient {i}" for i in range(1, 201)]})
        encounters = pd.DataFrame({
            "encounter_id": range(1, 601), "patient_id": rng.integers(1, 201, 600),
            "doctor_id": rng.integers(1, 26, 600), "heart_rate": rng.integers(60, 130, 600),
            "length_of_stay_days": rng.integers(1, 12, 600),
        })
        return {"Hospitals.csv": hospitals, "Doctors.csv": doctors, "Patients.csv": patients, "Encounters.csv": encounters}
    elif choice == "Finance":
        dept = pd.DataFrame({"department_id": range(1, 8), "department_name": ["Sales", "Marketing", "Engineering", "Ops", "Finance", "HR", "Legal"]})
        cc = pd.DataFrame({"cost_center_id": range(1, 8), "cost_center_name": [f"CC-{i}" for i in range(1, 8)], "department_id": range(1, 8)})
        gl = pd.DataFrame({
            "gl_id": range(1, 501), "cost_center_id": rng.integers(1, 8, 500),
            "expense_amount": rng.uniform(500, 50000, 500).round(2), "revenue_amount": rng.uniform(0, 80000, 500).round(2),
        })
        return {"Department.csv": dept, "CostCenter.csv": cc, "GL.csv": gl}
    else:  # Retail
        stores = pd.DataFrame({"store_id": range(1, 11), "store_name": [f"Store {i}" for i in range(1, 11)]})
        products = pd.DataFrame({"product_id": range(1, 31), "product_name": [f"Product {i}" for i in range(1, 31)]})
        customers = pd.DataFrame({"customer_id": range(1, 301), "customer_name": [f"Customer {i}" for i in range(1, 301)]})
        orders = pd.DataFrame({
            "order_id": range(1, 1001), "customer_id": rng.integers(1, 301, 1000),
            "product_id": rng.integers(1, 31, 1000), "store_id": rng.integers(1, 11, 1000),
            "order_value": rng.uniform(15, 800, 1000).round(2), "quantity": rng.integers(1, 8, 1000),
        })
        return {"Store.csv": stores, "Product.csv": products, "Customer.csv": customers, "Orders.csv": orders}


with st.container(border=True):
    st.markdown("**Domain name**")
    st.session_state.domain_name = st.text_input(
        "Domain name", value=st.session_state.domain_name, placeholder="e.g. Healthcare, Finance, Retail — any name",
        label_visibility="collapsed",
    )

    st.markdown("**Choose a data source**")
    source = st.radio(
        "Source", ["Upload files", "Try a sample domain"], label_visibility="collapsed", horizontal=True,
    )

    files = {}
    if source == "Upload files":
        uploaded = st.file_uploader("Upload tabular data", type=["csv", "xlsx", "xls", "json", "parquet"], accept_multiple_files=True)
        if uploaded:
            try:
                files = prepare_files(load_uploaded_files(uploaded))
            except Exception as e:
                st.error(str(e))
    else:
        sample_choice = st.selectbox("Sample domain", ["Healthcare", "Finance", "Retail"])
        if not st.session_state.domain_name:
            st.session_state.domain_name = sample_choice
        files = load_sample_domain(sample_choice)
        st.caption(f"{len(files)} sample tables ready: {', '.join(files.keys())}")

    st.markdown("<br>", unsafe_allow_html=True)
    go = st.button("Analyze My Data →", type="primary", disabled=not (files and st.session_state.domain_name))
    if not st.session_state.domain_name and files:
        st.caption("Enter a domain name above to continue.")

if go:
    st.session_state.uploaded_files = files
    st.session_state.stage = "processing"
    st.switch_page("pages/2_AI_Analysis.py")
