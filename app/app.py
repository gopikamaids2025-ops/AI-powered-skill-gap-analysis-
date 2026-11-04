"""AI-Powered Skill Gap Analysis and Placement Readiness Prediction System.

Run from the project root (the folder that contains app/, models/ and data/):

    streamlit run app/app.py

Three separate ideas live in this project and are never mixed into one score:
  A. Skill Gap          resume vs one job description (rule-based)         -> skill_gap.py
  B. Placement Readiness  numeric profile -> trained ML model               -> placement_model.py
  C. Career Roles       resume skills vs the predefined role database       -> recommendations.py
"""
import sys
from pathlib import Path

# Make "utils" (project root) and the sibling modules in app/ importable no matter where Streamlit is started from.
_APP_DIR = Path(__file__).resolve().parent
for _p in (str(_APP_DIR.parent), str(_APP_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Skill Gap & Placement Readiness", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

from auth import logout, page_login  # noqa: E402
from placement_model import load_artifacts  # noqa: E402
from state import get_ctx, init_state, record_progress  # noqa: E402
from ui import CSS, STRETCH, badge, html  # noqa: E402
from utils.helpers import esc  # noqa: E402
from views import page_dashboard, page_readiness, page_resume, page_skill_gap, page_target  # noqa: E402
from views_more import page_advisor, page_interview, page_profile, page_progress, page_roadmap, page_roles  # noqa: E402

PAGES = {"Dashboard": page_dashboard, "Resume Analysis": page_resume, "Target Job": page_target, "Skill Gap": page_skill_gap,
         "Placement Readiness": page_readiness, "Roadmap": page_roadmap, "Career Roles": page_roles,
         "Progress Tracker": page_progress, "Mock Interview": page_interview, "Study Advisor": page_advisor, "Profile": page_profile}


def main() -> None:
    html(CSS)
    if not st.session_state.get("authenticated"):
        page_login()
        return
    init_state()
    ss = st.session_state
    _, _, info = load_artifacts()
    with st.sidebar:
        html('<div class="brand">Skill Gap &amp;<br>Placement Readiness</div><div class="brand-sub">Career readiness platform</div>')
        st.radio("Navigation", list(PAGES), key="nav", label_visibility="collapsed")
        html("<br>" + badge("Model loaded" if info["ok"] else "Model unavailable", "green" if info["ok"] else "red")
             + f'<div class="side-note" style="margin:8px 0 10px 0">{esc(ss.user["name"])}<br>{esc(ss.user["email"])}</div>')
        st.button("Log out", key="logout_sidebar", on_click=logout, **STRETCH)
    ctx = get_ctx()
    PAGES[ss.nav](ctx)
    if ctx is not None and ctx["an"] is not None:
        record_progress(ctx)


main()