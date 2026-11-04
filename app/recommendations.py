"""Career Role Recommendations: compare the student's skills with the application's predefined role-skill database.

These are NOT job openings. The match % here is a role-skill match and is separate from the Job Requirement Match.
"""
from __future__ import annotations

import re

from skill_gap import skill_status
from utils.skill_database import ROLE_SKILLS

STATEMENT = "Role recommendations are based on the application's predefined role-skill database. They are not current job vacancies."


def suggest_roles(info: dict, ev: dict, job: dict | None = None, gap_names: set | None = None) -> list[dict]:
    gap_names = {g.lower() for g in (gap_names or set())}
    out = []
    for role, skills in ROLE_SKILLS.items():
        matched, partial, missing = [], [], []
        for s in skills:
            status, _, _ = skill_status(s, ev)
            {"MATCH": matched, "PARTIAL": partial, "GAP": missing}[status].append(s)
        low = {s.lower() for s in skills}
        projects = [p["name"] for p in info["projects"] if {t.lower() for t in p.get("tech", [])} & low]
        is_target = False
        if job:
            rt = job["role"].lower().strip()
            tw, ow = set(re.findall(r"[a-z]+", rt)), set(re.findall(r"[a-z]+", role.lower()))
            is_target = bool(rt) and (role.lower() in rt or rt in role.lower() or len(tw & ow) / max(len(tw | ow), 1) >= 0.5)
        out.append(dict(role=role, pct=100 * (len(matched) + 0.5 * len(partial)) / len(skills), matched=matched, partial=partial,
                        missing=missing, projects=projects, target=is_target, shared_gaps=[s for s in missing if s.lower() in gap_names]))
    return sorted(out, key=lambda r: (-r["pct"], not r["target"]))