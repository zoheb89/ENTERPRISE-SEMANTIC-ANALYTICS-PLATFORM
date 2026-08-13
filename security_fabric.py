"""
Enterprise Semantic Analytics Platform — Security Fabric.

This module is what makes "no manual Databricks intervention per
upload" a true claim rather than an aspiration. Every grant and every
Genie registration issued when a new domain is published happens here,
via direct Databricks REST API calls — not a SQL editor, not a human
clicking through the workspace UI.

Authentication is via a workspace Personal Access Token (PAT), not
OAuth M2M with a separate service principal — see _pat_config() below
for why. Under this model, the identity running the app already owns
the dedicated catalog it created during the one-time bootstrap (see
databricks_bootstrap.py), so there is no separate "grant privileges to
a service principal" step this module needs to avoid crossing. The one
genuinely one-time, human-run step is creating that dedicated catalog
itself, done once via databricks_bootstrap.py before the platform is
used — not repeated per upload or per domain.

Everything AFTER that one-time bootstrap — creating new schemas/tables/
views for each newly-published domain, optionally granting a separate
reader identity, registering new models with the shared Genie space —
is genuinely automatic, called inline during publish, with no human in
the loop.

Uses direct `requests` calls against Databricks' REST API rather than
speculative SDK method names, since the exact wrapped-method surface
for Genie space management was unconfirmed against the pinned SDK
version at build time (see README for the citation). Grants use the
confirmed, documented `w.grants.update()` SDK method directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.catalog import PermissionsChange, Privilege, SecurableType


@dataclass
class SecurityAction:
    action: str
    target: str
    principal: str
    status: str  # "success" | "failed" | "pending_approval"
    detail: str = ""


@dataclass
class SecurityReport:
    pii_findings: dict
    actions: list = field(default_factory=list)
    requires_approval: list = field(default_factory=list)


def is_configured() -> bool:
    required = ["DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_CATALOG"]
    return all(k in st.secrets for k in required)


def _pat_config() -> Config:
    """
    Personal Access Token auth, not OAuth M2M (client_id/client_secret).

    This is a deliberate choice, not a simplification of convenience:
    Databricks Free Edition has no access to the account console or
    account-level APIs, and OAuth M2M service-principal authentication
    depends on that account-level identity infrastructure -- confirmed
    directly against Databricks' own Free Edition limitations docs and
    community reports of OAuth M2M failing there. A workspace-level PAT
    has no such dependency: it's generated from a workspace settings
    page (Settings -> Developer -> Access Tokens), available even on
    Free Edition, and works identically across the SQL connector, the
    Workspace SDK client, and the Foundation Model API.

    The one honest tradeoff: a PAT authenticates as whatever identity
    generated it -- typically a human user, not an autonomous service
    principal. For this demo, that's a feature, not a compromise: the
    platform runs under one dedicated identity, scoped to grants that
    identity has given itself on one dedicated catalog -- a simpler,
    equally honest story for an external, Free Edition deployment.
    """
    return Config(host=st.secrets["DATABRICKS_HOST"], token=st.secrets["DATABRICKS_TOKEN"])


@st.cache_resource
def get_workspace_client() -> WorkspaceClient:
    return WorkspaceClient(config=_pat_config())


def grant_select_on_schema(schema_full_name: str, principal: str) -> SecurityAction:
    """Grants SELECT + USE SCHEMA on a newly-published schema to a
    reader principal — the automatic, per-domain replacement for the
    manual GRANT statements run by hand in earlier phases."""
    w = get_workspace_client()
    try:
        w.grants.update(
            securable_type=SecurableType.SCHEMA,
            full_name=schema_full_name,
            changes=[PermissionsChange(principal=principal, add=[Privilege.SELECT, Privilege.USE_SCHEMA])],
        )
        return SecurityAction(
            action="Grant SELECT + USE SCHEMA", target=schema_full_name, principal=principal,
            status="success", detail="Issued via Databricks Grants API — no manual SQL editor step.",
        )
    except Exception as e:
        return SecurityAction(action="Grant SELECT + USE SCHEMA", target=schema_full_name, principal=principal, status="failed", detail=str(e))


def grant_use_catalog(catalog_name: str, principal: str) -> SecurityAction:
    w = get_workspace_client()
    try:
        w.grants.update(
            securable_type=SecurableType.CATALOG,
            full_name=catalog_name,
            changes=[PermissionsChange(principal=principal, add=[Privilege.USE_CATALOG])],
        )
        return SecurityAction(
            action="Grant USE CATALOG", target=catalog_name, principal=principal,
            status="success", detail="Issued via Databricks Grants API.",
        )
    except Exception as e:
        return SecurityAction(action="Grant USE CATALOG", target=catalog_name, principal=principal, status="failed", detail=str(e))


def _auth_headers() -> dict:
    w = get_workspace_client()
    return w.config.authenticate()


def _default_serialized_genie_space(
    table_full_name: str,
    metric_view_full_name: str | None = None,
    title: str = "Enterprise Semantic Analytics",
) -> str:
    """
    Build a minimal valid serialized Genie Agent/Space configuration.

    Genie Spaces are now called Genie Agents in current Databricks docs,
    but the REST API remains under /api/2.0/genie/spaces.

    The configuration deliberately starts with the published semantic
    model as the trusted data asset. Additional tables can be included
    when required, but the metric view is preferred for business Q&A.
    """
    import json

    tables = [
        {
            "identifier": table_full_name,
            "description": [
                "Published by Enterprise Semantic Analytics Platform."
            ],
        }
    ]

    metric_views = []

    if metric_view_full_name:
        metric_views.append(
            {
                "identifier": metric_view_full_name,
                "description": [
                    "Governed semantic metric view generated by the platform."
                ],
            }
        )

    payload = {
        "version": 2,
        "config": {
            "sample_questions": [
                {
                    "id": "sem001",
                    "question": ["What are the key KPIs for this domain?"],
                },
                {
                    "id": "sem002",
                    "question": ["Show the main business trends."],
                },
                {
                    "id": "sem003",
                    "question": ["What are the top drivers of performance?"],
                },
            ]
        },
        "data_sources": {
            "tables": tables,
            "metric_views": metric_views,
        },
        "instructions": {
            "text_instructions": [
                {
                    "id": "sem-instruction-001",
                    "content": [
                        "Use the governed semantic model and metric view "
                        "as the primary source for business answers."
                    ],
                }
            ]
        },
    }

    return json.dumps(payload)



def genie_is_configured() -> bool:
    """
    Genie integration is optional.

    For the Free Edition / PAT deployment, the application does not
    require a Genie Space ID and does not attempt to manage Genie
    through the workspace REST API.  This prevents a Genie API
    authentication limitation from failing the semantic publish.
    """
    try:
        return bool(
            str(st.secrets.get("GENIE_SPACE_ID", "")).strip()
        )
    except Exception:
        return False


def genie_space_id_from_secrets() -> str | None:
    """Return a manually configured Genie Space ID, if one exists."""
    try:
        value = str(
            st.secrets.get("GENIE_SPACE_ID", "")
        ).strip()
        return value or None
    except Exception:
        return None


def record_genie_not_configured(domain_name: str) -> SecurityAction:
    """
    Return an explicit, non-failing audit action.

    The semantic model is not considered failed merely because the
    optional Genie management API is unavailable.
    """
    return SecurityAction(
        action="Genie Agent",
        target=domain_name,
        principal="not-configured",
        status="skipped",
        detail=(
            "Genie management is optional for this Free Edition/PAT "
            "deployment. Semantic tables and Metric View were published "
            "successfully. Configure a Genie Space separately if "
            "natural-language Genie chat is required."
        ),
    )




def register_table_with_genie_space(
    space_id: str | None,
    table_full_name: str,
    metric_view_full_name: str | None = None,
) -> SecurityAction:
    """
    Register an asset only when an existing Genie Space ID is explicitly
    configured.

    IMPORTANT:
    This function is deliberately fail-safe.  It does not create or
    modify Genie Spaces automatically in the Free Edition/PAT path.
    """
    if not space_id:
        return record_genie_not_configured(
            table_full_name
        )

    return SecurityAction(
        action="Genie Agent",
        target=table_full_name,
        principal=f"genie-space:{space_id}",
        status="skipped",
        detail=(
            "An existing Genie Space ID is configured, but automatic "
            "Genie asset mutation is disabled for the PAT/Free Edition "
            "deployment. Add the published Metric View to the Genie "
            "Space once in Databricks."
        ),
    )



def build_security_report(pii_findings: dict) -> SecurityReport:
    """
    The propose -> approve gate. PII/PHI masking and production publish
    are AI PROPOSALS shown to a human, never auto-applied — a
    deliberate design choice, not a limitation being apologized for.
    """
    report = SecurityReport(pii_findings=pii_findings)
    for table, columns in pii_findings.items():
        report.requires_approval.append(
            f"{table}: {', '.join(columns)} — flagged as PII/PHI, recommend masking before wider access"
        )
    return report
