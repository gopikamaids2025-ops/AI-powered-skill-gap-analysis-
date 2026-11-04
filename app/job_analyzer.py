"""Target Job: extract REQUIRED and PREFERRED requirements from the job description the student provides.

The student's own text is the source of truth. Only things found in that text are listed, and the student can edit
every list before the comparison runs.
"""
from __future__ import annotations

import re

from utils.skill_database import detect_skills

BULLET = r"^[\s•*▪●○◦‣\-–—]+"
PREF_CUE = re.compile(r"preferred|nice[- ]to[- ]have|good[- ]to[- ]have|a plus\b|\bplus\b|bonus|desirable|optional|added advantage|\badvantage\b", re.I)
REQ_CUE = re.compile(r"required|requirements?|must[- ]have|mandatory|qualifications?|skills?|responsibilities|eligibility|looking for|essential|you will need|what you.ll need", re.I)
EDU_REQ = re.compile(r"\b(b\.?\s?tech|(?-i:B\.\s?E\b|BE\b)|bachelor|b\.?\s?sc|bca|m\.?\s?tech|master|mba|mca|m\.?\s?sc|degree|graduat\w*|diploma)\b", re.I)
YEARS_REQ = re.compile(r"(\d+)\s*(?:\+|[-–]\s*\d+|to\s*\d+)?\s*(?:years?|yrs?)\b|\bfreshers?\b|\bentry[- ]level\b", re.I)
CGPA_REQ = re.compile(r"(\d(?:\.\d+)?)\s*\+?\s*(?:cgpa|gpa)|(?:cgpa|gpa)[^0-9\n]{0,25}(\d(?:\.\d+)?)", re.I)
NOT_SKILL_WORDS = {"strong", "good", "excellent", "knowledge", "understanding", "ability", "experience", "years", "skills", "team",
                   "work", "working", "proficiency", "familiarity", "hands", "degree", "passionate", "about", "with", "of", "in",
                   "to", "the", "a", "an", "we", "you", "will", "must", "should", "required", "preferred", "role", "responsibilities",
                   "candidate", "candidates", "ideal", "looking", "join", "company", "benefits", "salary", "location", "apply",
                   "minimum", "maximum", "cgpa", "gpa", "percent", "percentage", "marks"}


def empty_requirements() -> dict:
    return {"required": [], "preferred": [], "education": "", "experience": "", "cert_required": [], "cert_preferred": [], "cgpa_min": None}


def extract_requirements(text: str, role: str = "") -> dict:
    """Return required/preferred skills plus education, experience, certification and CGPA requirements."""
    out = empty_requirements()
    required, preferred = out["required"], out["preferred"]
    edu, exp = [], []
    raw_lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln.strip()]
    short = [ln for ln in raw_lines if len(ln.split()) <= 4]
    list_like = len(raw_lines) >= 2 and len(short) / len(raw_lines) >= 0.6
    mode, explicit = "required", list_like
    for raw in raw_lines:
        body = re.sub(r"^\d+[.)]\s+", "", re.sub(BULLET, "", raw)).strip()
        if not body or (role and body.lower() == role.strip().lower()):
            continue
        skills = detect_skills(body)
        heading = len(body) <= 70 and (body.endswith(":") or (not skills and len(body.split()) <= 6 and
                                                                (PREF_CUE.search(body) or REQ_CUE.search(body))))
        if heading:
            explicit = True
            if PREF_CUE.search(body):
                mode = "preferred"
            elif REQ_CUE.search(body):
                mode = "required"
            continue
        line_mode = "preferred" if PREF_CUE.search(body) else mode
        if EDU_REQ.search(body):
            edu.append(body)
        if (m := CGPA_REQ.search(body)) and out["cgpa_min"] is None:
            v = float(m.group(1) or m.group(2))
            out["cgpa_min"] = v if 0 < v <= 10 else None
        if YEARS_REQ.search(body):
            exp.append(body)
        if re.search(r"certif", body, re.I):
            (out["cert_preferred"] if line_mode == "preferred" else out["cert_required"]).append(body)
        found = list(skills)
        if explicit and not skills and len(body) <= 60 and not body.endswith(".") and not EDU_REQ.search(body):
            for item in re.split(r"[,;/|]", body):
                item = item.strip(" -•*:.")
                words = re.findall(r"[A-Za-z0-9+#.]+", item)
                if (1 <= len(words) <= 3 and re.fullmatch(r"[A-Za-z][A-Za-z0-9 .+#&/\-]*", item)
                        and not {w.lower() for w in words} & NOT_SKILL_WORDS and not re.search(r"certif", item, re.I)
                        and not CGPA_REQ.search(item) and not YEARS_REQ.search(item)
                        and not any(re.fullmatch(r"[\d.]+\+?", w) for w in words)):
                    found.append(item)
        for s in found:
            if line_mode == "preferred":
                if s.lower() not in {x.lower() for x in required + preferred}:
                    preferred.append(s)
            else:
                if s.lower() not in {x.lower() for x in required}:
                    required.append(s)
                preferred[:] = [p for p in preferred if p.lower() != s.lower()]
    out["education"] = edu[0] if edu else ""
    out["experience"] = exp[0] if exp else ""
    out["cert_required"], out["cert_preferred"] = out["cert_required"][:4], out["cert_preferred"][:4]
    return out