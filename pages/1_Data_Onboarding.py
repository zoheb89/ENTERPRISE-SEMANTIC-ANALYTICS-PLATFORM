import streamlit as st
import pandas as pd
import numpy as np

from theme import inject_base_css, render_sidebar_brand, page_header


inject_base_css()
render_sidebar_brand()

page_header(
    "Data Onboarding",
    "Upload files, or try a sample domain — no Databricks knowledge required",
)


# =============================================================================
# SESSION STATE
# =============================================================================

if "domain_name" not in st.session_state:
    st.session_state.domain_name = ""

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}

if "model" not in st.session_state:
    st.session_state.model = None

if "stage" not in st.session_state:
    st.session_state.stage = "upload"

if "llm_suggestion_count" not in st.session_state:
    st.session_state.llm_suggestion_count = 0


# =============================================================================
# SAMPLE DATA
# =============================================================================

def load_sample_domain(choice: str) -> dict:
    """
    Generate deterministic sample data for the selected domain.

    IMPORTANT:
    The selected sample domain is authoritative. The previous domain
    must never be reused when the user changes the sample selector.
    """

    rng = np.random.default_rng(11)

    if choice == "Healthcare":
        hospitals = pd.DataFrame(
            {
                "hospital_id": range(1, 6),
                "hospital_name": [
                    f"Hospital {c}" for c in "ABCDE"
                ],
            }
        )

        doctors = pd.DataFrame(
            {
                "doctor_id": range(1, 26),
                "doctor_name": [
                    f"Dr. {i}" for i in range(1, 26)
                ],
                "hospital_id": rng.integers(
                    1,
                    6,
                    25,
                ),
            }
        )

        patients = pd.DataFrame(
            {
                "patient_id": range(1, 201),
                "patient_name": [
                    f"Patient {i}" for i in range(1, 201)
                ],
            }
        )

        encounters = pd.DataFrame(
            {
                "encounter_id": range(1, 601),
                "patient_id": rng.integers(
                    1,
                    201,
                    600,
                ),
                "doctor_id": rng.integers(
                    1,
                    26,
                    600,
                ),
                "heart_rate": rng.integers(
                    60,
                    130,
                    600,
                ),
                "length_of_stay_days": rng.integers(
                    1,
                    12,
                    600,
                ),
            }
        )

        return {
            "Hospitals.csv": hospitals,
            "Doctors.csv": doctors,
            "Patients.csv": patients,
            "Encounters.csv": encounters,
        }

    if choice == "Finance":
        dept = pd.DataFrame(
            {
                "department_id": range(1, 8),
                "department_name": [
                    "Sales",
                    "Marketing",
                    "Engineering",
                    "Ops",
                    "Finance",
                    "HR",
                    "Legal",
                ],
            }
        )

        cc = pd.DataFrame(
            {
                "cost_center_id": range(1, 8),
                "cost_center_name": [
                    f"CC-{i}" for i in range(1, 8)
                ],
                "department_id": range(1, 8),
            }
        )

        gl = pd.DataFrame(
            {
                "gl_id": range(1, 501),
                "cost_center_id": rng.integers(
                    1,
                    8,
                    500,
                ),
                "expense_amount": rng.uniform(
                    500,
                    50000,
                    500,
                ).round(2),
                "revenue_amount": rng.uniform(
                    0,
                    80000,
                    500,
                ).round(2),
            }
        )

        return {
            "Department.csv": dept,
            "CostCenter.csv": cc,
            "GL.csv": gl,
        }

    if choice == "Retail":
        stores = pd.DataFrame(
            {
                "store_id": range(1, 11),
                "store_name": [
                    f"Store {i}" for i in range(1, 11)
                ],
            }
        )

        products = pd.DataFrame(
            {
                "product_id": range(1, 31),
                "product_name": [
                    f"Product {i}" for i in range(1, 31)
                ],
            }
        )

        customers = pd.DataFrame(
            {
                "customer_id": range(1, 301),
                "customer_name": [
                    f"Customer {i}" for i in range(1, 301)
                ],
            }
        )

        orders = pd.DataFrame(
            {
                "order_id": range(1, 1001),
                "customer_id": rng.integers(
                    1,
                    301,
                    1000,
                ),
                "product_id": rng.integers(
                    1,
                    31,
                    1000,
                ),
                "store_id": rng.integers(
                    1,
                    11,
                    1000,
                ),
                "order_value": rng.uniform(
                    15,
                    800,
                    1000,
                ).round(2),
                "quantity": rng.integers(
                    1,
                    8,
                    1000,
                ),
            }
        )

        return {
            "Store.csv": stores,
            "Product.csv": products,
            "Customer.csv": customers,
            "Orders.csv": orders,
        }

    raise ValueError(
        f"Unsupported sample domain: {choice}"
    )


# =============================================================================
# RESET CURRENT MODEL
# =============================================================================

def reset_current_model():
    """
    Clear only the current in-progress semantic model.

    This does NOT delete anything from Databricks or the published registry.
    Previously published domains remain available for Analytics.
    """

    st.session_state.model = None
    st.session_state.uploaded_files = {}
    st.session_state.llm_suggestion_count = 0
    st.session_state.stage = "upload"


# =============================================================================
# DATA ONBOARDING
# =============================================================================

with st.container(border=True):

    st.markdown("**Domain name**")

    domain_input = st.text_input(
        "Domain name",
        value=st.session_state.domain_name,
        placeholder="e.g. Healthcare, Finance, Retail — any name",
        label_visibility="collapsed",
    )

    # For uploaded data, the user's entered domain is authoritative.
    st.session_state.domain_name = domain_input.strip()

    st.markdown("**Choose a data source**")

    source = st.radio(
        "Source",
        [
            "Upload files",
            "Try a sample domain",
        ],
        label_visibility="collapsed",
        horizontal=True,
    )

    files = {}

    # -------------------------------------------------------------------------
    # USER UPLOAD
    # -------------------------------------------------------------------------

    if source == "Upload files":

        uploaded = st.file_uploader(
            "Upload CSV or Excel files",
            type=[
                "csv",
                "xlsx",
                "xls",
            ],
            accept_multiple_files=True,
        )

        if uploaded:

            for f in uploaded:

                try:

                    if f.name.lower().endswith(
                        ".csv"
                    ):
                        files[f.name] = pd.read_csv(f)
                    else:
                        files[f.name] = pd.read_excel(f)

                except Exception as exc:

                    st.error(
                        f"Couldn't read {f.name}: {exc}"
                    )

    # -------------------------------------------------------------------------
    # SAMPLE DOMAIN
    # -------------------------------------------------------------------------

    else:

        sample_choice = st.selectbox(
            "Sample domain",
            [
                "Healthcare",
                "Finance",
                "Retail",
            ],
            key="sample_domain_choice",
        )

        # CRITICAL FIX:
        #
        # Previously this was:
        #
        #     if not st.session_state.domain_name:
        #         st.session_state.domain_name = sample_choice
        #
        # That meant once Healthcare was selected, changing the sample selector
        # to Finance or Retail did NOT change domain_name.
        #
        # The selected sample must always drive the domain.
        st.session_state.domain_name = sample_choice

        files = load_sample_domain(
            sample_choice
        )

        st.caption(
            f"{len(files)} sample tables ready: "
            f"{', '.join(files.keys())}"
        )

        st.info(
            f"Sample domain selected: **{sample_choice}**"
        )


    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )

    go = st.button(
        "Analyze My Data →",
        type="primary",
        disabled=not (
            files
            and bool(
                st.session_state.domain_name
            )
        ),
    )

    if (
        not st.session_state.domain_name
        and files
    ):
        st.caption(
            "Enter a domain name above to continue."
        )


# =============================================================================
# START ANALYSIS
# =============================================================================

if go:

    # -------------------------------------------------------------------------
    # CRITICAL FIX:
    #
    # Never allow the previous domain's semantic model to survive into the
    # next analysis run.
    #
    # The model is rebuilt entirely from the files selected in THIS run.
    # -------------------------------------------------------------------------

    st.session_state.model = None
    st.session_state.llm_suggestion_count = 0

    # Make a clean copy of the current files.
    st.session_state.uploaded_files = {
        name: dataframe.copy()
        for name, dataframe in files.items()
    }

    # Keep the current domain exactly as selected.
    st.session_state.domain_name = (
        st.session_state.domain_name.strip()
    )

    st.session_state.stage = "processing"

    st.switch_page(
        "pages/2_AI_Analysis.py"
    )
