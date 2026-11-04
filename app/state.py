"""Session state: everything the student has entered or confirmed during this session."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from placement_model import FEATURES, check_value, predict
from recommendations import suggest_roles
from resume_analyzer import cgpa_number
from roadmap import build_roadmap, completed_skills
from skill_gap import analyze, evidence_context, gap_rows, match_breakdown


def log(text: str) -> None:
    st.session_state.activity.insert(0, (datetime.now().strftime("%d %b, %H:%M"), text))
    del st.session_state.activity[30:]


def init_state() -> None:
    ss = st.session_state
    if "career_init" in ss:
        return
    ss.career_init = True
    ss.resume, ss.resume_draft, ss.resume_ver = None, None, 0   # confirmed resume / editable draft
    ss.job, ss.job_draft, ss.job_ver = None, None, 0            # confirmed target job / editable draft
    ss.ml, ss.ml_src, ss.ml_notes, ss.form_ver = {f: None for f in FEATURES}, {}, [], 0
    ss.roadmap_done, ss.progress_log = {}, []
    ss.activity, ss.iv_history, ss.iv_q, ss.iv_last, ss.chat = [], [], None, None, []
    log("Signed in")


def sync_ml_from_resume() -> None:
    """Pre-fill the ML inputs that the VERIFIED resume can supply.

    Every value is checked first. A value that is impossible (outside its valid range) is NOT stored and the student is told
    why. A value that is possible but outside the training range is stored unchanged and flagged with a visible warning.
    Values the student typed themselves are never overwritten.
    """
    ss = st.session_state
    info, notes, derived = ss.resume["info"], [], {}
    derived["Projects"] = len(info["projects"])
    derived["Internships"] = len(info["internships"])
    derived["Certifications"] = len(info["certifications"])
    derived["Resume_Score"] = ss.resume["quality"]["score"]
    if (c := cgpa_number(info)) is not None:
        derived["CGPA"] = c
    elif info["cgpa"]:
        notes.append(f"CGPA '{info['cgpa']}' is not on a 10-point scale, so it was not used. Please enter your CGPA in Profile.")
    if info["hackathons"]:  # only when the student verified at least one hackathon entry
        derived["Hackathon"] = 1
    for key, value in derived.items():
        clean, problem = check_value(key, value)
        if problem:
            notes.append(f"{problem} It was not saved. Please enter the correct value in Profile.")
        elif ss.ml_src.get(key) != "user":
            ss.ml[key], ss.ml_src[key] = clean, "resume"
    ss.ml_notes = notes
    ss.form_ver += 1


def reset_profile_inputs() -> None:
    ss = st.session_state
    ss.ml, ss.ml_src, ss.ml_notes = {f: None for f in FEATURES}, {}, []
    if ss.resume:
        sync_ml_from_resume()
    ss.form_ver += 1


def reset_analysis() -> None:
    """Start New Analysis: clears resume, target job, gaps, roadmap and progress. The login is kept."""
    ss = st.session_state
    ss.resume = ss.resume_draft = ss.job = ss.job_draft = None
    ss.roadmap_done, ss.progress_log = {}, []
    ss.iv_q, ss.iv_last, ss.iv_history, ss.chat = None, None, [], []
    for k in [k for k, v in ss.ml_src.items() if v == "resume"]:
        ss.ml[k] = None
        del ss.ml_src[k]
    ss.ml_notes = []
    ss.resume_ver += 1
    ss.job_ver += 1
    ss.form_ver += 1
    log("Started a new analysis")


def get_ctx() -> dict | None:
    """Everything the pages need. None until a resume is confirmed. Job-related parts are empty until a job is confirmed."""
    ss = st.session_state
    if ss.resume is None:
        return None
    info, text = ss.resume["info"], ss.resume["text"]
    ctx = dict(info=info, text=text, quality=ss.resume["quality"], ev=evidence_context(info, text), ml=ss.ml, pred=predict(ss.ml),
               job=ss.job, an=None, gaps=[], road=[])
    if ss.job is not None:
        ctx["an"] = analyze(info, text, ss.job)
        ctx["gaps"] = gap_rows(ctx["an"])
        ctx["road"] = build_roadmap(ctx["gaps"], ss.job["role"])
    ctx["roles"] = suggest_roles(info, ctx["ev"], ss.job, {g["skill"] for g in ctx["gaps"]})
    return ctx


def projected_match(ctx: dict) -> float | None:
    """Job Requirement Match if every completed roadmap skill were on the resume (shown in Progress Tracker only)."""
    return match_breakdown(ctx["an"]["rows"], completed_skills(ctx["gaps"], st.session_state.roadmap_done))["percent"]


def record_progress(ctx: dict) -> None:
    ss = st.session_state
    done = sum(1 for v in ss.roadmap_done.values() if v)
    if (ss.progress_log and ss.progress_log[-1]["done"] != done) or (not ss.progress_log and done):
        ss.progress_log.append({"time": datetime.now().strftime("%d %b %H:%M"), "done": done, "projected": projected_match(ctx) or 0})
