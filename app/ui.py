"""Look and feel: dark navy / blue theme with cyan accents, plus small helpers for cards, badges and charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.helpers import esc

ACCENT, ACCENT2 = "#22D3EE", "#3B82F6"  # cyan, blue
GREEN, AMBER, RED = "#4ADE80", "#FBBF24", "#F87171"
TONES = {"green": ("rgba(74,222,128,.15)", "#4ADE80"), "amber": ("rgba(251,191,36,.15)", "#FBBF24"),
         "red": ("rgba(248,113,113,.15)", "#F87171"), "blue": ("rgba(59,130,246,.18)", "#60A5FA"),
         "cyan": ("rgba(34,211,238,.15)", "#22D3EE"), "gray": ("rgba(148,163,184,.15)", "#CBD5E1")}
STATUS_UI = {"MATCH": ("MATCH", "green", GREEN), "PARTIAL": ("PARTIAL", "amber", AMBER), "GAP": ("GAP", "red", RED)}

# Newer Streamlit versions use width="stretch"; older ones use use_container_width=True.
_NEW_ST = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit()) >= (1, 50)
STRETCH = {"width": "stretch"} if _NEW_ST else {"use_container_width": True}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }
.stApp { background: #0B1230; color: #F1F5FF; }
.block-container { padding-top: 1.6rem; max-width: 1350px; }
header[data-testid="stHeader"] { background: transparent; }
h1, h2, h3, h4, label, .stMarkdown, p, li, span { color: #F1F5FF; }
.stCaption, [data-testid="stCaptionContainer"] { color: #9FB0E0 !important; }
section[data-testid="stSidebar"] { background: #070D24; border-right: 1px solid #1B2858; }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 2px; }
section[data-testid="stSidebar"] label[data-baseweb="radio"] { padding: 9px 14px; border-radius: 10px; width: 100%; margin: 0; cursor: pointer; }
section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child { display: none; }
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover { background: rgba(255,255,255,.06); }
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) { background: linear-gradient(90deg, #0E7490, #2563EB); }
.brand { font-size: 19px; font-weight: 700; color: #fff !important; line-height: 1.25; }
.brand-sub { font-size: 12px; color: #22D3EE !important; margin-bottom: 8px; }
.side-note { font-size: 12px; color: #9FB0E0 !important; }
.page-title { font-size: 28px; font-weight: 700; color: #fff; margin-bottom: 2px; }
.page-sub { color: #9FB0E0; font-size: 14px; margin-bottom: 18px; }
[class*="st-key-card"] { background: #121C45; border: 1px solid #1E2B63; border-radius: 16px; padding: 1.1rem 1.3rem; }
.card-title { font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 8px; }
.kpi { background: #121C45; border: 1px solid #1E2B63; border-radius: 16px; padding: 16px 18px; min-height: 118px; }
.kpi-label { font-size: 12.5px; color: #9FB0E0; font-weight: 500; }
.kpi-value { font-size: 27px; font-weight: 700; color: #fff; margin: 4px 0 6px 0; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.pbar { background: #1E2B63; border-radius: 999px; height: 8px; overflow: hidden; }
.pbar > div { height: 100%; border-radius: 999px; }
.srow { display: flex; justify-content: space-between; font-size: 13.5px; color: #F1F5FF; margin: 10px 0 5px 0; }
.srow span:last-child { color: #9FB0E0; }
.note { background: rgba(34,211,238,.08); border-left: 4px solid #22D3EE; border-radius: 8px; padding: 10px 14px; font-size: 13px; color: #CFEFFA; margin: 8px 0; }
.note.warn { background: rgba(251,191,36,.10); border-left-color: #FBBF24; color: #FDE9B0; }
.item { border: 1px solid #1E2B63; border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; background: #0E1740; font-size: 13.5px; color: #DDE6FF; }
.item b { color: #fff; }
.banner { border-radius: 16px; padding: 20px 24px; color: #fff; }
.banner .t { font-size: 13px; opacity: .9; } .banner .v { font-size: 30px; font-weight: 700; }
.chip { display: inline-block; padding: 4px 11px; margin: 3px 5px 3px 0; border-radius: 999px; font-size: 12.5px; font-weight: 500; }
.stButton > button { border-radius: 10px; font-weight: 600; }
div[data-testid="stExpander"] { border: 1px solid #1E2B63; border-radius: 12px; background: #0F1840; }
</style>
"""


def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def badge(text: str, tone: str = "blue") -> str:
    bg, fg = TONES[tone]
    return f'<span class="badge" style="background:{bg};color:{fg}">{esc(text)}</span>'


def chips(items: list[str], tone: str = "blue") -> str:
    bg, fg = TONES[tone]
    return "".join(f'<span class="chip" style="background:{bg};color:{fg}">{esc(i)}</span>' for i in items) or '<span style="color:#9FB0E0;font-size:13px">None</span>'


def kpi(label: str, value: str, sub: str = "", tone: str = "blue") -> None:
    html(f'<div class="kpi"><div class="kpi-label">{esc(label)}</div><div class="kpi-value">{esc(value)}</div>{badge(sub, tone) if sub else ""}</div>')


def header(title: str, subtitle: str = "") -> None:
    html(f'<div class="page-title">{esc(title)}</div><div class="page-sub">{subtitle}</div>')


def card(name: str):
    return st.container(key=f"card_{name}")


def card_title(text: str) -> None:
    html(f'<div class="card-title">{esc(text)}</div>')


def note(text: str, warn: bool = False) -> None:
    html(f'<div class="note{" warn" if warn else ""}">{text}</div>')


def progress_row(name: str, pct: float, right: str = "", color: str = ACCENT) -> None:
    html(f'<div class="srow"><span>{esc(name)}</span><span>{esc(right)}</span></div>'
         f'<div class="pbar"><div style="width:{max(0, min(100, pct)):.0f}%;background:{color}"></div></div>')


def table(df: pd.DataFrame) -> None:
    st.dataframe(df, hide_index=True, **STRETCH)


def plot(fig: go.Figure, key: str, height: int = 300) -> None:
    fig.update_layout(template="plotly_dark", height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, Segoe UI, sans-serif", size=12, color="#DDE6FF"),
                      legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#1E2B63")
    st.plotly_chart(fig, key=key, **STRETCH)


def gauge(value: float, key: str, title: str = "", height: int = 240) -> None:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=value, number={"suffix": "%", "font": {"size": 36}},
                                 title={"text": title, "font": {"size": 13}},
                                 gauge={"axis": {"range": [0, 100]}, "bar": {"color": ACCENT, "thickness": 0.28},
                                        "steps": [{"range": [0, 50], "color": "rgba(248,113,113,.25)"},
                                                  {"range": [50, 75], "color": "rgba(251,191,36,.25)"},
                                                  {"range": [75, 100], "color": "rgba(74,222,128,.25)"}]}))
    plot(fig, key, height)


def go_to(page: str) -> None:
    """Button callback: switch the sidebar page."""
    st.session_state.nav = page