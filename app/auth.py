"""Login / Create Account (demo authentication).

Accounts are stored in data/users.json with salted, hashed passwords. This is a simple Streamlit session login for a
college project. It is NOT enterprise-grade authentication.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re

import streamlit as st

from ui import STRETCH, card, html
from utils.helpers import BASE_DIR

USERS_PATH = BASE_DIR / "data" / "users.json"  # created automatically on first registration


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


LOGIN_CSS = """
<style>
.stApp { background: radial-gradient(1100px 600px at 8% 0%, #2B3A8C 0%, transparent 60%),
         radial-gradient(900px 520px at 100% 100%, #5B2FC9 0%, transparent 55%), #0B1437; }
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none; }
.block-container { padding-top: 7vh; }
.st-key-card_login { padding: 2.1rem 2.3rem 1.6rem 2.3rem; border-radius: 20px; box-shadow: 0 24px 60px rgba(5,10,40,.45); }
.login-logo { width: 54px; height: 54px; border-radius: 15px; background: linear-gradient(135deg, #0891B2, #2563EB); display: flex; align-items: center; justify-content: center; margin: 0 auto 14px auto; }
.login-title { text-align: center; font-size: 22px; font-weight: 700; color: #fff; line-height: 1.25; }
.login-sub { text-align: center; font-size: 14px; color: #9FB0E0; margin: 4px 0 18px 0; }
.login-foot { font-size: 11.5px; color: #7F8FC0; text-align: center; margin-top: 12px; }
</style>
"""


LOGO_SVG = ('<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" '
            'stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="15 7 21 7 21 13"/></svg>')


def _login_bg_uri() -> str:
    """Subtle AI / data network pattern (inline SVG) used behind the login card."""
    import urllib.parse
    nodes = [(60, 80), (180, 40), (300, 110), (420, 60), (540, 130), (100, 220), (240, 200), (360, 260), (480, 210), (560, 320),
             (40, 360), (170, 340), (300, 400), (430, 380), (530, 470), (90, 500), (220, 540), (350, 520), (470, 570), (580, 560)]
    links = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (8, 9), (2, 6), (4, 8), (5, 10), (10, 11), (11, 12),
             (12, 13), (13, 14), (7, 12), (11, 15), (15, 16), (16, 17), (17, 18), (18, 19), (13, 17), (9, 14)]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">']
    parts += [f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}" stroke="#7C93FF" stroke-opacity="0.16" stroke-width="1"/>' for a, b in links]
    parts += [f'<circle cx="{x}" cy="{y}" r="{5 if i % 5 == 0 else 2.6}" fill="#9DB1FF" fill-opacity="{0.28 if i % 5 == 0 else 0.5}"/>' for i, (x, y) in enumerate(nodes)]
    parts += [f'<rect x="{500 + k * 14}" y="{590 - h}" width="8" height="{h}" fill="#7C93FF" fill-opacity="0.12"/>' for k, h in enumerate([20, 34, 26, 48, 38, 60])]
    parts.append("</svg>")
    return "data:image/svg+xml;utf8," + urllib.parse.quote("".join(parts))


LOGIN_BG_CSS = ("<style>.stApp { background-image: url(\"" + _login_bg_uri() + "\"), radial-gradient(1100px 600px at 8% 0%, #2B3A8C 0%, transparent 60%), "
                "radial-gradient(900px 520px at 100% 100%, #5B2FC9 0%, transparent 55%), linear-gradient(180deg, #0B1437, #070D26); "
                "background-size: 600px 600px, auto, auto, auto; background-attachment: fixed; }</style>")


def validate_email(email: str) -> str | None:
    email = email.strip()
    if not email:
        return "Email cannot be empty."
    if not EMAIL_RE.match(email) or ".." in email:
        return "Enter a valid email address, for example student@college.edu."
    return None


def validate_password(pw: str) -> str | None:
    if not pw:
        return "Password cannot be empty."
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one number."
    return None


def hash_password(pw: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16).hex()
    return salt, hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()


@st.cache_resource(show_spinner=False)
def _memory_users() -> dict:
    """Fallback store used only if the users file cannot be written."""
    return {}


def load_users() -> dict:
    users = dict(_memory_users())
    try:
        if USERS_PATH.is_file():
            users.update(json.loads(USERS_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return users


def save_user(email: str, record: dict) -> bool:
    """Store the user; returns True if persisted to disk."""
    _memory_users()[email] = record
    try:
        users = {}
        if USERS_PATH.is_file():
            users = json.loads(USERS_PATH.read_text(encoding="utf-8"))
        users[email] = record
        USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        USERS_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")
        return True
    except (OSError, ValueError):
        return False


def verify_login(email: str, pw: str) -> dict | None:
    rec = load_users().get(email.strip().lower())
    if not rec:
        return None
    _, digest = hash_password(pw, rec["salt"])
    return rec if hmac.compare_digest(digest, rec["hash"]) else None


def set_auth_mode(mode: str) -> None:
    st.session_state.auth_mode = mode
    st.session_state.pop("auth_notice", None)


def logout() -> None:
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def page_login() -> None:
    ss = st.session_state
    html(LOGIN_CSS + LOGIN_BG_CSS)
    mode = ss.get("auth_mode", "login")
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid, card("login"):
        html(f'<div class="login-logo">{LOGO_SVG}</div><div class="login-title">AI-Powered Skill Gap Analysis</div>'
             f'<div class="login-sub">Placement Readiness Platform<br><span style="font-size:12px;color:#7F8FC0">'
             f'Resume analysis &middot; Skill gaps &middot; Personalized roadmap</span></div>')
        if ss.get("auth_notice"):
            st.success(ss.auth_notice)
        if mode == "login":
            with st.form("login_form"):
                email = st.text_input("Email address", placeholder="student@college.edu")
                pw = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("LOGIN", type="primary", **STRETCH)
            if submitted:
                err = validate_email(email) or validate_password(pw)
                if err:
                    st.error(err)
                else:
                    rec = verify_login(email, pw)
                    if rec is None:
                        st.error("Incorrect email or password. New here? Create an account below.")
                    else:
                        for k in ("auth_notice", "auth_mode"):
                            ss.pop(k, None)
                        ss.authenticated = True
                        ss.user = {"name": rec["name"], "email": email.strip().lower()}
                        st.rerun()
            st.button("Don't have an account? Create Account", key="to_register", on_click=set_auth_mode,
                      args=("register",), **STRETCH)
        else:
            with st.form("register_form"):
                name = st.text_input("Full name", placeholder="Your full name")
                email = st.text_input("Email address", placeholder="student@college.edu")
                pw = st.text_input("Password", type="password", placeholder="At least 8 characters, letters and numbers")
                pw2 = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("CREATE ACCOUNT", type="primary", **STRETCH)
            if submitted:
                err = ("Full name cannot be empty." if len(name.strip()) < 2 else None) or validate_email(email) \
                    or validate_password(pw) or (None if pw == pw2 else "Passwords do not match.")
                if not err and email.strip().lower() in load_users():
                    err = "An account with this email already exists. Please log in."
                if err:
                    st.error(err)
                else:
                    salt, digest = hash_password(pw)
                    saved = save_user(email.strip().lower(), {"name": name.strip(), "salt": salt, "hash": digest})
                    ss.auth_mode = "login"
                    ss.auth_notice = "Account created. Please log in." + ("" if saved else " (Stored for this server session only.)")
                    st.rerun()
            st.button("Already have an account? Log in", key="to_login", on_click=set_auth_mode, args=("login",), **STRETCH)
        html('<div class="login-foot">Demo sign-in for this college project. Passwords are stored hashed on this '
             'machine; this is not enterprise-grade authentication.</div>')