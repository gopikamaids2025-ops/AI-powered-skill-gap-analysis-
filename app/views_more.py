"""Pages (part 2): Roadmap, Career Roles, Progress Tracker, Mock Interview, Study Advisor, Profile."""
from __future__ import annotations

import json
import random
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import logout
from interview import evaluate_answer, question_pool
from mentor import RuleBasedMentor, advice_items
from placement_model import (FEATURE_SPECS, SECTIONS, check_value, load_artifacts, load_companies, load_dataset,
                             missing_values, range_warnings, training_ranges)
from recommendations import STATEMENT
from resume_analyzer import Document, PdfReader
from roadmap import completed_skills, progress_label, skill_items, skill_progress
from state import log, projected_match, reset_analysis, reset_profile_inputs
from ui import ACCENT, STRETCH, badge, card, card_title, chips, header, html, kpi, note, plot, progress_row, table
from utils.helpers import BASE_DIR, esc, install_hint
from utils.skill_database import learning_plan
from views import need_job, need_resume


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------
def page_roadmap(ctx) -> None:
    if need_job(ctx):
        return
    ss, road = st.session_state, ctx["road"]
    header("Roadmap", f"A learning plan built only from your real gaps for <b>{esc(ctx['job']['role'])}</b>.")
    if not road:
        st.success("Your resume currently covers all detected requirements. No roadmap is needed.")
        return
    note("One week per gap: Required skills first, missing before partial. Tick items as you finish them; the Progress Tracker uses these ticks.")
    done = ss.roadmap_done
    total = sum(skill_progress(w["skill"], done)[1] for w in road)
    finished = sum(skill_progress(w["skill"], done)[0] for w in road)
    with card("rm_overall"):
        progress_row(f"Overall progress: {len(road)} weeks", 100 * finished / total, f"{finished}/{total} items")
    for w in road:
        with card(f"rm_{w['week']}"):
            html(f'<div class="card-title">Week {w["week"]}: {esc(w["skill"])} &nbsp;{badge(w["level"], "red" if w["level"] == "Required" else "blue")} '
                 f'{badge("GAP" if w["status"] == "GAP" else "PARTIAL", "red" if w["status"] == "GAP" else "amber")}</div>')
            html(f'<div style="font-size:13.5px;color:#BFD0F5;margin-bottom:8px"><b>Why it matters:</b> {esc(w["why"])}</div>')
            for item in skill_items(w["skill"]):
                k = f"{w['skill']}|{item}"
                done[k] = st.checkbox(item, value=done.get(k, False), key=f"rmk_{w['week']}_{item}")
            d, n = skill_progress(w["skill"], done)
            progress_row("Week progress", 100 * d / n, f"{d}/{n}")
            if w["generic"]:
                st.caption("This skill has no detailed guide in the app, so the topics follow a standard template.")


# ---------------------------------------------------------------------------
# Career Roles
# ---------------------------------------------------------------------------
def page_roles(ctx) -> None:
    if need_resume(ctx):
        return
    header("Career Roles", "Career role recommendations based on the skills in your verified resume.")
    note(STATEMENT)
    roles = [r for r in ctx["roles"] if r["pct"] > 0 or r["target"]]
    if not roles:
        st.info("None of your detected skills match the roles in the database yet. Add skills on the Resume Analysis page.")
        return
    for i, r in enumerate(roles[:8]):
        with st.expander(f"{r['role']} - {r['pct']:.0f}% role-skill match" + ("  (your target)" if r["target"] else ""), expanded=i == 0):
            html("<b>Matching skills</b><br>" + chips(r["matched"], "green"))
            html("<b>Partial skills</b><br>" + chips(r["partial"], "amber"))
            html("<b>Missing skills</b><br>" + chips(r["missing"], "red"))
            if r["projects"]:
                st.write("Your related projects: " + ", ".join(r["projects"][:3]))
            if r["shared_gaps"]:
                st.write("Also missing from your target job: " + ", ".join(r["shared_gaps"]))
            prep = [s for s in r["partial"] + r["missing"]][:3]
            st.write("Recommended preparation: " + ("; ".join(f"{s} ({learning_plan(s)['topics'][0]})" for s in prep) if prep else "You already show every skill listed for this role."))
    st.caption("Match % here = (matching skills + half of partial skills) ÷ skills listed for the role. It is separate from the Job Requirement Match.")


# ---------------------------------------------------------------------------
# Progress Tracker
# ---------------------------------------------------------------------------
def page_progress(ctx) -> None:
    if need_job(ctx):
        return
    ss, gaps = st.session_state, ctx["gaps"]
    header("Progress Tracker", "Progress toward closing the gaps in your roadmap.")
    if not gaps:
        st.success("Your resume currently covers all detected requirements. There is nothing to track.")
        return
    labels = {g["skill"]: progress_label(g, ss.roadmap_done) for g in gaps}
    comp = completed_skills(gaps, ss.roadmap_done)
    proj = projected_match(ctx)
    c = st.columns(4)
    with c[0]:
        kpi("Skills to learn", str(len(gaps)), "from your target job", "red")
    with c[1]:
        kpi("Completed", str(len(comp)), "skills", "green")
    with c[2]:
        kpi("In progress", str(sum(v == "In progress" for v in labels.values())), "skills", "amber")
    with c[3]:
        kpi("Projected job match", f"{proj:.0f}%", f"now {ctx['an']['match']:.0f}%", "blue")
    st.caption("Projected match = your Job Requirement Match if every completed skill were shown on your resume. "
               "Your real match only changes when you update your resume.")
    tone = {"Missing": "red", "Partial": "amber", "In progress": "blue", "Completed": "green"}
    a, b = st.columns(2)
    with a, card("pt_status"):
        card_title("Status of each gap")
        for g in gaps:
            d, n = skill_progress(g["skill"], ss.roadmap_done)
            html(f'<div class="item"><b>{esc(g["skill"])}</b> &nbsp;{badge(labels[g["skill"]], tone[labels[g["skill"]]])}'
                 f'<span style="float:right;color:#9FB0E0">{d}/{n}</span></div>')
    with b, card("pt_bars"):
        card_title("Completion by skill")
        vals = [100 * skill_progress(g["skill"], ss.roadmap_done)[0] / skill_progress(g["skill"], ss.roadmap_done)[1] for g in gaps]
        fig = go.Figure(go.Bar(x=vals[::-1], y=[g["skill"] for g in gaps][::-1], orientation="h", marker_color=ACCENT))
        fig.update_xaxes(range=[0, 100])
        plot(fig, "pt_bars_fig", max(230, 34 * len(gaps) + 60))
    with card("pt_hist"):
        card_title("Progress during this session")
        if not ss.progress_log:
            st.info("Tick items on the Roadmap page to start recording progress.")
        else:
            xs = [x["time"] for x in ss.progress_log]
            fig = go.Figure([go.Scatter(x=xs, y=[x["done"] for x in ss.progress_log], mode="lines+markers", name="Items completed"),
                             go.Scatter(x=xs, y=[x["projected"] for x in ss.progress_log], mode="lines+markers", name="Projected match %", yaxis="y2")])
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100], showgrid=False))
            plot(fig, "pt_hist_fig", 260)


# ---------------------------------------------------------------------------
# Mock Interview
# ---------------------------------------------------------------------------
def page_interview(ctx) -> None:
    if need_job(ctx):
        return
    ss = st.session_state
    header("Mock Interview", f"Practice questions for <b>{esc(ctx['job']['role'])}</b>, built from your target job and resume skills.")
    note("Rule-based feedback: the app checks whether key concepts appear in your answer, plus length and structure. No AI/LLM evaluates your answer.")
    a, b, c = st.columns([2, 2, 1])
    cat = a.selectbox("Category", ["Target job skills", "Technical (resume skills)", "HR"])
    diff = b.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    pool = question_pool(cat, diff, ctx)
    if not pool:
        st.info("No questions are available for this choice. Try the HR category or another difficulty.")
        return
    cur = ss.iv_q
    if cur is None or cur["cat"] != cat or cur["diff"] != diff or cur["q"] not in [p[1] for p in pool]:
        pick = random.choice(pool)
        ss.iv_q = cur = dict(cat=cat, diff=diff, label=pick[0], q=pick[1], kws=pick[2])
        ss.iv_last = None
    if c.button("New question", **STRETCH):
        pick = random.choice([p for p in pool if p[1] != cur["q"]] or pool)
        ss.iv_q = dict(cat=cat, diff=diff, label=pick[0], q=pick[1], kws=pick[2])
        ss.iv_last = None
        st.rerun()
    with card("iv_q"):
        html(f'<div class="card-title">{esc(cur["label"])} - {diff}</div><div style="font-size:17px;color:#fff">{esc(cur["q"])}</div>')
    with st.form("iv_form", clear_on_submit=True):
        answer = st.text_area("Your answer", height=150)
        submitted = st.form_submit_button("Submit answer", type="primary")
    if submitted:
        if len(answer.strip()) < 5:
            st.warning("Please write an answer first.")
        else:
            res = evaluate_answer(answer, cur["kws"], diff)
            ss.iv_last = res
            ss.iv_history.append({"Time": datetime.now().strftime("%H:%M"), "Topic": cur["label"], "Difficulty": diff, "Question": cur["q"], "Score": res["score"]})
            log(f"Mock interview: {cur['label']} ({diff}) scored {res['score']}")
    res = ss.iv_last
    if res:
        a, b = st.columns([1, 2])
        with a:
            kpi("Score", f"{res['score']}/100", f"{res['covered']}/{res['total']} concepts", "green" if res["score"] >= 70 else "amber")
        with b, card("iv_fb"):
            card_title("Feedback")
            st.write(res["feedback"])
            if res["missed"]:
                st.write("**Concepts to mention:** " + ", ".join(res["missed"]))
            st.caption("Score = 70% concept coverage + 20% answer length + 10% structure.")
    if ss.iv_history:
        hist = pd.DataFrame(ss.iv_history)
        st.markdown("**Interview history**")
        a, b = st.columns([2, 1])
        with a:
            table(hist.iloc[::-1])
        with b:
            kpi("Average score", f"{hist['Score'].mean():.0f}", f"{len(hist)} answers", "cyan")


# ---------------------------------------------------------------------------
# Study Advisor (rule-based)
# ---------------------------------------------------------------------------
def page_advisor(ctx) -> None:
    if need_job(ctx):
        return
    ss = st.session_state
    header("Study Advisor", "Guidance built from your resume, target job and gaps.")
    note("<b>Rule-based.</b> The advisor applies fixed rules to your own data. No AI/LLM is connected.")
    a, b = st.columns(2)
    with a, card("adv_plan"):
        card_title("Your priorities")
        names = {1: ("High", "red"), 2: ("Medium", "amber"), 3: ("Note", "blue")}
        for it in advice_items(ctx)[:10]:
            lab, tone = names[it["pri"]]
            html(f'<div class="item">{badge(lab, tone)} &nbsp;<b>{esc(it["area"])}</b><br>{esc(it["text"])}</div>')
    with b, card("adv_chat"):
        card_title("Ask the advisor")
        advisor = RuleBasedMentor()
        prompts = ["What should I focus on?", "How is my placement prediction?", "Which roles fit me?", "How can I improve my resume?"]
        cols = st.columns(2)
        clicked = next((q for i, q in enumerate(prompts) if cols[i % 2].button(q, key=f"mq_{i}")), None)
        typed = st.chat_input("Ask about a skill, project ideas, your resume or roles...")
        question = typed or clicked
        if question:
            ss.chat.append(("user", question))
            ss.chat.append(("assistant", advisor.respond(question, ctx)))
        for role, msg in ss.chat[-8:]:
            with st.chat_message(role):
                st.markdown(msg)


# ---------------------------------------------------------------------------
# Profile (ML inputs + account)
# ---------------------------------------------------------------------------
def number_field(key: str, ver: int, ranges: dict):
    """A number box that can never crash: its limits are the VALID range and the stored value is checked first."""
    ss = st.session_state
    label, lo, hi, step, typ = FEATURE_SPECS[key]
    clean, problem = check_value(key, ss.ml.get(key))
    if problem:
        st.warning(problem + " The stored value was not used. Please enter it again.")
        clean = None
    tag = " (from resume)" if ss.ml_src.get(key) == "resume" else ""
    r = ranges.get(key)
    help_text = f"Allowed: {lo:g}-{hi:g}." + (f" The model was trained on values from {r[0]:g} to {r[1]:g}." if r else "")
    return st.number_input(label + tag, typ(lo), typ(hi), None if clean is None else typ(clean), typ(step), help=help_text, key=f"pf_{key}_{ver}")


def page_profile(ctx) -> None:
    ss, ver = st.session_state, st.session_state.form_ver
    header("Profile", "Values for the ML placement model, plus account and data options.")
    t1, t2 = st.tabs(["Placement inputs", "Account and data"])
    with t1:
        ranges, src = training_ranges()
        for n in ss.ml_notes:
            st.warning(n)
        miss = missing_values(ss.ml)
        note(f"{17 - len(miss)} of 17 values are filled in. The placement prediction needs all of them. Values marked 'from resume' come from your "
             "verified resume (counts of projects, internships and certifications, the resume score and CGPA). Nothing is assumed: "
             "anything else you must enter yourself.")
        with st.form("profile_form"):
            new: dict = {}
            cols = st.columns(4)
            for col, (section, keys) in zip(cols, SECTIONS.items()):
                with col:
                    html(f'<div class="card-title">{section}</div>')
                    for key in keys:
                        new[key] = number_field(key, ver, ranges)
                    if section == "Career":
                        h = ss.ml.get("Hackathon")
                        sel = st.selectbox("Hackathon participation" + (" (from resume)" if ss.ml_src.get("Hackathon") == "resume" else ""),
                                           ["Yes", "No"], index=None if h is None else (0 if h else 1), placeholder="Select", key=f"pf_hack_{ver}",
                                           help="Yes = 1, No = 0, the same coding used when the model was trained.")
                        new["Hackathon"] = None if sel is None else int(sel == "Yes")
            a, b = st.columns(2)
            save = a.form_submit_button("Save profile", type="primary", **STRETCH)
            reset = b.form_submit_button("Reset profile values", **STRETCH)
        if save:
            for k, v in new.items():
                clean, problem = check_value(k, v)
                if problem:
                    st.error(problem)
                    continue
                if clean != ss.ml.get(k):
                    ss.ml_src[k] = "user"
                ss.ml[k] = clean
            log("Profile values saved")
            st.success("Profile saved.")
        if reset:
            reset_profile_inputs()
            log("Profile values reset")
            st.rerun()
        warns = range_warnings(ss.ml)
        if warns:
            html('<div class="note warn"><b>Outside the data the model was trained on (values are kept exactly as you entered them):</b><br>'
                 + "<br>".join(f"• {esc(w['field'])} = {w['value']:g} (training data covers {w['lo']:g} to {w['hi']:g})" for w in warns)
                 + "<br>Check that the value is correct. The prediction may be less reliable.</div>")
        st.caption(f"Training ranges come from the {src}.")
    with t2:
        u = ss.user
        a, b = st.columns(2)
        with a, card("acct"):
            card_title("Account")
            st.write(f"Name: **{u['name']}**")
            st.write(f"Email: **{u['email']}**")
            st.button("Log out", key="logout_profile", on_click=logout)
            st.caption("Session-based demo login for a college project; not enterprise-grade authentication.")
        with b, card("acct_actions"):
            card_title("Start over")
            if st.button("Start New Analysis", type="primary", **STRETCH):
                reset_analysis()
                st.rerun()
            st.caption("Clears your resume, target job, gaps, roadmap and progress. Values you typed in Profile are kept.")
        _, _, info = load_artifacts()
        df, ds_path = load_dataset()
        cos = load_companies()
        with card("acct_status"):
            card_title("Model and data status")
            rows = [("Placement model", "Loaded" if info["ok"] else f"Not loaded - {info.get('error')}"),
                    ("Feature order", info.get("order_check", "-")), ("Hackathon encoding", info.get("hackathon_check", "Yes = 1, No = 0")),
                    ("Training dataset", f"{len(df)} rows" if df is not None else "Not found (optional)"),
                    ("Company requirements file", f"{len(cos)} companies" if cos is not None else "Not found (optional)"),
                    ("PDF reading", "Available" if PdfReader else f"Missing: {install_hint('pypdf')}"),
                    ("DOCX reading", "Available" if Document else f"Missing: {install_hint('python-docx')}")]
            table(pd.DataFrame(rows, columns=["Item", "Status"]))
            st.caption("Version 4.0.0 | ML: placement readiness only. Everything else is rule-based. No AI/LLM is connected. Project folder: " + BASE_DIR.name)
            st.download_button("Download my analysis (JSON)", json.dumps({"resume": ss.resume["info"] if ss.resume else None, "target_job": ss.job,
                                                                           "profile_values": ss.ml}, indent=2, default=str),
                               "career_analysis.json", "application/json")