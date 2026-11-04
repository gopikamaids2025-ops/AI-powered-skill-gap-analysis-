"""Skill Gap: compare the student's VERIFIED resume with the target job requirements.

Exactly three states are used for every requirement:

  MATCH    the skill is in the verified resume AND the resume shows it: listed in the Skills section, used in a
           project / internship / experience / certification, or added by the student during verification.
  PARTIAL  either (a) the skill is only mentioned somewhere in the resume text, with no Skills-section entry and no
           project/experience evidence, or (b) the skill itself is missing but a RELATED skill is present
           (for example MySQL for SQL).
  GAP      nothing relevant was found.

Job Requirement Match % = (2 x points of Required skills + 1 x points of Preferred skills) / (2 x #Required + 1 x #Preferred)
where MATCH = 1 point, PARTIAL = 0.5 point and GAP = 0 points.  It describes how well the resume covers THIS job's
skill list. It is not a chance of being hired and it has nothing to do with the ML placement prediction.
"""
from __future__ import annotations

import re

from resume_analyzer import cgpa_number, split_sections
from utils.skill_database import RELATED, SKILL_PATTERNS, find_evidence, mentions, skill_category

STATUS_SCORE = {"MATCH": 1.0, "PARTIAL": 0.5, "GAP": 0.0}
WEIGHT = {"Required": 2, "Preferred": 1}


def evidence_context(info: dict, text: str) -> dict:
    """Collect WHERE each skill appears in the verified resume."""
    sec = split_sections(text)
    applied: list[tuple[str, str]] = []  # (label, text) places where a skill is actually used
    for p in info["projects"]:
        applied.append((f"project '{p['name']}'", " ".join([p["name"], ", ".join(p.get("tech", [])), p.get("detail", "")])))
    for e in info["internships"]:
        applied.append(("an internship", e))
    for e in info["experience"]:
        applied.append(("work experience", e))
    for c in info["certifications"]:
        applied.append(("a certification", c))
    for h in info.get("hackathons", []):
        applied.append(("a hackathon", h))
    return {"text": text, "skills_text": "\n".join(sec.get("skills", [])), "applied": applied,
            "have": {s.lower() for s in info["skills"]}}


def skill_status(skill: str, ev: dict) -> tuple[str, str, list[str]]:
    """Return (MATCH | PARTIAL | GAP, evidence sentence, related skills found)."""
    key = skill.lower()
    in_text = mentions(skill, ev["text"])
    # Skills in the database follow the student's VERIFIED list (the student may have removed or added items).
    # Skills not in the database (custom requirements) are searched for in the resume text.
    verified = key in ev["have"] or (skill not in SKILL_PATTERNS and in_text)
    if verified:
        where = []
        if mentions(skill, ev["skills_text"]):
            where.append("listed in the Skills section")
        used = [label for label, t in ev["applied"] if mentions(skill, t)]
        if used:
            where.append("used in " + ", ".join(dict.fromkeys(used[:2])))
        if key in ev["have"] and not in_text:
            where.append("added by you during verification")
        if where:
            text = "; ".join(where)
            return "MATCH", text[0].upper() + text[1:], []
        line = find_evidence(ev["text"], skill)
        return "PARTIAL", "Mentioned in the resume but not in the Skills section or any project/experience" + (f': "{line}"' if line else ""), []
    related = [r for r in RELATED.get(skill, []) if r.lower() in ev["have"]]
    if related:
        return "PARTIAL", f"Related skill found: {', '.join(related)}. {skill} itself was not found.", related
    return "GAP", "Not found in the resume", []


def compare_skills(info: dict, text: str, job: dict) -> list[dict]:
    ev = evidence_context(info, text)
    rows = []
    for level, skills in (("Required", job["required"]), ("Preferred", job["preferred"])):
        for s in skills:
            status, evidence, related = skill_status(s, ev)
            rows.append(dict(skill=s, category=skill_category(s), level=level, status=status, evidence=evidence, related=related))
    return rows


def match_breakdown(rows: list[dict], completed: set | frozenset = frozenset()) -> dict:
    """The Job Requirement Match % with every number shown, so the score can be explained."""
    parts, total_w, total_p = [], 0.0, 0.0
    for level in ("Required", "Preferred"):
        sel = [r for r in rows if r["level"] == level]
        pts = sum(1.0 if r["skill"] in completed else STATUS_SCORE[r["status"]] for r in sel)
        parts.append(dict(group=level, count=len(sel), weight=WEIGHT[level], points=pts, possible=len(sel)))
        total_w += WEIGHT[level] * len(sel)
        total_p += WEIGHT[level] * pts
    return {"percent": 100 * total_p / total_w if total_w else None, "parts": parts}


def degree_level(text: str) -> int:
    if re.search(r"master|m\.?\s?tech|\bmba\b|\bmca\b|m\.?\s?sc", text, re.I):
        return 3
    if re.search(r"bachelor|b\.?\s?tech|(?-i:B\.\s?E\b|BE\b)|b\.?\s?sc|\bbca\b|b\.?\s?com", text, re.I):
        return 2
    return 1 if re.search(r"diploma", text, re.I) else 0


def experience_minimum(text: str) -> int | None:
    if not text:
        return None
    if re.search(r"fresher|entry[- ]level", text, re.I):
        return 0
    m = re.search(r"(\d+)\s*(?:\+|[-–]\s*\d+|to\s*\d+)?\s*(?:years?|yrs?)", text, re.I)
    return int(m.group(1)) if m else None


def requirement_checklist(info: dict, job: dict) -> list[dict]:
    """Non-skill requirements: education, CGPA, experience, certifications. Status: Met / Not met / Verify."""
    items = []
    if job["education"]:
        need = min([lvl for lvl in [degree_level(job["education"])] if lvl] or [2])
        have = degree_level(info["degree"])
        items.append(dict(requirement=f"Education: {job['education'][:90]}", status="Verify" if not have else ("Met" if have >= need else "Not met"),
                          detail=info["degree"] or "Degree not detected in your resume - please verify."))
    if job["cgpa_min"]:
        c = cgpa_number(info)
        items.append(dict(requirement=f"Minimum CGPA {job['cgpa_min']:g}", status="Verify" if c is None else ("Met" if c >= job["cgpa_min"] else "Not met"),
                          detail=f"Your CGPA: {c:g}" if c is not None else "CGPA not detected - please verify."))
    if job["experience"]:
        lo = experience_minimum(job["experience"])
        n = len(info["internships"]) + len(info["experience"])
        items.append(dict(requirement=f"Experience: {job['experience'][:90]}", status="Met" if lo == 0 else "Verify",
                          detail="Fresher-friendly" if lo == 0 else f"Your resume lists {n} internship/experience entr{'y' if n == 1 else 'ies'}; years cannot be checked automatically."))
    for cert in job["cert_required"]:
        words = {w for w in re.findall(r"[a-z]{4,}", cert.lower())} - {"certification", "certificate", "certified", "required", "preferred"}
        ok = any(words & set(re.findall(r"[a-z]{4,}", c.lower())) for c in info["certifications"])
        items.append(dict(requirement=f"Certification: {cert[:90]}", status="Met" if ok else "Not met",
                          detail=f"{len(info['certifications'])} certification(s) listed in your resume"))
    return items


def analyze(info: dict, text: str, job: dict) -> dict:
    rows = compare_skills(info, text, job)
    checklist = requirement_checklist(info, job)
    req = [r for r in rows if r["level"] == "Required"]
    countable = [c for c in checklist if c["status"] != "Verify"]
    return dict(rows=rows, checklist=checklist, breakdown=match_breakdown(rows),
                match=match_breakdown(rows)["percent"],
                met=sum(r["status"] == "MATCH" for r in req) + sum(c["status"] == "Met" for c in countable),
                met_total=len(req) + len(countable),
                matched=[r for r in rows if r["status"] == "MATCH"], partial=[r for r in rows if r["status"] == "PARTIAL"],
                missing_required=[r for r in req if r["status"] == "GAP"],
                missing_preferred=[r for r in rows if r["level"] == "Preferred" and r["status"] == "GAP"],
                evidence=evidence_context(info, text))


def gap_rows(an: dict) -> list[dict]:
    """Skills still to work on (missing or partial): Required first, missing before partial."""
    return sorted([r for r in an["rows"] if r["status"] != "MATCH"], key=lambda r: (r["level"] != "Required", r["status"] != "GAP"))