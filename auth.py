"""DataPrepAI role-based access control for Streamlit Cloud.

Authentication is intentionally server-side: credentials live in Streamlit
Secrets and are never committed to the repository or exposed to the browser.
This is a small-team access gate. For enterprise SSO, replace authenticate()
with the organization's OIDC/Entra/Okta integration while keeping the same
role/page authorization contract.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import streamlit as st

ROLES = ("Admin", "Data Engineer", "Analyst", "Business User", "Viewer")

ROLE_PAGES = {
    "Admin": {
        "Home", "Data Onboarding", "Data Preparation", "Databricks Discovery", "AI Analysis",
        "Semantic Intelligence", "Business Model", "QA Validation",
        "Analytics", "AI/BI Dashboard", "Ask AI", "Genie Agent", "Security Center",
        "Connectors", "Audit & Policies",
    },
    "Data Engineer": {
        "Home", "Data Onboarding", "Data Preparation", "Databricks Discovery", "AI Analysis",
        "Semantic Intelligence", "Business Model", "QA Validation",
    },
    "Analyst": {"Home", "Analytics", "AI/BI Dashboard", "Ask AI"},
    "Business User": {"Home", "Analytics", "AI/BI Dashboard", "Genie Agent"},
    "Viewer": {"Home", "Analytics"},
}

ROLE_PUBLISH = {"Admin"}


def _secret(name: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def auth_enabled() -> bool:
    raw = _secret("CINVENT_AUTH_ENABLED", True)
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _load_users() -> list[dict[str, str]]:
    """Load the single shared DataPrepAI demo/workspace identity from secrets.

    Secrets expected:
    [DATAPREPAI_AUTH]
    email = "cinvent@capgemini.com"
    password = "<secret>"
    role = "Admin"
    """
    users=[]
    try:
        cfg=st.secrets.get("DATAPREPAI_AUTH")
        if cfg and hasattr(cfg,"get"):
            email=str(cfg.get("email","")).strip().lower()
            password=str(cfg.get("password",""))
            role=str(cfg.get("role","Admin")).strip()
            name=str(cfg.get("name","DataPrepAI Shared User")).strip()
            if email and password and role in ROLES:
                users.append({"email":email,"plain_password":password,"role":role,"name":name})
    except Exception:
        pass
    return users

def password_hash(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return digest.hex()


def authenticate(email: str, password: str) -> dict[str, str] | None:
    email=email.strip().lower()
    for user in _load_users():
        if user["email"] != email:
            continue
        if hmac.compare_digest(password, user["plain_password"]):
            return {"email":email,"name":user.get("name") or "DataPrepAI Shared User","role":user["role"]}
    return None

def is_authenticated() -> bool:
    return bool(st.session_state.get("cinvent_authenticated"))


def current_user() -> dict[str, str] | None:
    if not is_authenticated():
        return None
    return {
        "email": str(st.session_state.get("cinvent_email", "")),
        "role": str(st.session_state.get("cinvent_role", "")),
    }


def can_access(page: str, role: str | None = None) -> bool:
    role = role or str(st.session_state.get("cinvent_role", ""))
    return page in ROLE_PAGES.get(role, set())


def can_publish(role: str | None = None) -> bool:
    role = role or str(st.session_state.get("cinvent_role", ""))
    return role in ROLE_PUBLISH


def logout() -> None:
    for key in ("cinvent_authenticated", "cinvent_email", "cinvent_role"):
        st.session_state.pop(key, None)
    st.session_state["_invent_current_page"] = "Home"
    st.rerun()


def render_login() -> None:
    st.markdown("""
    <div style='max-width:560px;margin:6vh auto 0;background:#fff;border:1px solid #DCE5ED;border-radius:22px;padding:30px 34px;box-shadow:0 20px 60px rgba(8,34,60,.10)'>
      <div style='display:flex;align-items:center;gap:14px;margin-bottom:22px'>
        <div style='width:58px;height:58px;border-radius:16px;background:linear-gradient(135deg,#0B1F36,#0875D1);display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px;font-weight:900;letter-spacing:-.5px'>DP<span style="color:#B7A3FF">AI</span></div>
        <div>
          <div style='font-size:13px;font-weight:700;color:#0875D1'>Capgemini</div>
          <div style='font-size:25px;font-weight:900;color:#0B1F36'>DataPrep<span style="color:#6B35F5">AI</span></div>
          <div style='font-size:9px;color:#6C7E91;letter-spacing:1px;font-weight:700'>DATA PREPARATION • SEMANTIC ANALYTICS • AI</div>
        </div>
      </div>
      <div style='height:1px;background:#E8EEF3;margin:0 0 20px'></div>
      <div style='font-size:15px;font-weight:800;color:#0B1F36;margin-bottom:5px'>Welcome back</div>
      <div style='font-size:12px;color:#6C7E91;margin-bottom:18px'>Sign in to access Capgemini DataPrepAI.</div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("dataprepai_login_form", clear_on_submit=False):
        email = st.text_input("Login ID", placeholder="cinvent@capgemini.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in to DataPrepAI", type="primary", use_container_width=True)
        if submitted:
            now = time.time()
            lock_until = float(st.session_state.get("cinvent_lock_until", 0))
            if now < lock_until:
                st.error("Too many failed attempts. Please try again in 60 seconds.")
                return
            user = authenticate(email, password)
            if user:
                st.session_state["cinvent_authenticated"] = True
                st.session_state["cinvent_email"] = user["email"]
                st.session_state["cinvent_role"] = user["role"]
                st.session_state["cinvent_login_failures"] = 0
                st.session_state["_invent_current_page"] = "Home"
                st.rerun()
            else:
                failures = int(st.session_state.get("cinvent_login_failures", 0)) + 1
                st.session_state["cinvent_login_failures"] = failures
                if failures >= 5:
                    st.session_state["cinvent_lock_until"] = now + 60
                    st.session_state["cinvent_login_failures"] = 0
                st.error("Invalid login ID or password.")

def require_login() -> bool:
    if not auth_enabled():
        return True
    if not is_authenticated():
        render_login()
        return False
    return True
