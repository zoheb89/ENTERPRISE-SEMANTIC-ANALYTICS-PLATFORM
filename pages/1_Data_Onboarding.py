
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from theme import inject_base_css, render_sidebar_brand, page_header
from data_engine import load_uploaded_files, prepare_files
from connector_engine import (
    ConnectorError,
    connect_cloud,
    connect_database,
    connect_databricks,
    connect_rest_api,
)

inject_base_css()
render_sidebar_brand()

page_header(
    "Data Onboarding",
    "Connect any supported source and send it through the same metadata-driven semantic engine",
)

DEMO_DATA_DIR = Path(__file__).resolve().parent.parent / "demo_datasets"

for key, default in {
    "domain_name": "",
    "uploaded_files": {},
    "model": None,
    "stage": "upload",
    "llm_suggestion_count": 0,
    "onboarding_source_type": "File",
    "onboarding_source": "Upload files",
    "onboarding_sample_domain": "Healthcare",
    "onboarding_upload_domain": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


@st.cache_data(show_spinner=False)
def available_demo_domains() -> list[str]:
    if not DEMO_DATA_DIR.exists():
        return []
    return sorted(
        p.name
        for p in DEMO_DATA_DIR.iterdir()
        if p.is_dir()
        and not p.name.startswith(".")
        and any(
            f.is_file() and f.suffix.lower() == ".csv"
            for f in p.iterdir()
        )
    )


@st.cache_data(show_spinner=False)
def load_sample_domain(choice: str) -> dict[str, pd.DataFrame]:
    domain_dir = DEMO_DATA_DIR / choice.lower()
    if not domain_dir.exists():
        raise ValueError(f"Demo domain '{choice}' is not available.")

    files = {
        path.name: pd.read_csv(path)
        for path in sorted(domain_dir.glob("*.csv"))
    }
    if not files:
        raise ValueError(f"Demo domain '{choice}' contains no CSV files.")
    return prepare_files(files)


def reset_current_model():
    st.session_state.model = None
    st.session_state.uploaded_files = {}
    st.session_state.llm_suggestion_count = 0
    st.session_state.stage = "upload"


def load_databricks_defaults():
    return {
        "host": st.secrets.get("DATABRICKS_HOST", ""),
        "token": st.secrets.get("DATABRICKS_TOKEN", ""),
        "warehouse_id": st.secrets.get("DATABRICKS_WAREHOUSE_ID", ""),
        "catalog": st.secrets.get("DATABRICKS_CATALOG", "invent_semantic_platform"),
        "schema": "",
    }


with st.container(border=True):
    st.markdown("### Choose a data source")

    source_type = st.radio(
        "Source type",
        ["File", "Database", "API", "Cloud Storage", "Databricks / Unity Catalog", "Sample Domain"],
        key="onboarding_source_type",
        horizontal=True,
    )

    files: dict[str, pd.DataFrame] = {}
    selected_domain = ""
    source_description = ""

    # ------------------------------------------------------------------
    # FILE
    # ------------------------------------------------------------------
    if source_type == "File":
        selected_domain = st.text_input(
            "Domain name",
            key="onboarding_upload_domain",
            placeholder="e.g. Finance, Manufacturing, Customer Analytics",
        ).strip()

        uploaded = st.file_uploader(
            "Upload tabular data",
            type=["csv", "xlsx", "xls", "json", "parquet"],
            accept_multiple_files=True,
            key="onboarding_uploaded_files",
            help="CSV, Excel, JSON and Parquet are normalized into the common INVENT table contract.",
        )

        if uploaded:
            try:
                files = prepare_files(load_uploaded_files(uploaded))
                source_description = f"File upload: {len(files)} table(s)"
                st.success(
                    f"{len(files)} file(s) loaded: {', '.join(files.keys())}"
                )
            except Exception as exc:
                st.error(f"Couldn't load the selected files: {exc}")

    # ------------------------------------------------------------------
    # SAMPLE
    # ------------------------------------------------------------------
    elif source_type == "Sample Domain":
        domains = available_demo_domains()
        if not domains:
            st.error("No bundled demo domains are available.")
            st.stop()

        sample_choice = st.selectbox(
            "Sample domain",
            domains,
            key="onboarding_sample_domain",
        )
        selected_domain = sample_choice
        files = load_sample_domain(sample_choice)
        source_description = f"Bundled sample: {sample_choice}"

        st.info(
            f"Sample domain selected: **{sample_choice}** · "
            f"{len(files)} table(s) ready"
        )
        st.caption(
            "Sample data is only a regression/demo path. "
            "All other source types use the connector layer."
        )

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    elif source_type == "Database":
        selected_domain = st.text_input(
            "Domain name",
            key="db_domain",
            placeholder="e.g. Finance",
        ).strip()

        db_type = st.selectbox(
            "Database",
            ["PostgreSQL", "MySQL", "SQL Server", "SQLite"],
            key="db_type",
        )

        if db_type == "SQLite":
            sqlite_file = st.file_uploader(
                "SQLite database file",
                type=["db", "sqlite", "sqlite3"],
                key="sqlite_file",
            )
            sqlite_path = ""
            if sqlite_file:
                temp_dir = Path(st.session_state.get("_connector_tmp", "/tmp/invent_connectors"))
                temp_dir.mkdir(parents=True, exist_ok=True)
                sqlite_path = str(temp_dir / sqlite_file.name)
                Path(sqlite_path).write_bytes(sqlite_file.getvalue())

            if st.button("Connect & Discover Tables", key="sqlite_connect"):
                if not sqlite_path:
                    st.error("Upload a SQLite database first.")
                else:
                    try:
                        result = connect_database(
                            "sqlite",
                            sqlite_path=sqlite_path,
                        )
                        files = result.tables
                        st.session_state.connector_preview = result
                        st.success(
                            f"Connected · {len(files)} table(s) discovered"
                        )
                    except Exception as exc:
                        st.error(str(exc))
        else:
            c1, c2 = st.columns(2)
            with c1:
                db_host = st.text_input("Host", key="db_host")
                db_port = st.text_input("Port", key="db_port")
                db_name = st.text_input("Database", key="db_name")
            with c2:
                db_user = st.text_input("Username", key="db_user")
                db_password = st.text_input("Password", type="password", key="db_password")
                db_schema = st.text_input("Schema (optional)", key="db_schema")

            st.caption(
                "Credentials are used only for the connection and are not written "
                "to the semantic registry."
            )

            if st.button("Connect & Discover Tables", key="database_connect"):
                try:
                    result = connect_database(
                        db_type,
                        host=db_host,
                        port=db_port,
                        database=db_name,
                        username=db_user,
                        password=db_password,
                        schema=db_schema,
                    )
                    st.session_state.connector_preview = result
                    st.success(
                        f"Connected to {result.description} · "
                        f"{len(result.tables)} table(s) discovered"
                    )
                except Exception as exc:
                    st.error(str(exc))

        preview = st.session_state.get("connector_preview")
        if preview and preview.source_type in {"Postgresql", "Mysql", "Sql Server", "SQLite"}:
            discovered = preview.tables
            selected_tables = st.multiselect(
                "Tables to onboard",
                list(discovered.keys()),
                default=list(discovered.keys()),
                key="db_selected_tables",
            )
            files = {
                name: discovered[name]
                for name in selected_tables
            }
            source_description = preview.description

    # ------------------------------------------------------------------
    # REST API
    # ------------------------------------------------------------------
    elif source_type == "API":
        selected_domain = st.text_input(
            "Domain name",
            key="api_domain",
            placeholder="e.g. Customer Operations",
        ).strip()

        url = st.text_input(
            "REST API URL",
            key="api_url",
            placeholder="https://api.example.com/v1/domain-data",
        )
        method = st.selectbox(
            "Method",
            ["GET", "POST"],
            key="api_method",
        )
        # Streamlit's st.text_area does not support type="password".
        # Keep this as a multiline JSON field because APIs may require
        # multiple headers. Do not log or display the entered header value.
        headers = st.text_area(
            "Headers JSON (optional)",
            key="api_headers",
            placeholder='{"Authorization":"Bearer <token>"}',
            help="Optional HTTP headers as JSON. Credentials are used only for the request and are not displayed by INVENT.",
        )
        body = st.text_area(
            "Request body JSON (POST only, optional)",
            key="api_body",
            placeholder='{"limit":1000}',
        )

        if st.button("Connect & Fetch API Data", key="api_connect"):
            try:
                result = connect_rest_api(
                    url=url,
                    method=method,
                    headers_json=headers,
                    body_json=body,
                )
                st.session_state.connector_preview = result
                st.success(
                    f"API connected · {len(result.tables)} table(s) detected"
                )
            except Exception as exc:
                st.error(str(exc))

        preview = st.session_state.get("connector_preview")
        if preview and preview.source_type == "REST API":
            files = preview.tables
            source_description = preview.description
            st.caption(
                f"Detected tables: {', '.join(files.keys())}"
            )

    # ------------------------------------------------------------------
    # CLOUD
    # ------------------------------------------------------------------
    elif source_type == "Cloud Storage":
        selected_domain = st.text_input(
            "Domain name",
            key="cloud_domain",
            placeholder="e.g. Retail",
        ).strip()

        protocol = st.selectbox(
            "Cloud",
            ["s3", "abfs"],
            key="cloud_protocol",
            format_func=lambda x: "Amazon S3" if x == "s3" else "Azure Data Lake Storage Gen2",
        )
        path = st.text_input(
            "Path",
            key="cloud_path",
            placeholder="s3://bucket/prefix/ or abfs://container@account.dfs.core.windows.net/prefix/",
        )

        st.caption(
            "For production, keep cloud credentials in Streamlit Secrets or "
            "the deployment's workload identity. INVENT does not store them "
            "in the semantic model."
        )

        if st.button("Connect & Discover Files", key="cloud_connect"):
            try:
                options = {}
                secret_name = "INVENT_CLOUD_STORAGE_OPTIONS"
                if secret_name in st.secrets:
                    raw = st.secrets[secret_name]
                    options = json.loads(raw) if isinstance(raw, str) else dict(raw)

                result = connect_cloud(
                    protocol=protocol,
                    path=path,
                    storage_options=options,
                )
                st.session_state.connector_preview = result
                st.success(
                    f"Cloud source connected · {len(result.tables)} table(s) detected"
                )
            except Exception as exc:
                st.error(str(exc))

        preview = st.session_state.get("connector_preview")
        if preview and preview.source_type == "Cloud Storage":
            files = preview.tables
            source_description = preview.description
            st.caption(f"Detected tables/files: {', '.join(files.keys())}")

    # ------------------------------------------------------------------
    # DATABRICKS / UNITY CATALOG
    # ------------------------------------------------------------------
    else:
        selected_domain = st.text_input(
            "Domain name",
            key="dbc_domain",
            placeholder="e.g. Existing Customer Domain",
        ).strip()

        defaults = load_databricks_defaults()

        host = st.text_input(
            "Databricks Host",
            value=defaults["host"],
            key="onboard_dbx_host",
        )
        token = st.text_input(
            "Databricks Token",
            value=defaults["token"],
            type="password",
            key="onboard_dbx_token",
        )
        warehouse = st.text_input(
            "SQL Warehouse ID",
            value=defaults["warehouse_id"],
            key="onboard_dbx_warehouse",
        )

        c1, c2 = st.columns(2)
        with c1:
            catalog = st.text_input(
                "Catalog",
                value=defaults["catalog"],
                key="onboard_dbx_catalog",
            )
        with c2:
            schema = st.text_input(
                "Schema",
                key="onboard_dbx_schema",
                placeholder="source_schema",
            )

        if st.button("Connect & Discover Tables", key="dbx_connect"):
            try:
                result = connect_databricks(
                    host=host,
                    token=token,
                    warehouse_id=warehouse,
                    catalog=catalog,
                    schema=schema,
                    tables=[],
                )
                st.session_state.connector_preview = result
                st.success(
                    f"Connected to {result.description} · "
                    f"{len(result.tables)} table(s) discovered"
                )
            except Exception as exc:
                st.error(str(exc))

        preview = st.session_state.get("connector_preview")
        if preview and preview.source_type == "Databricks / Unity Catalog":
            discovered = preview.tables
            selected_tables = st.multiselect(
                "Tables to onboard",
                list(discovered.keys()),
                default=list(discovered.keys()),
                key="dbx_selected_tables",
            )
            files = {
                name: discovered[name]
                for name in selected_tables
            }
            source_description = preview.description

    if files:
        st.divider()
        st.markdown(
            f"**Source ready:** `{source_description}` · "
            f"**{len(files)} table(s)**"
        )

        for name, df in files.items():
            st.caption(
                f"{name} · {len(df):,} rows · {len(df.columns)} columns"
            )

    can_analyze = bool(files and selected_domain)

    st.divider()

    go = st.button(
        "Analyze Connected Data →",
        type="primary",
        disabled=not can_analyze,
        key="analyze_current_onboarding",
    )

if go:
    st.session_state.domain_name = selected_domain
    st.session_state.model = None
    st.session_state.llm_suggestion_count = 0
    st.session_state.uploaded_files = {
        name: dataframe.copy()
        for name, dataframe in files.items()
    }
    st.session_state.source_description = source_description
    st.session_state.source_type = source_type
    st.session_state.stage = "processing"

    st.switch_page("pages/2_AI_Analysis.py")
