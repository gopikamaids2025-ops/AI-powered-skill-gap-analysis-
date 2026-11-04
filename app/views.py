"""Pages (part 1): Dashboard, Resume Analysis, Target Job, Skill Gap, Placement Readiness."""
from __future__ import annotations

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from job_analyzer import extract_requirements
from placement_model import LABELS, evaluate_companies, load_artifacts, missing_values, predict, training_ranges
from resume_analyzer import Document, PdfReader, ResumeReadError, analyze_resume, extract_resume_info, read_document
from roadmap import skill_progress
from state import log, sync_ml_from_resume
from ui import (STATUS_UI, badge, card, card_title, chips, gauge, go_to, header, html, kpi, note, plot,
                progress_row, table)
from utils.helpers import NOT_DETECTED, esc, install_hint
from utils.skill_database import canonicalize, detect_skills, parse_skill_lines, skill_category
from auth import validate_email


def lines_of(text: str) -> list[str]:
    return [x.strip() for x in (text or "").splitlines() if x.strip()]


def dependency_warnings() -> None:
    for pkg, ok in (("pypdf", PdfReader is not None), ("python-docx", Document is not None)):
        if not ok:
            st.warning(f"{pkg} is not installed, so that file type cannot be read. Run this command in the same terminal "
                       "window you use for Streamlit, then restart the app:")
            st.code(install_hint(pkg), language="bash")
            if pkg == "python-docx":
                st.caption("If it is installed but still fails, an unrelated package named 'docx' may be in the way. "
                           "Run `pip uninstall docx`, then install python-docx again.")


def need_resume(ctx) -> bool:
    if ctx is None:
        st.info("No resume yet. Upload and verify your resume first.")
        st.button("Go to Resume Analysis", on_click=go_to, args=("Resume Analysis",), type="primary")
        return True
    return False


def need_job(ctx) -> bool:
    if need_resume(ctx):
        return True
    if ctx["job"] is None:
        st.info("No target job yet. Enter a job description and confirm its requirements first.")
        st.button("Go to Target Job", on_click=go_to, args=("Target Job",), type="primary")
        return True
    if not ctx["an"]["rows"]:
        st.warning("The target job has no skills to compare. Add some on the Target Job page.")
        return True
    return False


# ---------------------------------------------------------------------------
# Resume Analysis
# ---------------------------------------------------------------------------
def extraction_summary(info: dict) -> None:
    fields = [("Name", info["name"]), ("Email", info["email"]), ("Phone", info["phone"]), ("LinkedIn", info["linkedin"]),
              ("GitHub", info["github"]), ("Degree", info["degree"]), ("Department", info["department"]), ("College", info["college"]),
              ("CGPA", info["cgpa"]), ("Skills", f"{len(info['skills'])} found" if info["skills"] else ""),
              ("Internships", f"{len(info['internships'])} found" if info["internships"] else ""),
              ("Other experience", f"{len(info['experience'])} found" if info["experience"] else ""),
              ("Projects", f"{len(info['projects'])} found" if info["projects"] else ""),
              ("Certifications", f"{len(info['certifications'])} found" if info["certifications"] else ""),
              ("Hackathons", f"{len(info['hackathons'])} found" if info["hackathons"] else "")]
    cols = st.columns(3)
    for i, (label, val) in enumerate(fields):
        shown = esc(val) if val else badge(NOT_DETECTED, "amber")
        cols[i % 3].markdown(f'<div class="item"><b>{label}</b><br>{shown}</div>', unsafe_allow_html=True)


def resume_editor(data: dict, confirming: bool, key: str) -> None:
    """Editable form for the extracted information. Nothing is used for analysis until the student confirms it."""
    ss, info, ver = st.session_state, data["info"], st.session_state.resume_ver
    note("Extraction is rule-based and not 100% accurate. Please check every field, fix mistakes and add anything we missed.")
    with st.form(f"resume_form_{key}"):
        a, b, c = st.columns(3)
        name = a.text_input("Name", info["name"], placeholder=NOT_DETECTED, key=f"{key}_name_{ver}")
        email = b.text_input("Email", info["email"], placeholder=NOT_DETECTED, key=f"{key}_email_{ver}")
        phone = c.text_input("Phone", info["phone"], placeholder=NOT_DETECTED, key=f"{key}_phone_{ver}")
        a, b = st.columns(2)
        linkedin = a.text_input("LinkedIn", info["linkedin"], placeholder=NOT_DETECTED, key=f"{key}_li_{ver}")
        github = b.text_input("GitHub", info["github"], placeholder=NOT_DETECTED, key=f"{key}_gh_{ver}")
        a, b, c, d = st.columns(4)
        degree = a.text_input("Degree", info["degree"], placeholder=NOT_DETECTED, key=f"{key}_deg_{ver}")
        dept = b.text_input("Course / department", info["department"], placeholder=NOT_DETECTED, key=f"{key}_dep_{ver}")
        college = c.text_input("College", info["college"], placeholder=NOT_DETECTED, key=f"{key}_col_{ver}")
        cgpa = d.text_input("CGPA / percentage", info["cgpa"], placeholder=NOT_DETECTED, key=f"{key}_cg_{ver}")
        skills = st.text_area("Skills (one per line; keep only skills you really have)", "\n".join(info["skills"]), height=150,
                              placeholder=NOT_DETECTED, key=f"{key}_sk_{ver}")
        a, b = st.columns(2)
        interns = a.text_area("Internships (one per line)", "\n".join(info["internships"]), height=100, placeholder=NOT_DETECTED, key=f"{key}_in_{ver}")
        exp = b.text_area("Other work experience (one per line)", "\n".join(info["experience"]), height=100, placeholder=NOT_DETECTED, key=f"{key}_ex_{ver}")
        a, b = st.columns(2)
        proj = a.text_area("Projects (one per line: Name — technologies)", "\n".join(
            p["name"] + (" — " + ", ".join(p["tech"]) if p["tech"] else "") for p in info["projects"]), height=110,
            placeholder=NOT_DETECTED, key=f"{key}_pr_{ver}")
        certs = b.text_area("Certifications (one per line)", "\n".join(info["certifications"]), height=110, placeholder=NOT_DETECTED, key=f"{key}_ce_{ver}")
        a, b = st.columns(2)
        hacks = a.text_area("Hackathons you really took part in (one per line; leave empty if none)", "\n".join(info["hackathons"]), height=90,
                            placeholder="None detected", key=f"{key}_hk_{ver}")
        other = b.text_area("Other relevant information", info["other"], height=90, placeholder=NOT_DETECTED, key=f"{key}_ot_{ver}")
        st.caption("Only entries in 'Internships' are counted as internships, and the app never assumes hackathon participation unless you list it.")
        submitted = st.form_submit_button("Confirm resume information" if confirming else "Save changes", type="primary")
    if not submitted:
        return
    err = validate_email(email) if email.strip() else None
    if not err and cgpa.strip() and not re.fullmatch(r"\d{1,3}(\.\d{1,2})?\s*%?", cgpa.strip()):
        err = "CGPA must be a number such as 8.5, or a percentage such as 82%."
    if not err and cgpa.strip() and "%" not in cgpa and float(cgpa) > 10:
        err = "CGPA must be 10 or below (use a % sign for percentages)."
    if err:
        st.error(err)
        return
    projects = []
    for line in lines_of(proj):
        parts = re.split(r"\s+[—|–]\s+|\s+-\s+", line, maxsplit=1)
        tech = [canonicalize(t) for t in re.split(r"[,;]", parts[1]) if t.strip()] if len(parts) > 1 else detect_skills(line)
        old = next((p for p in info["projects"] if p["name"] == parts[0].strip()), None)
        projects.append({"name": parts[0].strip(), "tech": tech, "detail": old["detail"] if old else line})
    new = dict(name=name.strip(), email=email.strip(), phone=phone.strip(), linkedin=linkedin.strip(), github=github.strip(),
               degree=degree.strip(), department=dept.strip(), college=college.strip(), cgpa=cgpa.strip(),
               skills=parse_skill_lines(skills), internships=lines_of(interns), experience=lines_of(exp), projects=projects,
               certifications=lines_of(certs), hackathons=lines_of(hacks), other=other.strip())
    ss.resume = {"text": data["text"], "source": data["source"], "info": new, "quality": analyze_resume(data["text"])}
    ss.resume_draft = None
    ss.resume_ver += 1
    sync_ml_from_resume()
    log(f"Resume verified ({len(new['skills'])} skills)")
    if not new["skills"]:
        st.warning("No skills are listed. Add your skills on the Resume Analysis page so they can be compared with a job.")
    st.rerun()


def resume_upload_card() -> None:
    ss = st.session_state
    with card("resume_upload"):
        card_title("Upload your resume")
        up = st.file_uploader("PDF, DOCX or TXT", type=["pdf", "docx", "txt"], key=f"rup_{ss.resume_ver}")
        pasted = st.text_area("...or paste your resume text", height=150, key=f"rpaste_{ss.resume_ver}")
        dependency_warnings()
        if st.button("Extract information", type="primary", key="btn_extract_resume"):
            try:
                if up is not None:
                    text, source = read_document(up), up.name
                else:
                    text, source = pasted, "Pasted text"
                    if len(text.strip()) < 30:
                        raise ResumeReadError("Nothing to analyse yet. Upload a resume file or paste your resume text (at least a few lines).")
            except ResumeReadError as exc:
                st.error(str(exc))
                return
            ss.resume_draft = {"text": text, "source": source, "info": extract_resume_info(text)}
            ss.resume_ver += 1
            st.rerun()


def page_resume(ctx) -> None:
    ss = st.session_state
    header("Resume Analysis", "See what was extracted from your resume, verify it, and run a quality check.")
    note("Both parts are rule-based (pattern and keyword checks). No AI/LLM reads your resume, and extraction can make mistakes.")
    if ss.resume_draft:
        with card("res_draft"):
            card_title("Step 2: Check what was found")
            st.caption(f"Source: {ss.resume_draft['source']}")
            extraction_summary(ss.resume_draft["info"])
            with st.expander("Show the text the app read from your file (check this if something looks wrong)"):
                st.text_area("Extracted text", ss.resume_draft["text"], height=220, disabled=True, key=f"raw_draft_{ss.resume_ver}")
                st.caption("If this text is jumbled or missing parts (common with two-column or designed PDFs), paste your resume text instead.")
            if not ss.resume_draft["info"]["skills"]:
                st.warning("No known skills were detected. Add your skills in the form below.")
        resume_editor(ss.resume_draft, True, "res")
        if st.button("Cancel and upload a different resume"):
            ss.resume_draft = None
            ss.resume_ver += 1
            st.rerun()
        return
    if ctx is None:
        resume_upload_card()
        return
    info, q = ctx["info"], ctx["quality"]
    for n in ss.ml_notes:
        st.warning(n)
    t1, t2, t3 = st.tabs(["Extracted information", "Resume quality", "Replace resume"])
    with t1:
        st.markdown(f"Status: {badge('Verified', 'green')} &nbsp; source: {esc(ss.resume['source'])}", unsafe_allow_html=True)
        extraction_summary(info)
        with st.expander("Show the text the app read from your file"):
            st.text_area("Extracted text", ss.resume["text"], height=220, disabled=True, key=f"raw_saved_{ss.resume_ver}")
        a, b = st.columns(2)
        with a, card("res_skills"):
            card_title(f"Skills ({len(info['skills'])})")
            groups: dict[str, list[str]] = {}
            for s in info["skills"]:
                groups.setdefault(skill_category(s), []).append(s)
            for cat, items in groups.items():
                html(f"<small style='color:#9FB0E0'>{esc(cat)}</small><br>" + chips(items, "cyan" if cat != "Soft Skill" else "blue"))
            if not groups:
                st.caption(NOT_DETECTED)
        with b, card("res_proj"):
            card_title("Projects, internships and certifications")
            for p in info["projects"]:
                html(f'<div class="item"><b>Project: {esc(p["name"])}</b><br>{esc(", ".join(p["tech"])) or "technologies not detected"}</div>')
            for e in info["internships"]:
                html(f'<div class="item"><b>Internship:</b> {esc(e[:160])}</div>')
            for e in info["experience"]:
                html(f'<div class="item"><b>Experience:</b> {esc(e[:160])}</div>')
            for c in info["certifications"]:
                html(f'<div class="item"><b>Certification:</b> {esc(c)}</div>')
            for h in info["hackathons"]:
                html(f'<div class="item"><b>Hackathon:</b> {esc(h)}</div>')
        with st.expander("Edit extracted information"):
            resume_editor({"text": ss.resume["text"], "source": ss.resume["source"], "info": info}, False, "edit")
    with t2:
        a, b = st.columns([1, 2])
        with a, card("res_score"):
            card_title("Resume quality score")
            gauge(q["score"], "res_gauge", f"{q['words']} words", 230)
            st.caption("Rule-based. This score is also used as the 'Resume score' input of the ML placement model.")
        with b, card("res_breakdown"):
            card_title("Score breakdown")
            for k, (v, mx) in q["parts"].items():
                progress_row(k, 100 * v / mx, f"{v:.0f}/{mx}")
        a, b = st.columns(2)
        with a, card("res_sections"):
            card_title("Sections detected")
            html("".join(f'<div class="item">{esc(s)} &nbsp;{badge("Detected", "green")}</div>' for s, f in q["sections"].items() if f) or "None")
            card_title("Missing sections")
            html("".join(f'<div class="item">{esc(s)} &nbsp;{badge("Missing", "red")}</div>' for s, f in q["sections"].items() if not f) or "None")
        with b, card("res_tips"):
            card_title("Suggestions")
            for t in q["tips"] or ["No major issues detected."]:
                html(f'<div class="item">{esc(t)}</div>')
    with t3:
        resume_upload_card()


# ---------------------------------------------------------------------------
# Target Job
# ---------------------------------------------------------------------------
def job_summary(job: dict) -> None:
    a, b = st.columns(2)
    with a, card("job_req"):
        card_title("Required")
        html("".join(f'<div class="item">✓ {esc(s)}</div>' for s in job["required"]) or "<small>No required skills</small>")
        if job["education"]:
            html(f'<div class="item"><b>Education:</b> {esc(job["education"])}</div>')
        if job["experience"]:
            html(f'<div class="item"><b>Experience:</b> {esc(job["experience"])}</div>')
        if job["cgpa_min"]:
            html(f'<div class="item"><b>Minimum CGPA:</b> {job["cgpa_min"]:g}</div>')
        for c in job["cert_required"]:
            html(f'<div class="item"><b>Certification:</b> {esc(c)}</div>')
    with b, card("job_pref"):
        card_title("Preferred (nice to have)")
        html("".join(f'<div class="item">○ {esc(s)}</div>' for s in job["preferred"]) or "<small>No preferred skills</small>")
        for c in job["cert_preferred"]:
            html(f'<div class="item"><b>Certification:</b> {esc(c)}</div>')


def page_target(ctx) -> None:
    ss = st.session_state
    header("Target Job", "Enter the job you are preparing for, check the extracted requirements, then compare.")
    if ctx is None:
        note("Tip: upload and verify your resume first (Resume Analysis). You can still prepare the job requirements now.", warn=True)
    base, ver = ss.job_draft or ss.job or {}, ss.job_ver
    with card("job_input"):
        card_title("Step 3: Job and requirements")
        a, b = st.columns(2)
        role = a.text_input("Target job role", base.get("role", ""), placeholder="e.g. Software Developer", key=f"role_{ver}")
        company = b.text_input("Company (optional)", base.get("company", ""), key=f"company_{ver}")
        up = st.file_uploader("Upload the job description (PDF, DOCX or TXT)", type=["pdf", "docx", "txt"], key=f"jup_{ver}")
        text = st.text_area("...or paste the job description / requirements", base.get("text", ""), height=200, key=f"jtxt_{ver}",
                            placeholder="Required:\nPython\nSQL\nGit\n\nPreferred:\nAWS\nDocker")
        dependency_warnings()
        if st.button("Extract requirements", type="primary", key="btn_extract_job"):
            if not role.strip():
                st.error("Please enter the target job role.")
                return
            try:
                body, source = (read_document(up), up.name) if up is not None else (text, "Pasted text")
            except ResumeReadError as exc:
                st.error(str(exc))
                return
            if len(body.strip()) < 3:
                st.error("No job description entered. Paste the requirements or upload a file.")
                return
            reqs = extract_requirements(body, role)
            if not (reqs["required"] or reqs["preferred"]):
                st.warning("No skills were recognised in this text. You can add requirements by hand in the next step.")
            ss.job_draft = {"role": role.strip(), "company": company.strip(), "source": source, "text": body, **reqs}
            ss.job_ver += 1
            st.rerun()
    d = ss.job_draft
    if d:
        with card("job_verify"):
            card_title("Step 4: Verify and edit the requirements")
            note("The text you provided is the source of truth. Only things found in it are listed. Add what we missed and remove what is wrong. "
                 "A line that says 'preferred', 'nice to have' or 'a plus' makes its skills Preferred.")
            with st.form("job_form"):
                a, b = st.columns(2)
                req = a.text_area("Required skills (one per line)", "\n".join(d["required"]), height=170, key=f"req_{ver}")
                pref = b.text_area("Preferred skills (one per line)", "\n".join(d["preferred"]), height=170, key=f"pref_{ver}")
                a, b = st.columns(2)
                edu = a.text_input("Education requirement", d["education"], placeholder="e.g. B.Tech / B.E.", key=f"edu_{ver}")
                exp = b.text_input("Experience requirement", d["experience"], placeholder="e.g. 0-2 years", key=f"exp_{ver}")
                a, b, c = st.columns(3)
                cgpa = a.number_input("Minimum CGPA (optional)", 0.0, 10.0, d["cgpa_min"], 0.1, key=f"cg_{ver}")
                cert_r = b.text_area("Required certifications (one per line)", "\n".join(d["cert_required"]), height=80, key=f"cr_{ver}")
                cert_p = c.text_area("Preferred certifications (one per line)", "\n".join(d["cert_preferred"]), height=80, key=f"cp_{ver}")
                go_ = st.form_submit_button("Confirm requirements", type="primary")
        if go_:
            required, preferred = parse_skill_lines(req), parse_skill_lines(pref)
            preferred = [p for p in preferred if p.lower() not in {r.lower() for r in required}]
            if not required and not preferred:
                st.error("Add at least one skill so a comparison is possible.")
            else:
                ss.job = {**d, "required": required, "preferred": preferred, "education": edu.strip(), "experience": exp.strip(),
                          "cgpa_min": cgpa or None, "cert_required": lines_of(cert_r), "cert_preferred": lines_of(cert_p)}
                ss.job_draft = None
                ss.job_ver += 1
                ss.roadmap_done, ss.progress_log = {}, []
                log(f"Target job set: {ss.job['role']}")
                st.rerun()
    elif ss.job:
        st.markdown(f"Target: **{esc(ss.job['role'])}**" + (f" at **{esc(ss.job['company'])}**" if ss.job["company"] else "")
                    + f" &nbsp; {badge('Requirements confirmed', 'green')}", unsafe_allow_html=True)
        job_summary(ss.job)
        if st.button("Edit these requirements"):
            ss.job_draft = dict(ss.job)
            ss.job_ver += 1
            st.rerun()


# ---------------------------------------------------------------------------
# Skill Gap
# ---------------------------------------------------------------------------
def page_skill_gap(ctx) -> None:
    if need_job(ctx):
        return
    an, job = ctx["an"], ctx["job"]
    header("Skill Gap", f"Your verified resume compared with the <b>{esc(job['role'])}</b> job requirements.")
    bd = an["breakdown"]
    a, b = st.columns([1, 2])
    with a, card("sg_match"):
        card_title("Job Requirement Match")
        gauge(an["match"], "sg_gauge", "Resume-to-Job Match", 230)
        st.caption("How well your resume covers this job's skill list. It is NOT a chance of being hired.")
    with b, card("sg_how"):
        card_title("How the percentage is calculated")
        html("<div style='font-size:13.5px;color:#DDE6FF'>Each requirement earns <b>1 point</b> for MATCH, <b>0.5</b> for PARTIAL and <b>0</b> for GAP. "
             "<b>Required</b> skills count <b>twice</b> as much as <b>Preferred</b> skills.<br>"
             "Match % = (2 × required points + 1 × preferred points) ÷ (2 × required skills + 1 × preferred skills)</div>")
        table(pd.DataFrame([{"Group": p["group"], "Skills": p["count"], "Weight": p["weight"], "Points earned": p["points"],
                             "Weighted": f"{p['weight'] * p['points']:g} / {p['weight'] * p['possible']:g}"} for p in bd["parts"]]))
        st.caption("Rule-based and separate from the ML placement prediction and from the career role recommendations.")
    c = st.columns(4)
    for col, (title, rows, tone) in zip(c, [("Matched skills", an["matched"], "green"), ("Partial skills", an["partial"], "amber"),
                                            ("Missing required skills", an["missing_required"], "red"),
                                            ("Missing preferred skills", an["missing_preferred"], "blue")]):
        with col, card("sg_" + title.split()[0].lower() + title.split()[1].lower()):
            card_title(f"{title} ({len(rows)})")
            html(chips([r["skill"] for r in rows], tone))
    with card("sg_chart"):
        card_title("Match status by requirement type")
        fig = go.Figure([go.Bar(name=s, x=["Required", "Preferred"], y=[sum(r["status"] == s and r["level"] == lv for r in an["rows"]) for lv in ("Required", "Preferred")],
                                marker_color=STATUS_UI[s][2]) for s in ("MATCH", "PARTIAL", "GAP")])
        fig.update_layout(barmode="stack")
        plot(fig, "sg_chart_fig", 250)
    st.markdown("#### Requirement by requirement")
    table(pd.DataFrame([{"Requirement": r["skill"], "Type": r["level"], "Student Status": r["status"], "Evidence": r["evidence"]} for r in an["rows"]]))
    st.caption("MATCH = shown in your Skills section or used in a project/experience. PARTIAL = only mentioned in passing, or only a related skill found. "
               "GAP = not found. A loosely related word never counts as a MATCH.")
    if an["checklist"]:
        st.markdown("#### Other requirements")
        table(pd.DataFrame([{"Requirement": c["requirement"], "Status": c["status"], "Details": c["detail"]} for c in an["checklist"]]))
        st.caption("'Verify' means the app cannot decide automatically. Please check it yourself.")


# ---------------------------------------------------------------------------
# Placement Readiness (ML) - independent of the job comparison
# ---------------------------------------------------------------------------
def page_readiness(ctx) -> None:
    ss = st.session_state
    header("Placement Readiness", "A prediction from the trained ML model, based on your numeric profile values.")
    note("<b>ML-based.</b> This uses your profile values only. It is separate from the resume-to-job match and from career role recommendations.")
    ml = ss.ml
    miss = missing_values(ml)
    _, _, info = load_artifacts()
    if not info["ok"]:
        st.error(f"The prediction model could not be loaded. {info.get('error') or ''} Make sure placement_model.pkl and scaler.pkl are in the models folder.")
        return
    if miss:
        note("The model needs every profile value. Still missing: <b>" + ", ".join(LABELS[f] for f in miss) + "</b>.", warn=True)
        st.button("Complete Profile", on_click=go_to, args=("Profile",), type="primary")
        return
    p = ctx["pred"] if ctx else None
    if p is None:
        p = predict(ml)
    if not p:
        return
    ok = p["label"] == 1
    a, b = st.columns([1.2, 1])
    with a:
        bg = "linear-gradient(135deg,#0E9F6E,#047857)" if ok else "linear-gradient(135deg,#D97706,#B45309)"
        html(f'<div class="banner" style="background:{bg}"><div class="t">Placement Readiness Prediction</div><div class="v">{"READY" if ok else "NOT READY"}</div></div>')
    with b:
        kpi("Model confidence", f"{p['confidence']:.0f}%" if p["confidence"] is not None else "n/a", "model output", "cyan")
    note("Model confidence is how sure the model is about its own answer. It is a model output, <b>not a guarantee</b> of placement.", warn=True)
    if p["warnings"]:
        html('<div class="note warn"><b>Some values are outside the data this model was trained on, so the result is less reliable:</b><br>'
             + "<br>".join(f"• {esc(w['field'])} = {w['value']:g} (training data covers {w['lo']:g} to {w['hi']:g})" for w in p["warnings"]) + "</div>")
    a, b = st.columns(2)
    with a, card("pred_gauge"):
        card_title("Chance the model gives to READY")
        if p["p_ready"] is not None:
            gauge(p["p_ready"], "pred_gauge_fig", "P(READY)")
    with b, card("pred_factors"):
        card_title("Key factors in this prediction")
        if p["contrib"] is not None:
            c = p["contrib"].sort_values("Contribution")
            fig = go.Figure(go.Bar(x=c["Contribution"], y=c["Feature"], orientation="h", marker_color=["#F87171" if v < 0 else "#4ADE80" for v in c["Contribution"]]))
            plot(fig, "pred_factors_fig", 300)
            st.caption("Green bars push toward READY; red bars push toward NOT READY.")
    with st.expander("Values sent to the model"):
        ranges, src = training_ranges()
        rows = []
        for f in info["feature_order"]:
            r = ranges.get(f)
            rows.append({"Value": LABELS[f], "Entered": ("Yes" if ml[f] else "No") if f == "Hackathon" else f"{ml[f]:g}",
                         "Training range": "Yes / No" if r is None else f"{r[0]:g} - {r[1]:g}",
                         "Source": "From resume (verified)" if ss.ml_src.get(f) == "resume" else "Entered by you"})
        table(pd.DataFrame(rows))
        st.caption(f"Feature order: {info.get('order_check', '')}. Training ranges come from the {src}.")
    cos = evaluate_companies(ml)
    with st.expander("Optional: company benchmarks (company_requirements.csv)"):
        if cos is None:
            st.info("company_requirements.csv was not found in the data folder, so this optional section is empty.")
        else:
            st.caption("Compares your numeric profile values with each company's minimums. This is separate from the job analysis.")
            table(pd.DataFrame([{"Company": c["company"], "Status": c["status"], "Match %": None if c["match"] is None else round(c["match"]),
                                 "Short by": ", ".join(f"{n} (+{req - cur:g})" for n, cur, req in c["missing"]),
                                 "Needs your input": ", ".join(c["unknown"])} for c in cos]))
            st.caption("A company's minimums are not a guarantee of selection.")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def page_dashboard(ctx) -> None:
    ss = st.session_state
    header("Placement Readiness Dashboard", f"Welcome, {esc(ss.user['name'])}.")
    steps = [("Resume uploaded and verified", ctx is not None, "Resume Analysis"),
             ("Target job and requirements confirmed", ss.job is not None, "Target Job"),
             ("Placement profile values complete", not missing_values(ss.ml), "Profile")]
    if not all(done for _, done, _ in steps):
        with card("dash_steps"):
            card_title("Getting started")
            for i, (label, done, page) in enumerate(steps):
                a, b = st.columns([4, 1])
                a.markdown(f"{'✅' if done else '⬜'} {label}")
                if not done:
                    b.button("Open", key=f"step_{i}", on_click=go_to, args=(page,))
    if ctx is None:
        return
    info, an, p = ctx["info"], ctx["an"], ctx["pred"]
    req_rows = [r for r in an["rows"] if r["level"] == "Required"] if an else []
    c = st.columns(5)
    with c[0]:
        kpi("Resume", "✓ Verified", f"{len(info['skills'])} skills found", "green")
    with c[1]:
        kpi("Target role", ss.job["role"] if ss.job else "Not set", ss.job["company"] if ss.job and ss.job["company"] else "", "cyan")
    with c[2]:
        kpi("Job match", f"{an['match']:.0f}%" if an and an["match"] is not None else "-", "resume vs job", "blue")
    with c[3]:
        kpi("Placement readiness", ("READY" if p["label"] == 1 else "NOT READY") if p else "Not available", "ML prediction" if p else "complete Profile", "green" if p and p["label"] == 1 else "amber")
    with c[4]:
        kpi("Model confidence", f"{p['confidence']:.0f}%" if p and p["confidence"] is not None else "-", "model output", "cyan")
    st.write("")
    a, b = st.columns(2)
    with a, card("dash_required"):
        card_title("Required skills")
        if an:
            m = sum(r["status"] == "MATCH" for r in req_rows)
            pa = sum(r["status"] == "PARTIAL" for r in req_rows)
            g = sum(r["status"] == "GAP" for r in req_rows)
            html(f'<div class="item"><b>{m}</b> matched &nbsp; <b>{pa}</b> partial &nbsp; <b>{g}</b> missing</div>')
            fig = go.Figure(go.Pie(labels=["Matched", "Partial", "Missing"], values=[m, pa, g], hole=0.62, sort=False,
                                   marker=dict(colors=["#4ADE80", "#FBBF24", "#F87171"]), textinfo="value"))
            plot(fig, "dash_pie", 210)
        else:
            st.caption("Add a target job to see how your resume matches its requirements.")
    with b, card("dash_gaps"):
        card_title("Top skill gaps")
        if an:
            if not ctx["gaps"]:
                st.success("Your resume currently covers all detected requirements.")
            for r in ctx["gaps"][:5]:
                html(f'<div class="item"><b>{esc(r["skill"])}</b> &nbsp;{badge(r["level"], "red" if r["level"] == "Required" else "blue")} '
                     f'{badge(r["status"], STATUS_UI[r["status"]][1])}</div>')
        else:
            st.caption("No target job yet.")
    a, b = st.columns(2)
    top = ctx["roles"][0] if ctx["roles"] else None
    with a, card("dash_role"):
        card_title("Recommended career role")
        if top and top["pct"] > 0:
            html(f'<div class="item"><b>{esc(top["role"])}</b> &nbsp;{badge(f"{top['pct']:.0f}% role-skill match", "cyan")}</div>')
            st.caption("From the app's predefined role-skill database. Not a job vacancy.")
        else:
            st.caption("Not enough skills detected to suggest a role.")
        st.button("See Career Roles", on_click=go_to, args=("Career Roles",))
    with b, card("dash_next"):
        card_title("Progress toward your roadmap")
        if ctx["road"]:
            done = sum(skill_progress(w["skill"], ss.roadmap_done)[0] for w in ctx["road"])
            total = sum(skill_progress(w["skill"], ss.roadmap_done)[1] for w in ctx["road"])
            progress_row(f"{len(ctx['road'])} skills to learn", 100 * done / total, f"{done}/{total} items")
            st.button("Open Roadmap", on_click=go_to, args=("Roadmap",))
        else:
            st.caption("No roadmap yet: it appears once you have a target job with gaps.")
    note("Job match, ML placement readiness and career role recommendations are three separate calculations. None of them guarantees a job.")
