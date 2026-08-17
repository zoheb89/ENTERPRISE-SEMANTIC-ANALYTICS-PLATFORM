import streamlit as st

NAVY="#0F1F35"; NAVY_DEEP="#0A1626"; TEAL="#1B7A8C"; TEAL_LIGHT="#E4EEF0"
AMBER_LIGHT="#FBF0E4"; CANVAS="#F7F6F3"; PANEL="#FFFFFF"; SLATE_SOFT="#5C6B7A"
LINE="#E2E1DB"; RED="#B0473F"; RED_LIGHT="#FBEBE9"; GREEN="#2E8B57"; GREEN_LIGHT="#E9F4EE"

def inject_base_css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');
#MainMenu {{visibility:hidden}} footer {{visibility:hidden}}
html,body,[class*="css"] {{font-family:'Inter',sans-serif}}
.stApp {{background:{CANVAS}}}
.block-container {{padding-top:1rem!important;padding-bottom:1.2rem!important;max-width:1200px}}
[data-testid="stSidebar"] {{background:{NAVY_DEEP}!important;width:250px!important;min-width:250px!important;max-width:250px!important;overflow:hidden!important;position:relative!important;z-index:1000!important}}
[data-testid="stSidebar"]>div:first-child,[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{background:{NAVY_DEEP}!important;height:100vh!important;overflow:hidden!important;padding:0!important}}
[data-testid="stSidebarHeader"] {{height:0!important;min-height:0!important;padding:0!important;margin:0!important;border:0!important}}
[data-testid="stSidebarHeader"] button {{display:none!important}}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{gap:.12rem!important}}
[data-testid="stSidebar"] .stButton {{margin:0!important;padding:0!important}}
[data-testid="stSidebar"] .stButton>button {{width:100%!important;min-height:29px!important;height:29px!important;padding:4px 9px!important;margin:0!important;border:1px solid transparent!important;border-radius:7px!important;background:transparent!important;color:#C9D3DD!important;text-align:left!important;font-size:12px!important;font-weight:600!important;line-height:20px!important;box-shadow:none!important}}
[data-testid="stSidebar"] .stButton>button:hover {{background:rgba(27,122,140,.16)!important;color:#fff!important}}
.cinvent-sidebar-shell {{height:100vh;display:flex;flex-direction:column;overflow:hidden;background:{NAVY_DEEP};padding:8px 10px 9px}}
.cinvent-brand {{flex:0 0 auto;padding:5px 5px 7px;border-bottom:1px solid rgba(255,255,255,.10);margin-bottom:5px}}
.cinvent-brand-row {{display:flex;align-items:center;gap:9px}}
.cinvent-logo {{width:31px;height:31px;border-radius:9px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:19px;font-weight:900;background:linear-gradient(135deg,#0A8FA3,#0875D1)}}
.cinvent-brand-name {{color:#fff;font-size:16px;line-height:18px;font-weight:800}}
.cinvent-brand-sub {{color:#8FA4B7;font-size:8.5px;line-height:11px;margin-top:1px}}
.cinvent-nav {{flex:1 1 auto;min-height:0;overflow:hidden;padding-top:1px}}
.cinvent-section-label {{color:#71889C;font-size:8px;line-height:11px;font-weight:800;letter-spacing:1px;margin:5px 4px 1px}}
.cinvent-user-card {{flex:0 0 auto;margin-top:5px;padding:7px 8px;border:1px solid rgba(255,255,255,.10);border-radius:10px;background:rgba(255,255,255,.055)}}
.cinvent-user-row {{display:flex;align-items:center;gap:8px}}
.cinvent-avatar {{width:29px;height:29px;border-radius:50%;background:linear-gradient(135deg,#1B7A8C,#0875D1);color:#fff;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800}}
.cinvent-user-name {{color:#fff;font-size:10.5px;line-height:13px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.cinvent-user-role {{color:#75D4D9;font-size:8.5px;line-height:11px;font-weight:700}}
.cinvent-user-email {{color:#8FA4B7;font-size:7.5px;line-height:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.platform-topbar {{background:{PANEL};border:1px solid {LINE};border-radius:10px;padding:13px 20px;margin-bottom:12px}}
.platform-topbar h1 {{font-family:'Source Serif 4',serif;font-size:22px;font-weight:600;color:{NAVY};margin:0}}
.platform-topbar-sub {{font-size:12px;color:{SLATE_SOFT};margin-top:3px}}
.platform-card-title {{font-family:'Source Serif 4',serif;font-size:16px;font-weight:600;color:{NAVY};margin-bottom:2px}}
.platform-card-sub {{font-size:12px;color:{SLATE_SOFT};margin-bottom:8px}}
.platform-tag {{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}}
.platform-tag.fact {{background:{TEAL_LIGHT};color:{TEAL}}}
.platform-tag.dim {{background:{AMBER_LIGHT};color:#A2661E}}
.platform-tag.pii {{background:{RED_LIGHT};color:{RED}}}
.platform-tag.ai {{background:{AMBER_LIGHT};color:#A2661E}}
.platform-tag.ok {{background:{GREEN_LIGHT};color:{GREEN}}}
</style>""", unsafe_allow_html=True)

def _navigate(page):
    st.session_state["_invent_current_page"]=page
    st.rerun()

def _initials(name,email):
    if name:
        p=name.split()
        return ((p[0][0]+p[-1][0]) if len(p)>1 else name[:2]).upper()
    return email[:2].upper()

def render_sidebar_brand():
    st.markdown("""<div class="cinvent-brand"><div class="cinvent-brand-row"><div class="cinvent-logo">C</div><div><div class="cinvent-brand-name">C INVENT</div><div class="cinvent-brand-sub">Enterprise Semantic Analytics Platform</div></div></div></div>""",unsafe_allow_html=True)

def render_sidebar_navigation():
    try:
        from auth import current_user, can_access
        user=current_user()
    except Exception:
        user=None
        can_access=lambda page: True
    current=st.session_state.get("_invent_current_page","Home")
    icons={"Home":"⌂","Data Onboarding":"⇧","Databricks Discovery":"⌘","AI Analysis":"✦","Semantic Intelligence":"◈","Business Model":"◇","QA Validation":"✓","Analytics":"▥","Ask AI":"▤","Genie Agent":"✧","Security Center":"◇","Connectors":"↗","Audit & Policies":"◷"}
    sections=[("",["Home"]),("ONBOARD",["Data Onboarding","Databricks Discovery"]),("MODEL",["AI Analysis","Semantic Intelligence","Business Model","QA Validation"]),("ANALYZE",["Analytics","Ask AI","Genie Agent"]),("GOVERN",["Security Center","Connectors","Audit & Policies"])]
    st.markdown('<div class="cinvent-sidebar-shell"><div class="cinvent-nav">',unsafe_allow_html=True)
    for section,items in sections:
        if section:
            st.markdown(f'<div class="cinvent-section-label">{section}</div>',unsafe_allow_html=True)
        for page in items:
            if not can_access(page):
                continue
            if st.button(f'{icons[page]}  {page}',key='cinvent_nav_'+page.lower().replace(' ','_'),use_container_width=True):
                _navigate(page)
    st.markdown('</div>',unsafe_allow_html=True)
    if user:
        name=str(user.get("name") or user.get("email","").split("@")[0]).strip()
        email=str(user.get("email","")).strip()
        role=str(user.get("role","")).strip()
        card=(
            '<div class="cinvent-user-card"><div class="cinvent-user-row">'
            f'<div class="cinvent-avatar">{_initials(name,email)}</div>'
            '<div style="min-width:0;flex:1">'
            f'<div class="cinvent-user-name">{name}</div>'
            f'<div class="cinvent-user-role">{role}</div>'
            f'<div class="cinvent-user-email">{email}</div>'
            '</div></div></div></div>'
        )
        st.markdown(card,unsafe_allow_html=True)
    else:
        st.markdown('</div>',unsafe_allow_html=True)

def render_user_identity(user=None):
    """Render the signed-in user identity card.

    Compatible with app.py importing/calling render_user_identity().
    """
    if user is None:
        try:
            from auth import current_user
            user = current_user()
        except Exception:
            user = None

    if not user:
        return

    name = str(user.get("name") or user.get("email", "").split("@")[0]).strip()
    email = str(user.get("email", "")).strip()
    role = str(user.get("role", "")).strip()

    card = (
        '<div class="cinvent-user-card"><div class="cinvent-user-row">'
        f'<div class="cinvent-avatar">{_initials(name,email)}</div>'
        '<div style="min-width:0;flex:1">'
        f'<div class="cinvent-user-name">{name}</div>'
        f'<div class="cinvent-user-role">{role}</div>'
        f'<div class="cinvent-user-email">{email}</div>'
        '</div></div></div>'
    )
    st.markdown(card, unsafe_allow_html=True)


def page_header(title,subtitle):
    st.markdown(f'<div class="platform-topbar"><h1>{title}</h1><div class="platform-topbar-sub">{subtitle}</div></div>',unsafe_allow_html=True)

def section_title(title,subtitle=""):
    sub=f'<div class="platform-card-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="platform-card-title">{title}</div>{sub}',unsafe_allow_html=True)
