
"""
INVENT connector layer.

Every connector returns the same contract:
    dict[str, pandas.DataFrame]

Credentials are consumed at runtime and are never written to the semantic
model or the persistent registry.
"""

from __future__ import annotations

import io
import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from data_engine import normalize_columns, prepare_files


class ConnectorError(RuntimeError):
    pass


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value).strip())
    return value.strip("_") or "table"


def _validate_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value or ""):
        raise ConnectorError(f"Invalid SQL identifier: {value!r}")
    return value


def _frames_from_json(payload: Any, name_prefix: str = "api") -> dict[str, pd.DataFrame]:
    if isinstance(payload, list):
        if not payload:
            return {f"{name_prefix}_data": pd.DataFrame()}
        return {f"{name_prefix}_data": pd.json_normalize(payload)}

    if isinstance(payload, dict):
        frames = {}
        # Common API shape: {"data": [...]}.
        if isinstance(payload.get("data"), list):
            frames[f"{name_prefix}_data"] = pd.json_normalize(payload["data"])

        # Also accept {"customers": [...], "orders": [...]}.
        for key, value in payload.items():
            if isinstance(value, list) and value and all(
                isinstance(item, dict) for item in value
            ):
                frames[_safe_name(key)] = pd.json_normalize(value)

        if frames:
            return frames

        # Single JSON object.
        return {f"{name_prefix}_data": pd.json_normalize(payload)}

    raise ConnectorError("REST response is not a JSON object or array.")


@dataclass
class ConnectorResult:
    source_type: str
    description: str
    tables: dict[str, pd.DataFrame]


def connect_database(
    db_type: str,
    *,
    host: str = "",
    port: str = "",
    database: str = "",
    username: str = "",
    password: str = "",
    schema: str = "",
    sqlite_path: str = "",
) -> ConnectorResult:
    db_type = db_type.strip().lower()

    if db_type == "sqlite":
        if not sqlite_path:
            raise ConnectorError("SQLite database path is required.")
        conn = sqlite3.connect(sqlite_path)
        try:
            tables_df = pd.read_sql_query(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name",
                conn,
            )
            tables = {}
            for table in tables_df["name"].tolist():
                ident = _validate_identifier(table)
                tables[table] = pd.read_sql_query(
                    f'SELECT * FROM "{ident}"',
                    conn,
                )
        finally:
            conn.close()

        return ConnectorResult(
            "SQLite",
            f"SQLite: {sqlite_path}",
            prepare_files(tables),
        )

    try:
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy.engine import URL
    except ImportError as exc:
        raise ConnectorError(
            "SQLAlchemy is not installed. Install the database connector "
            "dependencies from requirements.txt."
        ) from exc

    driver_names = {
        "postgresql": ("postgresql+psycopg2", port or "5432"),
        "mysql": ("mysql+pymysql", port or "3306"),
        "sql server": ("mssql+pyodbc", port or "1433"),
    }

    if db_type not in driver_names:
        raise ConnectorError(f"Unsupported database connector: {db_type}")

    drivername, default_port = driver_names[db_type]

    if db_type == "sql server":
        query = {
            "driver": "ODBC Driver 18 for SQL Server",
            "Encrypt": "yes",
            "TrustServerCertificate": "no",
        }
    else:
        query = {}

    database_url = URL.create(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=int(port or default_port),
        database=database,
        query=query,
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        future=True,
    )


    engine = create_engine(
        drivers[db_type],
        pool_pre_ping=True,
        future=True,
    )

    inspector = inspect(engine)
    table_names = inspector.get_table_names(schema=schema or None)

    if not table_names:
        raise ConnectorError(
            f"No tables were found in database '{database}'"
            + (f", schema '{schema}'." if schema else ".")
        )

    frames = {}
    with engine.connect() as connection:
        for table in table_names:
            # Identifier comes from SQLAlchemy inspection, not user input.
            qualified = (
                f'"{schema}"."{table}"'
                if schema
                else f'"{table}"'
            )
            frames[table] = pd.read_sql_query(
                text(f"SELECT * FROM {qualified}"),
                connection,
            )

    engine.dispose()

    return ConnectorResult(
        db_type.title(),
        f"{db_type.title()} database: {database}",
        prepare_files(frames),
    )


def connect_databricks(
    *,
    host: str,
    token: str,
    warehouse_id: str,
    catalog: str,
    schema: str,
    tables: list[str],
) -> ConnectorResult:
    if not all([host, token, warehouse_id, catalog, schema]):
        raise ConnectorError(
            "Databricks host, token, warehouse, catalog and schema are required."
        )

    try:
        from databricks import sql
    except ImportError as exc:
        raise ConnectorError(
            "databricks-sql-connector is not installed."
        ) from exc

    conn = sql.connect(
        server_hostname=host.replace("https://", "").rstrip("/"),
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        access_token=token,
        catalog=catalog,
        schema=schema,
    )

    try:
        available = pd.read_sql(
            "SHOW TABLES",
            conn,
        )

        selected = tables or available["tableName"].tolist()
        frames = {}

        for table in selected:
            _validate_identifier(table)
            frames[table] = pd.read_sql(
                f"SELECT * FROM `{table}`",
                conn,
            )
    finally:
        conn.close()

    return ConnectorResult(
        "Databricks / Unity Catalog",
        f"{catalog}.{schema}",
        prepare_files(frames),
    )


def connect_rest_api(
    *,
    url: str,
    method: str = "GET",
    headers_json: str = "",
    body_json: str = "",
    timeout: int = 60,
) -> ConnectorResult:
    if not url.startswith(("https://", "http://")):
        raise ConnectorError("REST URL must use http:// or https://.")

    try:
        headers = json.loads(headers_json or "{}")
        if not isinstance(headers, dict):
            raise ValueError
    except Exception as exc:
        raise ConnectorError("REST headers must be a JSON object.") from exc

    try:
        body = json.loads(body_json) if body_json.strip() else None
    except Exception as exc:
        raise ConnectorError("REST request body must be valid JSON.") from exc

    method = method.upper()
    if method not in {"GET", "POST"}:
        raise ConnectorError("REST connector supports GET and POST.")

    response = requests.request(
        method,
        url,
        headers=headers,
        json=body,
        timeout=timeout,
    )
    response.raise_for_status()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ConnectorError(
            "REST endpoint did not return JSON."
        ) from exc

    frames = prepare_files(
        _frames_from_json(
            payload,
            _safe_name(url.rstrip("/").split("/")[-1] or "api"),
        )
    )

    return ConnectorResult(
        "REST API",
        f"{method} {url}",
        frames,
    )


def connect_cloud(
    *,
    protocol: str,
    path: str,
    storage_options: dict[str, Any] | None = None,
) -> ConnectorResult:
    if protocol not in {"s3", "abfs", "az"}:
        raise ConnectorError(
            "Cloud connector supports s3:// and abfs:// paths."
        )

    if not path.startswith(("s3://", "abfs://", "az://")):
        raise ConnectorError(
            "Cloud path must start with s3:// or abfs://."
        )

    try:
        import fsspec
    except ImportError as exc:
        raise ConnectorError(
            "fsspec/cloud filesystem dependencies are not installed."
        ) from exc

    options = storage_options or {}
    fs, fs_path = fsspec.core.url_to_fs(
        path,
        **options,
    )

    # A single file is read directly; a directory is expanded.
    if fs.isfile(fs_path):
        paths = [path]
    else:
        paths = fs.glob(fs_path + "/*")
        protocol_prefix = "s3://" if protocol == "s3" else "abfs://"
        paths = [protocol_prefix + p.lstrip("/") for p in paths]

    frames = {}
    for source_path in paths:
        lower = source_path.lower()
        name = _safe_name(source_path.rstrip("/").split("/")[-1])
        with fsspec.open(source_path, mode="rb", **options) as fh:
            payload = fh.read()

        if lower.endswith(".csv"):
            frames[name] = pd.read_csv(io.BytesIO(payload))
        elif lower.endswith(".json"):
            frames[name] = pd.read_json(io.BytesIO(payload))
        elif lower.endswith(".parquet"):
            frames[name] = pd.read_parquet(io.BytesIO(payload))
        elif lower.endswith((".xlsx", ".xls")):
            frames[name] = pd.read_excel(io.BytesIO(payload))

    if not frames:
        raise ConnectorError(
            "No supported tabular files were found at the cloud path."
        )

    return ConnectorResult(
        "Cloud Storage",
        path,
        prepare_files(frames),
    )
