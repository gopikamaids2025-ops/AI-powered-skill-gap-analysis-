"""Study Advisor (RULE-BASED). It applies fixed rules to the student's own data. No AI/LLM is connected.

To add a real LLM later, create a class with the same respond(question, ctx) method and use it in views.py.
"""
from __future__ import annotations

import re

from placement_model import LABELS, missing_values
from utils.skill_database import detect_skills, learning_plan


def advice_items(ctx: dict) -> list[dict]:
    """Priority list built from the real gaps, unmet requirements, resume tips and missing profile values."""
    job = ctx["job"]
    role = job["role"] + (f" at {job['company']}" if job["company"] else "")
    items = []
    for g in ctx["gaps"]:
        lp = learning_plan(g["skill"])
        topics = ", ".join(lp["topics"][:2])
        if g["status"] == "GAP":
            text = (f"Your target ({role}) {'requires' if g['level'] == 'Required' else 'prefers'} {g['skill']}, but {g['skill']} was not "
                    f"found in your resume. Consider learning it ({topics}) and adding a project: {lp['project'][0].lower() + lp['project'][1:]}.")
        else:
            text = f"{g['skill']} is {g['level'].lower()} for {role}. {g['evidence']} Strengthen it ({topics}) and show it in a project."
        items.append(dict(pri=1 if g["level"] == "Required" else 2, area=g["skill"], text=text))
    for c in ctx["an"]["checklist"]:
        if c["status"] == "Not met":
            items.append(dict(pri=1, area="Requirement", text=f"{c['requirement']} - not met ({c['detail']})."))
    for tip in ctx["quality"]["tips"][:2]:
        items.append(dict(pri=3, area="Resume", text=tip))
    miss = missing_values(ctx["ml"])
    if miss:
        items.append(dict(pri=3, area="Placement Readiness", text=f"{len(miss)} profile value(s) are missing, so the ML prediction cannot run yet. Add them in Profile."))
    if not items:
        items.append(dict(pri=3, area="Overall", text="Your resume currently covers all detected requirements."))
    return sorted(items, key=lambda i: i["pri"])


class RuleBasedMentor:
    name = "Study Advisor (rule-based)"

    def respond(self, question: str, ctx: dict) -> str:
        q, an, job, gaps = question.lower(), ctx["an"], ctx["job"], ctx["gaps"]
        for s in detect_skills(question):
            row = next((r for r in an["rows"] if r["skill"] == s), None)
            lp = learning_plan(s)
            status = {"MATCH": "is covered in your resume", "PARTIAL": "is only partly covered", "GAP": "was not found in your resume"}[row["status"]] \
                if row else "is not part of your target requirement"
            return f"**{s}** {status}.\n\nTopics: " + "; ".join(lp["topics"]) + f".\n\nMini project: {lp['project']}."
        if re.search(r"resume|cv", q):
            tips = ctx["quality"]["tips"][:4]
            return f"Your resume quality score is **{ctx['quality']['score']}/100** (rule-based). " + ("Suggestions:\n\n" + "\n".join(f"- {t}" for t in tips) if tips else "No major issues were found.")
        if re.search(r"role|job|career", q):
            return "Closest roles in the app's predefined role database (not job openings):\n\n" + "\n".join(f"- **{r['role']}**: {r['pct']:.0f}% role-skill match" for r in ctx["roles"][:3])
        if re.search(r"predict|ready|confidence|chance|placement", q):
            p = ctx["pred"]
            if not p:
                return "The ML prediction needs these values first: " + (", ".join(LABELS[f] for f in missing_values(ctx["ml"])) or "n/a") + ". Add them in Profile."
            conf = f" (model confidence {p['confidence']:.0f}%)" if p["confidence"] is not None else ""
            return f"The ML model predicts **{'READY' if p['label'] == 1 else 'NOT READY'}**{conf}. This is a model output, not a guarantee, and it is separate from your job match."
        if re.search(r"project", q):
            ideas = [f"- {g['skill']}: {learning_plan(g['skill'])['project']}" for g in gaps[:3]]
            return "Project ideas that close your gaps:\n\n" + "\n".join(ideas) if ideas else "You have no gaps to cover with a new project."
        if not gaps:
            return "Your resume currently covers all detected requirements."
        if re.search(r"focus|prior|week|improve|start|plan|weak|learn|gap", q):
            return f"For {job['role']}, focus on these first:\n\n" + "\n".join(f"- **{g['skill']}** ({g['level'].lower()}): {learning_plan(g['skill'])['topics'][0]}" for g in gaps[:4])
        return (f"Your Job Requirement Match is **{an['match']:.0f}%**. Remaining gaps: {', '.join(g['skill'] for g in gaps[:5])}. "
                "Ask about a skill, project ideas, your resume or career roles.")